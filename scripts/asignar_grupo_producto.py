#!/usr/bin/env python3
"""
asignar_grupo_producto.py
Usa Groq (llama-3.1-70b) para asignar grupo_producto a cada artículo en catalogo_articulos.
El grupo_producto es el nombre del producto SIN gramaje/medida.
Ejemplos:
  "Chocolate Puro Cacao 500 grs Bombones LT"  → "Chocolate Puro Cacao Bombones LT"
  "Miel Os Vidrio 640 grs"                     → "Miel Os Vidrio"
  "Tableta Chocolate 73p con Macadamia 50 grs" → "Tableta Chocolate 73p con Macadamia"
  "CHOCOMIEL OS 250cc"                          → "CHOCOMIEL OS"
  "Generico"                                    → "Generico"

Uso:
  python3 asignar_grupo_producto.py           # solo los que no tienen grupo asignado
  python3 asignar_grupo_producto.py --todos   # reasigna todos (útil si cambió el criterio)
  python3 asignar_grupo_producto.py --dry-run # muestra lo que haría sin escribir en BD
"""

import os, sys, json, time
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).parent / '.env')

DB_CFG = dict(host='localhost', user='osadmin', password='Epist2487.', database='effi_data')
GROQ_KEY = os.environ['GROQ_API_KEY']
LOTE = 40   # artículos por llamada a Groq
DRY_RUN = '--dry-run' in sys.argv
TODOS   = '--todos'   in sys.argv

SYSTEM_PROMPT = """Eres un asistente de normalización de nombres de productos.
Tu tarea: dado un listado de artículos con código y descripción, devolver el "grupo de producto" de cada uno.
El grupo de producto es el nombre SIN gramaje, medida, capacidad ni cantidad de porciones.
Elimina expresiones como: 500 grs, 250 grs, 400grs, 640 grs, 130 GRS, 50 grs, 80grs, 150 grs, 265 grs, 275 grs, 715grs, 565grs, 250cc, 400 cc, 500 cc, 135cc, 1kg, 1 kg, etc.
Elimina también patrones como: "(55p)", "(44p)", "(22P)", "PORCIONADA (15p)", "x4", "x6", "x12", etc.
Conserva EXACTAMENTE el resto del nombre (mayúsculas, tildes, abreviaturas como "OS", "LT", "CPM", "73p").
Para artículos genéricos o sin producto identificable (ej: "Generico", "Articulo 1Y", "SERVICIO", "FLETE"), mantén el nombre tal cual.

IMPORTANTE: responde SOLO con JSON válido, sin explicación, sin markdown, sin bloques de código.
Formato exacto: [{"cod": "11", "grupo": "CHOCOMIEL OS"}, ...]"""

def get_conn():
    return mysql.connector.connect(**DB_CFG)

def fetch_pendientes(conn, todos=False):
    cur = conn.cursor(dictionary=True)
    if todos:
        cur.execute("SELECT cod_articulo, descripcion FROM catalogo_articulos ORDER BY CAST(cod_articulo AS UNSIGNED)")
    else:
        cur.execute("SELECT cod_articulo, descripcion FROM catalogo_articulos WHERE grupo_producto IS NULL ORDER BY CAST(cod_articulo AS UNSIGNED)")
    rows = cur.fetchall()
    cur.close()
    return rows

def llamar_groq(client, lote):
    """Llama a Groq con un lote de artículos. Retorna lista de {cod, grupo}."""
    contenido = json.dumps(
        [{"cod": r['cod_articulo'], "desc": r['descripcion']} for r in lote],
        ensure_ascii=False
    )
    prompt = f"Asigna el grupo_producto a estos artículos:\n{contenido}"

    for intento in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            texto = resp.choices[0].message.content.strip()
            # Limpiar posible markdown
            if texto.startswith("```"):
                texto = texto.split("```")[1]
                if texto.startswith("json"):
                    texto = texto[4:]
            return json.loads(texto)
        except Exception as e:
            print(f"  ⚠️  Intento {intento+1}/3 falló: {e}")
            time.sleep(2)
    return []

def actualizar_bd(conn, resultados):
    cur = conn.cursor()
    ok = 0
    for r in resultados:
        grupo = r.get('grupo', '').strip()
        if not grupo:
            continue
        cur.execute(
            "UPDATE catalogo_articulos SET grupo_producto = %s, grupo_revisado = 1 WHERE cod_articulo = %s",
            (grupo, str(r['cod']))
        )
        ok += 1
    conn.commit()
    cur.close()
    return ok

def main():
    conn   = get_conn()
    client = Groq(api_key=GROQ_KEY)

    articulos = fetch_pendientes(conn, todos=TODOS)
    total = len(articulos)

    if total == 0:
        print("✅ Todos los artículos ya tienen grupo_producto asignado.")
        conn.close()
        return

    print(f"📦 {total} artículos a procesar {'(modo --dry-run)' if DRY_RUN else ''}")
    procesados = 0
    errores    = 0

    for i in range(0, total, LOTE):
        lote = articulos[i:i+LOTE]
        print(f"  Lote {i//LOTE + 1}/{(total+LOTE-1)//LOTE}  ({len(lote)} artículos)...", end=' ', flush=True)

        resultados = llamar_groq(client, lote)

        if not resultados:
            print("❌ sin respuesta")
            errores += len(lote)
            continue

        if DRY_RUN:
            for r in resultados:
                orig = next((x['descripcion'] for x in lote if str(x['cod_articulo']) == str(r.get('cod',''))), '?')
                print(f"\n    [{r.get('cod')}] {orig}  →  {r.get('grupo')}")
            print()
        else:
            ok = actualizar_bd(conn, resultados)
            procesados += ok
            print(f"✅ {ok}/{len(lote)}")

        time.sleep(0.5)  # cortesía con la API

    conn.close()

    if not DRY_RUN:
        print(f"\n🎉 Completado: {procesados}/{total} artículos actualizados, {errores} errores.")
        # Mostrar muestra del resultado
        conn2 = get_conn()
        cur = conn2.cursor()
        cur.execute("SELECT cod_articulo, descripcion, grupo_producto FROM catalogo_articulos WHERE grupo_producto IS NOT NULL ORDER BY CAST(cod_articulo AS UNSIGNED) LIMIT 15")
        print("\nMuestra del catálogo:")
        print(f"  {'Cód':>5}  {'Descripción':45}  Grupo")
        for row in cur.fetchall():
            print(f"  {row[0]:>5}  {str(row[1])[:45]:45}  {row[2]}")
        cur.close()
        conn2.close()

if __name__ == '__main__':
    main()
