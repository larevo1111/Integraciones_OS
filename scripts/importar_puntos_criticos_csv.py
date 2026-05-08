#!/usr/bin/env python3
"""
importar_puntos_criticos_csv.py — Importa puntos críticos validados por Santi
desde el CSV `inventario/puntos_criticos_para_validar.csv` a la tabla
`prod_recetas_puntos_criticos` (BD inventario_produccion_effi en VPS).

Reglas de marca (columna `aprobar` del CSV):
  's' → Aprobado tal cual; insertar con valores propuestos
  'm' → Modificado por Santi; insertar con los valores que él puso en el CSV
  'n' → Rechazado; OMITIR
  ''  → No revisado; OMITIR (regla explícita: vacío = n)

Para `s` y `m` la lógica es la misma: insertar el row del CSV tal cual.

Para tipo='seleccion', extrae las opciones de la columna `notas_claude`
con formato "Opciones: A / B / C" → JSON ["A", "B", "C"].

Uso:
  python3 scripts/importar_puntos_criticos_csv.py [--dry-run]
"""
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
from lib import inventario  # type: ignore

CSV_PATH = REPO / 'inventario' / 'puntos_criticos_para_validar.csv'
DRY_RUN = '--dry-run' in sys.argv

# Mapeo CSV (plural/abreviado) → maestra prod_unidades_medida (singular).
# El CSV usa "min"/"horas"/"dias" pero la UI lee de la maestra que usa singular.
MAPEO_UNIDADES = {
    'horas': 'hora',
    'min': 'minuto',
    'minutos': 'minuto',
    'dias': 'dia',
    'segundos': 'segundo',
}


def normalizar_unidad(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip()
    return MAPEO_UNIDADES.get(u.lower(), u)


def inferir_instrumento(parametro: str, tipo: str) -> str | None:
    """Devuelve instrumento sugerido desde el nombre del parámetro.
    Cuando el CSV viene con `instrumento` vacío (caso típico cuando Santi
    marca 'm' y solo cambia min/max sin completar el resto), inferimos
    con sentido común. Reglas alineadas a doc CALIDAD_Y_PUNTOS_CRITICOS.md.
    """
    import re as _re
    p = (parametro or '').lower()
    if _re.search(r'\btiempo\b', p): return 'Cronómetro'
    if _re.search(r'\btemperatura\b', p): return 'Termómetro'
    if _re.search(r'\bph\b', p): return 'pH-metro'
    if 'cristaliza' in p or 'test de papel' in p: return 'Test papel'
    if _re.search(r'\bsabor\b|\bolor\b|\baroma\b', p): return 'Organoléptico'
    if _re.search(r'\bcolor\b|\btextura\b', p): return 'Visual'
    if 'quiebre' in p: return 'Test manual'
    return None


def parse_opciones(notas_claude: str) -> str | None:
    """Extrae lista de opciones de 'Opciones: A / B / C' → JSON."""
    if not notas_claude:
        return None
    m = re.search(r'Opciones?:\s*(.+)$', notas_claude, re.IGNORECASE)
    if not m:
        return None
    items = [x.strip() for x in m.group(1).split('/') if x.strip()]
    return json.dumps(items, ensure_ascii=False) if items else None


def num_or_none(s: str):
    s = (s or '').strip()
    if not s:
        return None
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        return None


def main():
    with open(CSV_PATH, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f, delimiter=';'))

    aprobados = [r for r in rows if (r['aprobar'] or '').strip().lower() in ('s', 'm')]
    print(f"Total filas CSV: {len(rows)}")
    print(f"Filas a importar (s+m): {len(aprobados)}")

    with inventario(dict_cursor=True) as conn:
        cur = conn.cursor()
        cods = {r['cod'] for r in aprobados}
        cur.execute(
            "SELECT cod_articulo, id FROM prod_recetas WHERE cod_articulo IN %s",
            (tuple(cods),),
        )
        cod_to_rid = {r['cod_articulo']: r['id'] for r in cur.fetchall()}

        if DRY_RUN:
            print("\n[DRY-RUN] No se inserta nada. Preview:")
            for r in aprobados[:10]:
                rid = cod_to_rid[r['cod']]
                print(f"  receta_id={rid} cod={r['cod']} ord={r['orden']} {r['parametro'][:40]:40} "
                      f"tipo={r['tipo']:10} {r['min']}-{r['max']} {r['unidad']}")
            print(f"  ... ({len(aprobados)} en total)")
            return

        # Limpiar puntos críticos previos de las recetas afectadas (idempotente)
        receta_ids = list({cod_to_rid[r['cod']] for r in aprobados})
        cur.execute(
            "DELETE FROM prod_recetas_puntos_criticos WHERE receta_id IN %s",
            (tuple(receta_ids),),
        )
        print(f"DELETE previos: {cur.rowcount} filas borradas en {len(receta_ids)} recetas")

        # Insertar
        inserted = 0
        for r in aprobados:
            rid = cod_to_rid[r['cod']]
            tipo = (r['tipo'] or 'numerico').strip().lower()
            valor_min = num_or_none(r['min']) if tipo == 'numerico' else None
            valor_max = num_or_none(r['max']) if tipo == 'numerico' else None
            unidad = normalizar_unidad(r['unidad'])
            instrumento = (r['instrumento'] or '').strip() or None
            if not instrumento:
                instrumento = inferir_instrumento(r['parametro'], tipo)
                if instrumento:
                    print(f"  ⚠ inferido instrumento '{instrumento}' para "
                          f"cod {r['cod']} '{r['parametro']}'")
            opciones_json = parse_opciones(r.get('notas_claude', '')) if tipo == 'seleccion' else None
            orden = int(r['orden']) if str(r['orden']).strip().isdigit() else 1

            cur.execute("""
                INSERT INTO prod_recetas_puntos_criticos
                  (receta_id, orden, parametro, tipo, unidad, instrumento,
                   valor_min, valor_max, opciones_json, obligatorio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (rid, orden, r['parametro'].strip(), tipo, unidad, instrumento,
                  valor_min, valor_max, opciones_json))
            inserted += 1

        conn.commit()
        print(f"\nINSERT OK: {inserted} puntos críticos insertados en {len(receta_ids)} recetas")


if __name__ == '__main__':
    main()
