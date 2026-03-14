#!/usr/bin/env python3
"""
asignar_grupo_producto.py
Asigna grupo_producto en catalogo_articulos SOLO para artículos que han sido vendidos.
El grupo = nombre del producto sin gramaje ni medida.

Estrategia:
  - Paso 1: regex determinístico (yo, Claude) — asigna los actuales sin llamar a Groq
  - Paso 2: Groq (llama-3.1-8b-instant) — solo para nuevos que lleguen en el futuro
    y que el regex no resuelva bien

Uso:
  python3 asignar_grupo_producto.py            # asigna solo los que faltan
  python3 asignar_grupo_producto.py --dry-run  # muestra resultado sin escribir
  python3 asignar_grupo_producto.py --todos    # reasigna todos (útil si cambia el criterio)
  python3 asignar_grupo_producto.py --groq     # usa Groq para los que quedaron sin grupo
"""

import os, sys, re, time, json
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

DB_CFG  = dict(host='localhost', user='osadmin', password='Epist2487.', database='effi_data')
DRY_RUN = '--dry-run' in sys.argv
TODOS   = '--todos'   in sys.argv
USE_GROQ= '--groq'    in sys.argv

# ── REGEX — patrones de gramaje / medida a eliminar ──────────────────────────
# Orden importa: de más específico a más general
PATRONES_GRAMAJE = [
    # "X KG MOLDE 9 a 12 g" (caso especial producción)
    r'\bX\s+KG\s+MOLDE\b.*',
    # "(sin empacar)", "(ID 138)", "(ID102)"
    r'\(sin empacar\)',
    r'\(ID\s*\d+\)',
    # Porciones: "(55p)", "(27p)", "(22P)"
    r'\(\d+[pP]\)',
    # "PORCIONADA"
    r'\bPORCIONADA\b',
    # "PRODUCTO EN PROCESO", "SIN ETIQUETAR"
    r'\bPRODUCTO EN PROCESO\b',
    r'\bSIN\s+ETIQUETAR\b',
    # "MARZO 2024", "NOV 31", "OCT" (suelto al final)
    r'\b(?:ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+\d{4}\b',
    r'\b(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s+\d+\b',
    # "x 100 grs", "x 200 GRS", "X 100 GRS" (con número)
    r'\bx\s+\d+[\.,]?\d*\s*(?:grs?|g\b|kg|kl|kilos?|cc|lts?|ml)',
    # "X KILO", "X KG", "X KL", "X GRAMO", "X GRS" (sin número)
    r'\bx\s+(?:kilos?|kg|kl|gramos?|grs?|gr\b)\b',
    # "X UNIDAD", "X UND"
    r'\bX\s+(?:UNIDAD|UND|UNIDADES)\b',
    # Número + "grs", "gr", "g" (sin x): "500grs", "250 GRS", "1000g", "200g"
    r'\b\d+[\.,]?\d*\s*grs?\b',
    r'\b\d+\s*g\b',
    # Número + "kg", "kl", "kilo": "1kg", "5 KG", "1.370 GRS"
    r'\b\d+[\.,]?\d*\s*(?:kg|kl|kilos?)\b',
    # Número + "cc": "250cc", "135CC"
    r'\b\d+[\.,]?\d*\s*cc\b',
    # Número + "lt" como medida (ej "1 lt") — NO quita "LT" suelto (marca de producto)
    r'\b\d+[\.,]?\d*\s*lts?\b',
    # "Sg45" (gramos especiales Stevia): "Sg45", "Sg90"
    r'\bSg\d+\b',
    # "xgr" pegado
    r'\bxgr\b',
    # "x gramo", "x gramos"
    r'\bx\s+gramos?\b',
    # "65g" (sin espacio, al final)
    r'\b\d+gm\b',
]

def limpiar_grupo(desc: str) -> str:
    s = desc.strip()
    for p in PATRONES_GRAMAJE:
        s = re.sub(p, '', s, flags=re.IGNORECASE)
    # Limpiar espacios múltiples, comas/puntos/guiones finales
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[,.\-\s]+$', '', s).strip()
    # Si quedó vacío, devolver original
    return s if s else desc.strip()


# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
def get_conn():
    return mysql.connector.connect(**DB_CFG)

def fetch_vendidos(conn, todos=False):
    """Retorna los cod_articulo que han sido vendidos (facturas o remisiones)."""
    cur = conn.cursor(dictionary=True)
    if todos:
        cur.execute("""
            SELECT ca.cod_articulo, ca.descripcion
            FROM catalogo_articulos ca
            WHERE ca.cod_articulo IN (
                SELECT DISTINCT cod_articulo FROM zeffi_facturas_venta_detalle
                 WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
                UNION
                SELECT DISTINCT cod_articulo FROM zeffi_remisiones_venta_detalle
                 WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
            )
            ORDER BY CAST(ca.cod_articulo AS UNSIGNED)
        """)
    else:
        cur.execute("""
            SELECT ca.cod_articulo, ca.descripcion
            FROM catalogo_articulos ca
            WHERE ca.grupo_producto IS NULL
              AND ca.cod_articulo IN (
                SELECT DISTINCT cod_articulo FROM zeffi_facturas_venta_detalle
                 WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
                UNION
                SELECT DISTINCT cod_articulo FROM zeffi_remisiones_venta_detalle
                 WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
            )
            ORDER BY CAST(ca.cod_articulo AS UNSIGNED)
        """)
    rows = cur.fetchall()
    cur.close()
    return rows

def actualizar_bd(conn, cod, grupo):
    cur = conn.cursor()
    cur.execute(
        "UPDATE catalogo_articulos SET grupo_producto = %s, grupo_revisado = 1 WHERE cod_articulo = %s",
        (grupo, str(cod))
    )
    conn.commit()
    cur.close()


# ── GROQ — solo para nuevos con regex insuficiente ───────────────────────────
def asignar_con_groq(conn, articulos):
    try:
        from groq import Groq
    except ImportError:
        print("  groq no instalado. pip install groq")
        return

    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        print("  GROQ_API_KEY no configurada en .env")
        return

    client = Groq(api_key=api_key)
    LOTE   = 30  # conservador para llama-3.1-8b-instant (6K TPM)
    MODELO = 'llama-3.1-8b-instant'   # 14,400 RPD — más holgura

    SYSTEM = (
        "Eres un asistente de normalización de nombres de productos.\n"
        "Dado un listado de artículos, devuelve el grupo_producto de cada uno: "
        "el nombre SIN gramaje, medida ni cantidad de porciones.\n"
        "Elimina: '500 grs', '250g', '640 grs', '1kg', '250cc', '(55p)', 'PORCIONADA', "
        "'x KILO', 'x gramo', 'MARZO 2024', '(sin empacar)', etc.\n"
        "Conserva todo lo demás exactamente igual (mayúsculas, 'OS', 'LT', 'CPM', '73p', etc.).\n"
        "Para artículos sin gramaje (servicios, empaques, gastos), devuelve el nombre tal cual.\n"
        "Responde SOLO con JSON válido: [{\"cod\": \"11\", \"grupo\": \"...\"}]"
    )

    total_ok = 0
    for i in range(0, len(articulos), LOTE):
        lote = articulos[i:i+LOTE]
        payload = json.dumps(
            [{"cod": r['cod_articulo'], "desc": r['descripcion']} for r in lote],
            ensure_ascii=False
        )
        print(f"  Groq lote {i//LOTE+1}/{(len(articulos)+LOTE-1)//LOTE} ({len(lote)} artículos)...", end=' ', flush=True)
        try:
            resp = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": f"Artículos:\n{payload}"},
                ],
                temperature=0.1,
                max_tokens=1500,
            )
            texto = resp.choices[0].message.content.strip()
            if texto.startswith("```"):
                texto = texto.split("```")[1]
                if texto.startswith("json"):
                    texto = texto[4:]
            resultados = json.loads(texto)
            ok = 0
            for r in resultados:
                g = r.get('grupo', '').strip()
                if g and not DRY_RUN:
                    actualizar_bd(conn, r['cod'], g)
                    ok += 1
                elif DRY_RUN:
                    orig = next((x['descripcion'] for x in lote if str(x['cod_articulo']) == str(r.get('cod',''))), '?')
                    print(f"\n    [{r.get('cod')}] {orig[:45]}  →  {g}")
            total_ok += ok
            print(f"✅ {ok}")
        except Exception as e:
            # Rate limit: esperar 60s y reintentar
            if 'rate_limit' in str(e).lower() or '429' in str(e):
                print(f"⏳ rate limit — esperando 60s...")
                time.sleep(60)
            else:
                print(f"❌ {e}")
        time.sleep(1)
    print(f"  Groq: {total_ok} artículos actualizados.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    conn      = get_conn()
    articulos = fetch_vendidos(conn, todos=TODOS)
    total     = len(articulos)

    if total == 0:
        print("✅ Todos los artículos vendidos ya tienen grupo_producto asignado.")
        conn.close()
        return

    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}Procesando {total} artículos vendidos sin grupo...")
    print(f"\n  {'Cód':>5}  {'Descripción original':50}  Grupo asignado")
    print("  " + "-"*100)

    procesados   = 0
    sin_cambio   = 0  # donde regex no quitó nada

    for r in articulos:
        cod   = r['cod_articulo']
        desc  = r['descripcion']
        grupo = limpiar_grupo(desc)

        igual = (grupo.strip().lower() == desc.strip().lower())
        marcador = ' =' if igual else ''

        print(f"  {cod:>5}  {desc[:50]:50}  {grupo}{marcador}")

        if not DRY_RUN:
            actualizar_bd(conn, cod, grupo)
            procesados += 1
        if igual:
            sin_cambio += 1

    print(f"\n{'[DRY-RUN] ' if DRY_RUN else ''}{'Listo: ' if not DRY_RUN else ''}"
          f"{procesados if not DRY_RUN else total} artículos, "
          f"{sin_cambio} sin cambio (regex no encontró gramaje).")

    # Groq para los que quedaron igual y podrían necesitar revisión manual
    if USE_GROQ and not DRY_RUN:
        pendientes_groq = fetch_vendidos(conn, todos=False)
        if pendientes_groq:
            print(f"\nUsando Groq para {len(pendientes_groq)} artículos sin grupo aún...")
            asignar_con_groq(conn, pendientes_groq)

    conn.close()

    if not DRY_RUN:
        # Resumen final
        conn2 = get_conn()
        cur   = conn2.cursor()
        cur.execute("SELECT COUNT(*) FROM catalogo_articulos WHERE grupo_producto IS NOT NULL")
        n_con = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM catalogo_articulos WHERE grupo_producto IS NULL AND cod_articulo IN (SELECT DISTINCT cod_articulo FROM zeffi_facturas_venta_detalle UNION SELECT DISTINCT cod_articulo FROM zeffi_remisiones_venta_detalle)")
        n_sin = cur.fetchone()[0]
        cur.close()
        conn2.close()
        print(f"\nCatálogo: {n_con} con grupo_producto, {n_sin} vendidos aún sin grupo.")

if __name__ == '__main__':
    main()
