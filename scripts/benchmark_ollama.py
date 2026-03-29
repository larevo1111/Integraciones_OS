#!/usr/bin/env python3
"""
Benchmark de modelos Ollama locales.
Testea: conversación, SQL (analisis_datos), y routing.
Resultados en .agent/informes/benchmark_ollama_2026-03-29.md
"""
import requests, json, time, sys
from datetime import datetime

API = "http://localhost:5100/ia/consultar"
EMPRESA = "ori_sil_2"
USUARIO = "benchmark"
CANAL = "test"

# ── Preguntas por categoría ─────────────────────────────────────────────────

SQL_PREGUNTAS = [
    "¿Cuánto vendimos este mes?",
    "¿Cuánto vendimos en febrero 2026?",
    "Top 5 productos más vendidos en unidades este año",
    "¿Cuánto hay en cartera vencida?",
    "¿Cuántas remisiones pendientes de facturar hay?",
    "¿Cuál fue el canal de venta más fuerte en enero 2026?",
    "¿Cuánto stock hay de productos terminados?",
    "¿Cuántas órdenes de producción vigentes hay?",
    "¿Cuánto valor hay en consignación activa?",
    "Ventas por canal este mes",
    "¿Cuántos clientes nuevos compraron este año?",
    "Top 3 clientes por valor facturado este mes",
    "¿Cuál es el margen promedio de las ventas de febrero?",
    "Dame las compras de materia prima de este año",
    "¿Cuántas notas crédito se hicieron en marzo 2026?",
]

CONV_PREGUNTAS = [
    "Hola, ¿cómo estás?",
    "¿Quién eres y para qué sirves?",
    "¿Cuáles son los canales de venta de Origen Silvestre?",
    "Explícame cómo funciona la consignación",
    "¿Qué tarifas de precios maneja la empresa?",
    "¿Cómo se clasifica a los clientes?",
    "¿Cómo funciona la producción en Origen Silvestre?",
    "Explícame la política de devoluciones",
    "¿Qué categorías de artículos existen?",
    "Dame un resumen de cómo funciona la cartera",
]

ROUTER_PREGUNTAS = [
    "¿Cuánto vendimos ayer?",
    "Hola buenos días",
    "¿Cuánto stock tenemos?",
    "Explícame las tarifas",
    "Top 5 productos vendidos",
    "¿Quién eres?",
    "Dame las compras del mes",
    "¿Cómo funciona la consignación?",
    "Escríbeme un correo de cobro a un cliente moroso",
    "¿Cuántos clientes tenemos?",
    "¿Cuál fue el margen de enero?",
    "Resúmeme las ventas de la semana",
    "¿Qué productos están sin stock?",
    "Dame los pedidos pendientes",
    "Enséñame cómo se calculan las ventas netas",
]

# ── Config de tests ──────────────────────────────────────────────────────────

TESTS = [
    # SQL — agentes que deben generar SQL
    {"agente": "ollama-deepseek-r1",  "tipo": "analisis_datos", "preguntas": SQL_PREGUNTAS,  "label": "DeepSeek R1 14B — SQL"},
    {"agente": "ollama-qwen-coder",   "tipo": "analisis_datos", "preguntas": SQL_PREGUNTAS,  "label": "Qwen Coder 14B — SQL"},
    {"agente": "ollama-qwen-14b",     "tipo": "analisis_datos", "preguntas": SQL_PREGUNTAS,  "label": "Qwen 14B — SQL"},

    # Conversación
    {"agente": "ollama-deepseek-r1",  "tipo": "conversacion",   "preguntas": CONV_PREGUNTAS, "label": "DeepSeek R1 14B — Conv"},
    {"agente": "ollama-qwen-coder",   "tipo": "conversacion",   "preguntas": CONV_PREGUNTAS, "label": "Qwen Coder 14B — Conv"},
    {"agente": "ollama-qwen-14b",     "tipo": "conversacion",   "preguntas": CONV_PREGUNTAS, "label": "Qwen 14B — Conv"},

    # Router
    {"agente": "ollama-llama-3b",     "tipo": "enrutamiento",   "preguntas": ROUTER_PREGUNTAS, "label": "Llama 3B — Router"},
    {"agente": "ollama-qwen-7b",      "tipo": "enrutamiento",   "preguntas": ROUTER_PREGUNTAS, "label": "Qwen 7B — Router"},
]

TIPOS_ESPERADOS_ROUTER = {
    "¿Cuánto vendimos ayer?": "analisis_datos",
    "Hola buenos días": "conversacion",
    "¿Cuánto stock tenemos?": "analisis_datos",
    "Explícame las tarifas": "conversacion",
    "Top 5 productos vendidos": "analisis_datos",
    "¿Quién eres?": "conversacion",
    "Dame las compras del mes": "analisis_datos",
    "¿Cómo funciona la consignación?": "conversacion",
    "Escríbeme un correo de cobro a un cliente moroso": "redaccion",
    "¿Cuántos clientes tenemos?": "analisis_datos",
    "¿Cuál fue el margen de enero?": "analisis_datos",
    "Resúmeme las ventas de la semana": "analisis_datos",
    "¿Qué productos están sin stock?": "analisis_datos",
    "Dame los pedidos pendientes": "analisis_datos",
    "Enséñame cómo se calculan las ventas netas": "aprendizaje",
}


def consultar(pregunta, agente, tipo=None):
    """Llama al ia_service y retorna el resultado."""
    payload = {
        "pregunta": pregunta,
        "agente": agente,
        "usuario_id": USUARIO,
        "canal": CANAL,
        "empresa": EMPRESA,
    }
    if tipo:
        payload["tipo"] = tipo

    t0 = time.time()
    try:
        r = requests.post(API, json=payload, timeout=120)
        latencia = round((time.time() - t0) * 1000)
        data = r.json()
        return {
            "ok": data.get("ok", False),
            "respuesta": (data.get("respuesta") or "")[:200],
            "sql": (data.get("sql") or "")[:300],
            "formato": data.get("formato"),
            "tokens_in": data.get("tokens_in", 0),
            "tokens_out": data.get("tokens_out", 0),
            "latencia_ms": latencia,
            "error": data.get("error"),
            "tipo_detectado": data.get("tipo"),
        }
    except Exception as e:
        return {
            "ok": False,
            "respuesta": "",
            "sql": "",
            "formato": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "latencia_ms": round((time.time() - t0) * 1000),
            "error": str(e),
            "tipo_detectado": None,
        }


def evaluar_router(pregunta, resultado):
    """Para tests de routing: evalúa si el tipo detectado es correcto."""
    esperado = TIPOS_ESPERADOS_ROUTER.get(pregunta)
    detectado = resultado.get("tipo_detectado")
    if not esperado:
        return "?"
    return "✅" if detectado == esperado else f"❌ ({detectado} vs {esperado})"


def run_tests():
    resultados = []
    total = sum(len(t["preguntas"]) for t in TESTS)
    i = 0

    for grupo in TESTS:
        agente = grupo["agente"]
        tipo = grupo["tipo"]
        label = grupo["label"]
        preguntas = grupo["preguntas"]

        print(f"\n{'='*60}")
        print(f"  {label} — {len(preguntas)} preguntas")
        print(f"{'='*60}")

        grupo_resultados = []
        for pregunta in preguntas:
            i += 1
            print(f"  [{i}/{total}] {pregunta[:60]}...", end=" ", flush=True)

            res = consultar(pregunta, agente, tipo if tipo != "enrutamiento" else None)

            status = "✅" if res["ok"] else "❌"
            extras = ""
            if tipo == "analisis_datos":
                tiene_sql = "SQL✅" if res["sql"] else "SQL❌"
                extras = f" | {tiene_sql}"
            elif tipo == "enrutamiento":
                ruta_ok = evaluar_router(pregunta, res)
                extras = f" | ruta={ruta_ok}"

            print(f"{status} {res['latencia_ms']}ms{extras}")

            grupo_resultados.append({
                "pregunta": pregunta,
                "agente": agente,
                "tipo_test": tipo,
                "label": label,
                **res,
            })

        resultados.extend(grupo_resultados)

    return resultados


def generar_informe(resultados):
    """Genera el informe markdown."""
    lineas = [
        "# Benchmark Modelos Ollama Locales",
        f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total tests**: {len(resultados)}",
        "",
    ]

    # Agrupar por label
    grupos = {}
    for r in resultados:
        lbl = r["label"]
        if lbl not in grupos:
            grupos[lbl] = []
        grupos[lbl].append(r)

    # Resumen general
    lineas.append("## Resumen por agente/rol")
    lineas.append("")
    lineas.append("| Test | Total | OK | Fail | % Éxito | Avg latencia | Avg tokens in | Avg tokens out |")
    lineas.append("|---|---|---|---|---|---|---|---|")

    for label, items in grupos.items():
        total = len(items)
        ok = sum(1 for x in items if x["ok"])
        fail = total - ok
        pct = round(ok * 100 / total) if total else 0
        avg_lat = round(sum(x["latencia_ms"] for x in items) / total) if total else 0
        avg_in = round(sum(x["tokens_in"] for x in items) / total) if total else 0
        avg_out = round(sum(x["tokens_out"] for x in items) / total) if total else 0
        lineas.append(f"| {label} | {total} | {ok} | {fail} | {pct}% | {avg_lat}ms | {avg_in} | {avg_out} |")

    lineas.append("")

    # SQL detalle
    lineas.append("## Detalle — Tests SQL")
    lineas.append("")
    for label, items in grupos.items():
        if "SQL" not in label:
            continue
        lineas.append(f"### {label}")
        lineas.append("")
        lineas.append("| # | Pregunta | OK | SQL | Latencia | Error |")
        lineas.append("|---|---|---|---|---|---|")
        for idx, r in enumerate(items, 1):
            ok = "✅" if r["ok"] else "❌"
            sql = "✅" if r["sql"] else "❌"
            err = (r["error"] or "")[:60]
            lineas.append(f"| {idx} | {r['pregunta'][:50]} | {ok} | {sql} | {r['latencia_ms']}ms | {err} |")
        lineas.append("")

    # Conversación detalle
    lineas.append("## Detalle — Tests Conversación")
    lineas.append("")
    for label, items in grupos.items():
        if "Conv" not in label:
            continue
        lineas.append(f"### {label}")
        lineas.append("")
        lineas.append("| # | Pregunta | OK | Latencia | Respuesta (preview) |")
        lineas.append("|---|---|---|---|---|")
        for idx, r in enumerate(items, 1):
            ok = "✅" if r["ok"] else "❌"
            resp = (r["respuesta"] or "")[:80].replace("|", "\\|").replace("\n", " ")
            lineas.append(f"| {idx} | {r['pregunta'][:50]} | {ok} | {r['latencia_ms']}ms | {resp} |")
        lineas.append("")

    # Router detalle
    lineas.append("## Detalle — Tests Router")
    lineas.append("")
    for label, items in grupos.items():
        if "Router" not in label:
            continue
        lineas.append(f"### {label}")
        lineas.append("")
        lineas.append("| # | Pregunta | Esperado | Detectado | Correcto |")
        lineas.append("|---|---|---|---|---|")
        for idx, r in enumerate(items, 1):
            esperado = TIPOS_ESPERADOS_ROUTER.get(r["pregunta"], "?")
            detectado = r.get("tipo_detectado", "?")
            ok_ruta = evaluar_router(r["pregunta"], r)
            lineas.append(f"| {idx} | {r['pregunta'][:50]} | {esperado} | {detectado} | {ok_ruta} |")
        lineas.append("")

    return "\n".join(lineas)


if __name__ == "__main__":
    print(f"\n🚀 Benchmark Ollama — {sum(len(t['preguntas']) for t in TESTS)} tests")
    print(f"   Hora: {datetime.now().strftime('%H:%M:%S')}\n")

    resultados = run_tests()

    informe = generar_informe(resultados)
    ruta = "/home/osserver/Proyectos_Antigravity/Integraciones_OS/.agent/informes/benchmark_ollama_2026-03-29.md"
    with open(ruta, "w") as f:
        f.write(informe)

    # Resumen final
    total = len(resultados)
    ok = sum(1 for r in resultados if r["ok"])
    print(f"\n{'='*60}")
    print(f"  TOTAL: {ok}/{total} exitosos ({round(ok*100/total)}%)")
    print(f"  Informe: {ruta}")
    print(f"{'='*60}")
