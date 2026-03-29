#!/usr/bin/env python3
"""
Benchmark de routing con modelos Ollama locales.
Llama directamente a Ollama con el prompt de router real.
"""
import requests, json, time, re, sys

OLLAMA_API = "http://localhost:11434/v1/chat/completions"

ROUTER_SYSTEM = """Clasifica la siguiente pregunta y responde SOLO en formato JSON sin explicación:
{"tipo":"slug","tema":"slug_tema","requiere_sql":true}

TIPOS disponibles:
- analisis_datos: consultas sobre datos de la BD — ventas, facturas, compras, producción, inventario, remisiones, cotizaciones, clientes, pedidos, consignación, cartera, devoluciones, cifras, comparaciones.
- conversacion: preguntas sobre estrategia, planes, políticas, procesos, definiciones, saludos. Sin consultar la BD.
- redaccion: escribir textos, correos, documentos, mensajes.
- aprendizaje: el usuario enseña, corrige o aclara una regla de negocio.
- busqueda_web: información EXTERNA al negocio.
- resumen: resumir un texto largo.

PRINCIPIO FUNDAMENTAL:
  ¿La respuesta REQUIERE consultar registros de la BD para ser correcta?
  → SÍ: analisis_datos
  → NO: conversacion

TEMAS: comercial, finanzas, produccion, marketing, estrategia, administracion, general"""

PREGUNTAS = [
    ("¿Cuánto vendimos ayer?", "analisis_datos"),
    ("Hola buenos días", "conversacion"),
    ("¿Cuánto stock tenemos?", "analisis_datos"),
    ("Explícame las tarifas", "conversacion"),
    ("Top 5 productos vendidos", "analisis_datos"),
    ("¿Quién eres?", "conversacion"),
    ("Dame las compras del mes", "analisis_datos"),
    ("¿Cómo funciona la consignación?", "conversacion"),
    ("Escríbeme un correo de cobro a un cliente moroso", "redaccion"),
    ("¿Cuántos clientes tenemos?", "analisis_datos"),
    ("¿Cuál fue el margen de enero?", "analisis_datos"),
    ("Resúmeme las ventas de la semana", "analisis_datos"),
    ("¿Qué productos están sin stock?", "analisis_datos"),
    ("Dame los pedidos pendientes", "analisis_datos"),
    ("Enséñame cómo se calculan las ventas netas", "aprendizaje"),
]

MODELOS = [
    ("llama3.2:3b", "Llama 3B"),
    ("qwen2.5:7b", "Qwen 7B"),
]

def test_router(modelo, pregunta):
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_API, json={
            "model": modelo,
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM},
                {"role": "user", "content": pregunta}
            ],
            "temperature": 0,
            "max_tokens": 200,
        }, timeout=60)
        latencia = round((time.time() - t0) * 1000)
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Extraer JSON del contenido
        match = re.search(r'\{[^}]+\}', content)
        if match:
            parsed = json.loads(match.group())
            return {
                "tipo": parsed.get("tipo"),
                "tema": parsed.get("tema"),
                "sql": parsed.get("requiere_sql"),
                "raw": content[:100],
                "latencia": latencia,
                "ok": True,
            }
        return {"tipo": None, "raw": content[:100], "latencia": latencia, "ok": False}
    except Exception as e:
        return {"tipo": None, "raw": str(e)[:100], "latencia": round((time.time()-t0)*1000), "ok": False}


print(f"🔀 Benchmark Router Ollama — {len(PREGUNTAS) * len(MODELOS)} tests\n")

resultados = {}
for modelo, label in MODELOS:
    print(f"\n{'='*60}")
    print(f"  {label} ({modelo})")
    print(f"{'='*60}")

    aciertos = 0
    total = len(PREGUNTAS)
    resultados[label] = []

    for pregunta, esperado in PREGUNTAS:
        res = test_router(modelo, pregunta)
        detectado = res["tipo"]
        ok = detectado == esperado
        if ok:
            aciertos += 1
        icono = "✅" if ok else "❌"
        print(f"  {icono} {res['latencia']:>5}ms | {esperado:>16} → {str(detectado):>16} | {pregunta[:50]}")
        resultados[label].append({
            "pregunta": pregunta,
            "esperado": esperado,
            "detectado": detectado,
            "ok": ok,
            "latencia": res["latencia"],
            "raw": res["raw"],
        })

    print(f"\n  Resultado: {aciertos}/{total} ({round(aciertos*100/total)}%)")

# Guardar resultados al informe existente
ruta = "/home/osserver/Proyectos_Antigravity/Integraciones_OS/.agent/informes/benchmark_ollama_2026-03-29.md"
with open(ruta, "a") as f:
    f.write("\n\n## Detalle — Tests Router (corregidos)\n\n")
    f.write("Test directo contra Ollama API con el prompt de router real.\n\n")
    for label, items in resultados.items():
        ok_count = sum(1 for x in items if x["ok"])
        avg_lat = round(sum(x["latencia"] for x in items) / len(items))
        f.write(f"### {label} — {ok_count}/{len(items)} ({round(ok_count*100/len(items))}%) — avg {avg_lat}ms\n\n")
        f.write("| # | Pregunta | Esperado | Detectado | OK | Latencia |\n")
        f.write("|---|---|---|---|---|---|\n")
        for i, r in enumerate(items, 1):
            icono = "✅" if r["ok"] else "❌"
            f.write(f"| {i} | {r['pregunta'][:50]} | {r['esperado']} | {r['detectado']} | {icono} | {r['latencia']}ms |\n")
        f.write("\n")

print(f"\nResultados agregados a: {ruta}")
