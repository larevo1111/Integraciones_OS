#!/usr/bin/env python3
"""
sync_catalogo_articulos.py
Pipeline: detecta nuevos cod_articulo vendidos que no están en catalogo_articulos,
los agrega y les asigna grupo_producto.

Estrategia:
  1. Regex determinístico (instantáneo, sin API)
  2. Si quedan sin resolver → Groq llama-3.1-8b-instant (14,400 RPD free)
     Solo llamar a Groq si hay nuevos que el regex no resolvió bien.

Uso:
  python3 sync_catalogo_articulos.py            # modo normal (pipeline)
  python3 sync_catalogo_articulos.py --dry-run  # solo muestra novedades
"""

import os, re, sys, time, json
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
DB_CFG   = dict(host='localhost', user='osadmin', password='Epist2487.', database='effi_data')
DRY_RUN  = '--dry-run' in sys.argv

PATRONES_GRAMAJE = [
    r'\bX\s+KG\s+MOLDE\b.*',
    r'\(sin empacar\)',
    r'\(ID\s*\d+\)',
    r'\(\d+[pP]\)',
    r'\bPORCIONADA\b',
    r'\bPRODUCTO EN PROCESO\b',
    r'\bSIN\s+ETIQUETAR\b',
    r'\b(?:ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+\d{4}\b',
    r'\b(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s+\d+\b',
    r'\bx\s+\d+[\.,]?\d*\s*(?:grs?|g\b|kg|kl|kilos?|cc|lts?|ml)',
    r'\bx\s+(?:kilos?|kg|kl|gramos?|grs?|gr\b)\b',
    r'\bX\s+(?:UNIDAD|UND|UNIDADES)\b',
    r'\b\d+[\.,]?\d*\s*grs?\b',
    r'\b\d+\s*g\b',
    r'\b\d+[\.,]?\d*\s*(?:kg|kl|kilos?)\b',
    r'\b\d+[\.,]?\d*\s*cc\b',
    r'\b\d+[\.,]?\d*\s*lts?\b',
    r'\bSg\d+\b',
    r'\bxgr\b',
    r'\bx\s+gramos?\b',
    r'\b\d+gm\b',
]

def limpiar_grupo(desc: str) -> str:
    s = desc.strip()
    for p in PATRONES_GRAMAJE:
        s = re.sub(p, '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[,.\-\s]+$', '', s).strip()
    return s if s else desc.strip()

def get_conn():
    return mysql.connector.connect(**DB_CFG)

def fetch_nuevos(conn):
    """Artículos vendidos que no están en catalogo_articulos."""
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT v.cod_articulo, MIN(v.descripcion) AS descripcion
        FROM (
            SELECT cod_articulo, descripcion_articulo AS descripcion
              FROM zeffi_facturas_venta_detalle
             WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
               AND descripcion_articulo IS NOT NULL AND descripcion_articulo != ''
            UNION ALL
            SELECT cod_articulo, descripcion_articulo
              FROM zeffi_remisiones_venta_detalle
             WHERE cod_articulo IS NOT NULL AND cod_articulo != ''
               AND descripcion_articulo IS NOT NULL AND descripcion_articulo != ''
        ) v
        WHERE v.cod_articulo NOT IN (SELECT cod_articulo FROM catalogo_articulos)
        GROUP BY v.cod_articulo
        ORDER BY CAST(v.cod_articulo AS UNSIGNED)
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def insertar_y_asignar(conn, nuevos):
    cur = conn.cursor()
    for r in nuevos:
        grupo = limpiar_grupo(r['descripcion'])
        cur.execute(
            "INSERT IGNORE INTO catalogo_articulos (cod_articulo, descripcion, grupo_producto, grupo_revisado) VALUES (%s, %s, %s, 1)",
            (r['cod_articulo'], r['descripcion'], grupo)
        )
    conn.commit()
    cur.close()

def main():
    conn   = get_conn()
    nuevos = fetch_nuevos(conn)

    if not nuevos:
        print("✅ catalogo_articulos al día — sin productos nuevos.")
        conn.close()
        return

    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}🆕 {len(nuevos)} producto(s) nuevo(s) detectado(s):")
    for r in nuevos:
        grupo = limpiar_grupo(r['descripcion'])
        igual = grupo.strip().lower() == r['descripcion'].strip().lower()
        print(f"  [{r['cod_articulo']}] {r['descripcion'][:50]}  →  {grupo}{' =' if igual else ''}")

    if not DRY_RUN:
        insertar_y_asignar(conn, nuevos)
        print(f"✅ {len(nuevos)} producto(s) agregado(s) al catálogo.")

        # Si hay alguno donde regex no quitó gramaje y tenemos Groq, usarlo
        sin_limpiar = [r for r in nuevos if limpiar_grupo(r['descripcion']).strip().lower() == r['descripcion'].strip().lower()]
        if sin_limpiar and os.environ.get('GROQ_API_KEY'):
            print(f"  Groq verificará {len(sin_limpiar)} artículo(s) donde regex no actuó...")
            _groq_verificar(conn, sin_limpiar)

    conn.close()

def _groq_verificar(conn, articulos):
    """Usa Groq solo para artículos donde el regex no encontró gramaje."""
    try:
        from groq import Groq
    except ImportError:
        return

    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    MODELO = 'llama-3.1-8b-instant'
    SISTEMA = (
        "Dado un artículo con código y descripción, responde SOLO con JSON: "
        "{\"cod\": \"...\", \"grupo\": \"...\"}. "
        "El grupo = nombre SIN gramaje (500 grs, 250g, 1kg, 250cc, x kilo, x gramo, etc.). "
        "Si no hay gramaje, devuelve el nombre tal cual."
    )
    for r in articulos:
        try:
            resp = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": SISTEMA},
                    {"role": "user",   "content": json.dumps({"cod": r['cod_articulo'], "desc": r['descripcion']}, ensure_ascii=False)},
                ],
                temperature=0.1, max_tokens=100,
            )
            resultado = json.loads(resp.choices[0].message.content.strip())
            grupo = resultado.get('grupo', '').strip()
            if grupo and grupo.strip().lower() != r['descripcion'].strip().lower():
                cur = conn.cursor()
                cur.execute("UPDATE catalogo_articulos SET grupo_producto = %s WHERE cod_articulo = %s", (grupo, r['cod_articulo']))
                conn.commit()
                cur.close()
                print(f"  Groq [{r['cod_articulo']}]: {r['descripcion']} → {grupo}")
        except Exception as e:
            if '429' in str(e) or 'rate' in str(e).lower():
                print("  Groq rate limit — esperando 60s...")
                time.sleep(60)
        time.sleep(0.5)

if __name__ == '__main__':
    main()
