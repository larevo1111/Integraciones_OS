"""crear_inventario_30abr_desde_xlsx.py

Crea el inventario físico del 2026-04-30 a partir del xlsx export crudo de Effi
(`inventario/snapshots/inventario_2026-04-30_teorico.xlsx`).

Particularidades de este inventario (definidas por Santi 2026-05-03):
- Solo 3 bodegas: Principal, Productos No Conformes, Jenifer (las otras 12 se ignoran).
- Teórico = stock del xlsx tal cual (NO se descuentan OPs Generadas/Validadas).
- Aplica reglas estándar de exclusión (config_depuracion.json).
- Pre-carga físico para 2 cods nuevos de cacao San Luis (no estaban en Effi al 30-abr):
    cod 593 NIBS DE CACAO SL x KG → 97.5 kg en Principal
    cod 594 CASCARILLA DE CACAO SL x KG → 16 kg en Principal

Uso:
    python3 scripts/inventario/crear_inventario_30abr_desde_xlsx.py            # dry-run
    python3 scripts/inventario/crear_inventario_30abr_desde_xlsx.py --apply    # ejecuta
"""
import argparse
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
from lib import local  # type: ignore

XLSX_PATH = REPO / 'inventario' / 'snapshots' / 'inventario_2026-04-30_teorico.xlsx'
CONFIG_DEPURACION = REPO / 'scripts' / 'inventario' / 'config_depuracion.json'
FECHA_INVENTARIO = '2026-04-30'

BODEGAS_INCLUIDAS = ['Principal', 'Productos No Conformes', 'Jenifer']
COL_BODEGA_XLSX = {
    'Principal': 'Stock bodega: Principal (Sucursal: Principal)',
    'Productos No Conformes': 'Stock bodega: Productos No Conformes Bod PPAL (Sucursal: Principal)',
    'Jenifer': 'Stock bodega: Jenifer (Sucursal: Principal)',
}

PRECARGA_FISICO = [
    {'id_effi': '593', 'bodega': 'Principal', 'fisico': 97.5,
     'nombre_fallback': 'NIBS DE CACAO SL x KG',
     'categoria_fallback': 'T01.03. AGROECOLOGICOS GRAL',
     'costo_fallback': 19000.0},
    {'id_effi': '594', 'bodega': 'Principal', 'fisico': 16.0,
     'nombre_fallback': 'CASCARILLA DE CACAO SL x KG',
     'categoria_fallback': 'T01.03. AGROECOLOGICOS GRAL',
     'costo_fallback': 3300.0},
]

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def parse_xlsx(path):
    with zipfile.ZipFile(path) as z:
        sh_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall(f'{NS}si'):
                sh_strings.append(''.join(t.text or '' for t in si.iter(f'{NS}t')))
        sh_root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rows_xml = sh_root.findall(f'{NS}sheetData/{NS}row')

        def parse_row(row):
            cells = []
            for c in row.findall(f'{NS}c'):
                v_elem = c.find(f'{NS}v')
                t = c.get('t', 'n')
                v = v_elem.text if v_elem is not None else ''
                if t == 's' and v:
                    v = sh_strings[int(v)]
                cells.append(v)
            return cells

        headers = parse_row(rows_xml[0])
        data = [dict(zip(headers, parse_row(r))) for r in rows_xml[1:]]
        return data


def parsear_decimal(s):
    if not s or s == '' or s == '-No aplica-':
        return 0.0
    try:
        return float(str(s).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def aplica_exclusion(art, config):
    if config.get('excluir_sin_gestion_stock') and art.get('Gestión de stock', '').strip() != 'Sí':
        return ('excluido_sin_gestion_stock', 'No tiene gestión de stock')
    cat = (art.get('Categoría') or '').strip()
    if config.get('excluir_sin_categoria') and not cat:
        return ('excluido_sin_categoria', 'Sin categoría')
    for regla in config.get('excluir_categorias', []):
        patron = regla['patron'].rstrip('%')
        if cat.startswith(patron):
            return ('excluido_categoria', regla['razon'])
    return None


def construir_filas(articulos, config):
    """Devuelve lista de dicts listos para INSERT."""
    filas = []
    excluidos = []

    for art in articulos:
        if art.get('Vigencia', '').strip() != 'Vigente':
            continue
        id_effi = (art.get('ID') or '').strip()
        if not id_effi:
            continue

        nombre = (art.get('Nombre') or '').strip()
        cat = (art.get('Categoría') or '').strip()
        cod_barras = (art.get('COD. BARRAS') or '').strip() or None
        costo_manual = parsear_decimal(art.get('Costo manual'))

        excl = aplica_exclusion(art, config)
        if excl:
            excluidos.append({
                'id_effi': id_effi, 'nombre': nombre, 'categoria': cat,
                'cod_barras': cod_barras, 'razon': excl[1],
            })
            continue

        for bodega in BODEGAS_INCLUIDAS:
            col = COL_BODEGA_XLSX[bodega]
            stock = parsear_decimal(art.get(col))
            if stock <= 0:
                continue
            filas.append({
                'fecha_inventario': FECHA_INVENTARIO,
                'bodega': bodega,
                'id_effi': id_effi,
                'cod_barras': cod_barras,
                'nombre': nombre,
                'categoria': cat,
                'excluido': 0,
                'razon_exclusion': None,
                'inventario_teorico': round(stock, 2),
                'inventario_fisico': None,
                'diferencia': None,
                'costo_manual': costo_manual,
                'estado': 'pendiente',
                'contado_por': None,
                'fecha_conteo': None,
                'notas': None,
            })

    return filas, excluidos


def aplicar_precargas(filas, articulos_por_id):
    """Pre-carga conteo físico para los SL nuevos. Si ya existe la fila la actualiza,
    si no, la inserta con teorico=0 y costo_manual desde Effi (si está en xlsx) o 0."""
    for prec in PRECARGA_FISICO:
        id_effi = prec['id_effi']
        bodega = prec['bodega']
        fisico = prec['fisico']
        match = next((f for f in filas if f['id_effi'] == id_effi and f['bodega'] == bodega), None)
        if match:
            match['inventario_fisico'] = fisico
            match['diferencia'] = round(fisico - (match['inventario_teorico'] or 0), 2)
            match['estado'] = 'contado'
            match['contado_por'] = 'precarga_30abr_xlsx'
            match['notas'] = f'Precarga: {fisico} kg de cacao San Luis (cod nuevo, no en xlsx Effi 30-abr)'
        else:
            art = articulos_por_id.get(id_effi, {})
            costo = parsear_decimal(art.get('Costo manual')) or prec.get('costo_fallback', 0)
            nombre = (art.get('Nombre') or '').strip() or prec.get('nombre_fallback') or f'COD {id_effi}'
            categoria = (art.get('Categoría') or '').strip() or prec.get('categoria_fallback')
            filas.append({
                'fecha_inventario': FECHA_INVENTARIO,
                'bodega': bodega,
                'id_effi': id_effi,
                'cod_barras': (art.get('COD. BARRAS') or '').strip() or None,
                'nombre': nombre,
                'categoria': categoria,
                'excluido': 0,
                'razon_exclusion': None,
                'inventario_teorico': 0.0,
                'inventario_fisico': fisico,
                'diferencia': fisico,
                'costo_manual': costo,
                'estado': 'contado',
                'contado_por': 'precarga_30abr_xlsx',
                'fecha_conteo': None,
                'notas': f'Precarga: {fisico} kg de cacao San Luis (cod nuevo, no en xlsx Effi 30-abr)',
            })
    return filas


def fetch_articulos_sl_de_zeffi(cods):
    """Si los cods nuevos no están en el xlsx, los buscamos en os_integracion para
    tener nombre y costo correctos."""
    from lib import integracion  # type: ignore
    if not cods:
        return {}
    placeholders = ','.join(['%s'] * len(cods))
    with integracion(dict_cursor=True) as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, nombre, categoria, costo_manual FROM zeffi_inventario WHERE id IN ({placeholders})",
            cods,
        )
        return {r['id']: r for r in cur.fetchall()}


def insertar_filas(filas):
    sql = """
        INSERT INTO inv_conteos
          (fecha_inventario, bodega, id_effi, cod_barras, nombre, categoria,
           excluido, razon_exclusion, inventario_teorico, inventario_fisico,
           diferencia, costo_manual, estado, contado_por, fecha_conteo, notas)
        VALUES
          (%(fecha_inventario)s, %(bodega)s, %(id_effi)s, %(cod_barras)s, %(nombre)s, %(categoria)s,
           %(excluido)s, %(razon_exclusion)s, %(inventario_teorico)s, %(inventario_fisico)s,
           %(diferencia)s, %(costo_manual)s, %(estado)s, %(contado_por)s, %(fecha_conteo)s, %(notas)s)
    """
    with local('inventario_produccion_effi') as conn:
        cur = conn.cursor()
        cur.executemany(sql, filas)
        conn.commit()
        return cur.rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Ejecuta INSERT (default: dry-run)')
    args = parser.parse_args()

    print(f'Leyendo xlsx: {XLSX_PATH}')
    articulos = parse_xlsx(XLSX_PATH)
    print(f'  → {len(articulos)} filas')

    config = json.loads(CONFIG_DEPURACION.read_text(encoding='utf-8'))

    filas, excluidos = construir_filas(articulos, config)
    print(f'\nFilas construidas (sin precargas): {len(filas)}')
    print(f'  Por bodega:')
    for b in BODEGAS_INCLUIDAS:
        n = sum(1 for f in filas if f['bodega'] == b)
        teorico_total = sum(f['inventario_teorico'] for f in filas if f['bodega'] == b)
        print(f'    {b:30s} {n:4d} líneas | suma teórico: {teorico_total:>12,.2f}')

    print(f'\nArtículos excluidos: {len(excluidos)}')
    razones = {}
    for e in excluidos:
        razones[e['razon']] = razones.get(e['razon'], 0) + 1
    for razon, n in sorted(razones.items(), key=lambda x: -x[1]):
        print(f'  {n:4d}  {razon}')

    # Precargas — verificar si están en xlsx, si no buscar en zeffi
    cods_precarga = [p['id_effi'] for p in PRECARGA_FISICO]
    articulos_por_id = {a.get('ID', '').strip(): a for a in articulos}
    faltantes = [c for c in cods_precarga if c not in articulos_por_id]
    if faltantes:
        print(f'\nCods precarga NO en xlsx, buscando en zeffi_inventario: {faltantes}')
        try:
            extra = fetch_articulos_sl_de_zeffi(faltantes)
            for cid, row in extra.items():
                articulos_por_id[cid] = {
                    'ID': cid, 'Nombre': row['nombre'], 'Categoría': row['categoria'],
                    'Costo manual': row['costo_manual'], 'COD. BARRAS': '',
                }
                print(f'  ✓ {cid} {row["nombre"]} (costo {row["costo_manual"]})')
            for c in faltantes:
                if c not in extra:
                    print(f'  ⚠ {c} tampoco en zeffi_inventario — uso defaults')
        except Exception as e:
            print(f'  ⚠ No pude consultar zeffi: {e}. Uso defaults.')

    filas = aplicar_precargas(filas, articulos_por_id)

    print(f'\nFilas FINALES (con precargas): {len(filas)}')
    contadas = [f for f in filas if f['estado'] == 'contado']
    print(f'  Pre-contadas: {len(contadas)}')
    for f in contadas:
        print(f'    cod {f["id_effi"]:5s} {f["nombre"][:50]:50s} | {f["bodega"]:25s} | físico={f["inventario_fisico"]} teórico={f["inventario_teorico"]}')

    if not args.apply:
        print('\n[DRY-RUN] Ejecutar con --apply para insertar.')
        return

    print('\nInsertando en inv_conteos...')
    n = insertar_filas(filas)
    print(f'  ✅ {n} filas insertadas para fecha {FECHA_INVENTARIO}')


if __name__ == '__main__':
    main()
