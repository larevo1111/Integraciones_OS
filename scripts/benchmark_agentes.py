#!/usr/bin/env python3
"""
Benchmark comparativo de agentes IA — OS
Prueba 4 agentes en 2 roles: generador SQL y respuesta final.
Guarda resultados detallados para evaluación posterior.

Uso: python3 benchmark_agentes.py
"""

import requests, json, time, datetime, pymysql, os, sys

# ─── Config ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local
IA_URL     = "http://localhost:5100/ia/consultar"
DB_CONFIG  = dict(**cfg_local(), database="ia_service_os", charset="utf8mb4")
EMPRESA    = "ori_sil_2"
USUARIO    = "benchmark_test"
CANAL      = "api"

AGENTES_SQL      = ["gemini-flash", "gemini-flash-lite", "groq-llama", "gpt-oss-120b", "cerebras-llama"]
AGENTES_RESPUESTA = ["gemini-flash", "gemini-flash-lite", "groq-llama", "gpt-oss-120b", "cerebras-llama"]

OUTPUT_JSON = "/home/osserver/Proyectos_Antigravity/Integraciones_OS/.agent/benchmark_agentes_ronda3.json"
OUTPUT_MD   = "/home/osserver/Proyectos_Antigravity/Integraciones_OS/.agent/benchmark_agentes_ronda3.md"

# ─── Queries de prueba ───────────────────────────────────────────────────────
# (id, descripcion, query, tipo_esperado)
QUERIES_SQL = [
    ("SQL-01", "Ventas mes actual",
     "¿Cuánto vendimos en total este mes de marzo 2026?", "analisis_datos"),

    ("SQL-02", "Top canales febrero",
     "¿Cuál fue el top 3 de canales de venta en febrero 2026 por valor neto?", "analisis_datos"),

    ("SQL-03", "Producto más vendido",
     "¿Cuál fue el producto más vendido en unidades durante 2025?", "analisis_datos"),

    ("SQL-04", "Cartera vencida",
     "¿Cuánto hay en cartera vencida actualmente y cuáles son los 5 clientes con más deuda?", "analisis_datos"),

    ("SQL-05", "Stock inventario",
     "¿Cuánto stock tenemos actualmente de productos terminados?", "analisis_datos"),

    ("SQL-06", "Órdenes producción vigentes",
     "¿Cuántas órdenes de producción están vigentes y cuál es su valor total?", "analisis_datos"),

    ("SQL-07", "Remisiones pendientes",
     "¿Cuánto hay en remisiones pendientes de facturar y cuántas son?", "analisis_datos"),

    ("SQL-08", "Consignación activa",
     "¿Cuánto valor hay en consignación activa (órdenes de venta vigentes)?", "analisis_datos"),

    ("SQL-09", "Comparativo año anterior",
     "¿Cómo van las ventas de enero-marzo 2026 vs el mismo período de 2025?", "analisis_datos"),

    ("SQL-10", "Margen por canal",
     "¿Cuál es el margen promedio de cada canal de venta en los últimos 3 meses?", "analisis_datos"),

    ("SQL-11", "Clientes nuevos",
     "¿Cuántos clientes nuevos compraron por primera vez en lo que va del 2026?", "analisis_datos"),

    ("SQL-12", "Compras materia prima",
     "¿Cuánto hemos comprado en materia prima en lo que va del 2026?", "analisis_datos"),

    # ── Queries más complejas ──
    ("SQL-13", "Top 5 productos más rentables",
     "¿Cuáles son los 5 productos con mayor margen bruto en lo que va del 2026?", "analisis_datos"),

    ("SQL-14", "Evolución mensual ventas 6 meses",
     "Dame la evolución mes a mes de ventas netas en los últimos 6 meses", "analisis_datos"),

    ("SQL-15", "Clientes que compraron este año pero no el pasado",
     "¿Cuántos clientes compraron en 2026 pero no compraron nada en 2025?", "analisis_datos"),

    ("SQL-16", "Canal más rentable vs año anterior",
     "¿Qué canal tuvo el mayor crecimiento en ventas comparando enero-marzo 2026 vs enero-marzo 2025?", "analisis_datos"),

    ("SQL-17", "Productos sin movimiento",
     "¿Qué productos tienen stock en inventario pero no han tenido venta en los últimos 60 días?", "analisis_datos"),

    ("SQL-18", "Ticket promedio por canal",
     "¿Cuál es el ticket promedio de venta por canal en febrero y marzo 2026?", "analisis_datos"),
]

QUERIES_CONV = [
    ("CONV-01", "Estrategia precio",
     "¿Qué diferencia hay entre la tarifa distribuidor y la tarifa pública en OS?", "conversacion"),

    ("CONV-02", "Redacción email",
     "Redacta un mensaje corto de WhatsApp para avisar a un cliente que su pedido está listo para despacho.", "redaccion"),

    ("CONV-03", "Explicación sistema",
     "¿Qué tipos de consulta puedes hacer y cuáles requieren ir a la base de datos?", "conversacion"),

    ("CONV-04", "Redacción propuesta comercial",
     "Redacta un párrafo corto de propuesta comercial para un negocio nuevo interesado en nuestros chocolates, destacando calidad y origen natural.", "redaccion"),

    ("CONV-05", "Análisis estratégico",
     "Dado que nuestro canal mayorista creció más que el minorista este año, ¿qué riesgos o oportunidades debería considerar el equipo comercial?", "conversacion"),
]

# ─── Helpers BD ──────────────────────────────────────────────────────────────
def get_db():
    return pymysql.connect(**DB_CONFIG)

def set_agente_sql(slug):
    """Cambia el agente_sql del tipo analisis_datos en BD."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE ia_tipos_consulta SET agente_sql=%s WHERE slug='analisis_datos'", (slug,))
        conn.commit()

def restore_agente_sql():
    set_agente_sql("gemini-flash")

# ─── Llamada al servicio ──────────────────────────────────────────────────────
def llamar(pregunta, agente_override=None, tipo_override=None, canal_extra=""):
    payload = {
        "pregunta": pregunta,
        "usuario_id": f"{USUARIO}_{canal_extra}",
        "canal": CANAL,
        "empresa": EMPRESA,
    }
    if agente_override:
        payload["agente"] = agente_override
    if tipo_override:
        payload["tipo"] = tipo_override

    t0 = time.time()
    try:
        r = requests.post(IA_URL, json=payload, timeout=90)
        latencia = round((time.time() - t0) * 1000)
        data = r.json()
        return {
            "ok": data.get("ok", False),
            "respuesta": data.get("respuesta", ""),
            "sql": data.get("sql"),
            "tabla": data.get("tabla"),
            "tokens": data.get("tokens", {}),
            "costo_usd": data.get("costo_usd", 0),
            "agente_usado": data.get("agente", ""),
            "latencia_ms": latencia,
            "error": data.get("error", ""),
        }
    except Exception as e:
        return {
            "ok": False,
            "respuesta": "",
            "sql": None,
            "tabla": None,
            "tokens": {},
            "costo_usd": 0,
            "agente_usado": agente_override or "",
            "latencia_ms": round((time.time() - t0) * 1000),
            "error": str(e),
        }

# ─── Evaluación automática básica ────────────────────────────────────────────
def evaluar_sql(sql, resultado):
    """Heurísticas básicas: SQL bien formado, sin error, tiene filas."""
    if not sql:
        return "NO_SQL"
    sql_lower = sql.lower()
    if "select" not in sql_lower:
        return "INVALIDO"
    if resultado.get("error"):
        return "ERROR"
    tabla = resultado.get("tabla")
    if tabla and len(tabla) > 0:
        return "OK"
    if resultado.get("respuesta") and len(resultado["respuesta"]) > 50:
        return "OK_SIN_FILAS"
    return "VACIO"

def evaluar_respuesta(resultado):
    """Heurísticas: longitud, tiene datos numéricos, coherente."""
    if not resultado.get("ok"):
        return "FALLO"
    resp = resultado.get("respuesta", "")
    if len(resp) < 30:
        return "MUY_CORTA"
    if len(resp) > 100:
        return "OK"
    return "CORTA"

# ─── FASE 1: SQL Generation Benchmark ────────────────────────────────────────
def fase1_sql():
    print("\n" + "="*70)
    print("FASE 1 — Generadores de SQL (forzando agente_sql en BD)")
    print("="*70)

    resultados = []

    for agente in AGENTES_SQL:
        print(f"\n  ▶ Agente SQL: {agente}")
        set_agente_sql(agente)
        time.sleep(0.5)  # Pequeña pausa para que el cambio en BD se estabilice

        for qid, desc, query, _ in QUERIES_SQL:
            print(f"    {qid} — {desc}...", end=" ", flush=True)
            # Forzamos gemini-flash como agente de respuesta (no nos interesa aquí)
            res = llamar(query, agente_override="gemini-flash", canal_extra=f"sql_{agente}")
            calidad_sql = evaluar_sql(res.get("sql"), res)
            n_filas = len(res.get("tabla") or [])

            registro = {
                "fase": "SQL",
                "query_id": qid,
                "descripcion": desc,
                "agente": agente,
                "ok": res["ok"],
                "calidad_sql": calidad_sql,
                "sql_generado": (res.get("sql") or "")[:500],  # truncar
                "n_filas": n_filas,
                "latencia_ms": res["latencia_ms"],
                "tokens": res["tokens"],
                "costo_usd": res["costo_usd"],
                "error": res["error"],
                "respuesta_breve": res["respuesta"][:200],
            }
            resultados.append(registro)
            print(f"{calidad_sql} | {n_filas} filas | {res['latencia_ms']}ms")
            time.sleep(1)  # Pausa entre calls

    restore_agente_sql()
    return resultados

# ─── FASE 2: Response Quality Benchmark ──────────────────────────────────────
def fase2_respuesta():
    print("\n" + "="*70)
    print("FASE 2 — Calidad de respuesta (forzando agente_preferido)")
    print("="*70)

    resultados = []
    todas_queries = QUERIES_SQL[:8] + QUERIES_CONV  # 8 SQL + 5 conversación

    for agente in AGENTES_RESPUESTA:
        print(f"\n  ▶ Agente respuesta: {agente}")

        for qid, desc, query, tipo in todas_queries:
            print(f"    {qid} — {desc}...", end=" ", flush=True)
            res = llamar(query, agente_override=agente, canal_extra=f"resp_{agente}")
            calidad_resp = evaluar_respuesta(res)
            n_filas = len(res.get("tabla") or [])
            tiene_sql = bool(res.get("sql"))

            registro = {
                "fase": "RESPUESTA",
                "query_id": qid,
                "descripcion": desc,
                "agente": agente,
                "ok": res["ok"],
                "calidad_resp": calidad_resp,
                "tiene_sql": tiene_sql,
                "n_filas": n_filas,
                "latencia_ms": res["latencia_ms"],
                "tokens": res["tokens"],
                "costo_usd": res["costo_usd"],
                "error": res["error"],
                "respuesta_completa": res["respuesta"],  # Guardar completa para revisión
                "sql_generado": (res.get("sql") or "")[:300],
            }
            resultados.append(registro)
            print(f"{calidad_resp} | sql={'SI' if tiene_sql else 'NO'} | {res['latencia_ms']}ms")
            time.sleep(1)

    return resultados

# ─── Guardar resultados ───────────────────────────────────────────────────────
def guardar_json(resultados_sql, resultados_resp):
    output = {
        "fecha": datetime.datetime.now().isoformat(),
        "agentes_sql_testados": AGENTES_SQL,
        "agentes_respuesta_testados": AGENTES_RESPUESTA,
        "fase1_sql": resultados_sql,
        "fase2_respuesta": resultados_resp,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON guardado: {OUTPUT_JSON}")

def guardar_markdown(resultados_sql, resultados_resp):
    lines = []
    lines.append("# Benchmark de Agentes IA — Origen Silvestre")
    lines.append(f"**Fecha:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Agentes SQL testados:** {', '.join(AGENTES_SQL)}")
    lines.append(f"**Agentes respuesta testados:** {', '.join(AGENTES_RESPUESTA)}")
    lines.append("")

    # ── Resumen SQL por agente ──
    lines.append("---\n## FASE 1 — Generación de SQL\n")
    lines.append("| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |")
    lines.append("|---|---|---|---|---|---|")

    for qid, desc, _, _ in QUERIES_SQL:
        row = [qid, desc[:40]]
        for agente in AGENTES_SQL:
            match = next((r for r in resultados_sql if r["query_id"]==qid and r["agente"]==agente), None)
            if match:
                cal = match["calidad_sql"]
                lat = match["latencia_ms"]
                filas = match["n_filas"]
                row.append(f"{cal} / {filas}f / {lat}ms")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")

    # ── Latencia y costo SQL ──
    lines.append("\n### Latencia y costo promedio — SQL\n")
    lines.append("| Agente | Latencia prom (ms) | Costo total USD | SQL OK% |")
    lines.append("|---|---|---|---|")
    for agente in AGENTES_SQL:
        regs = [r for r in resultados_sql if r["agente"]==agente]
        if regs:
            lat_prom = round(sum(r["latencia_ms"] for r in regs) / len(regs))
            costo = round(sum(r["costo_usd"] for r in regs), 6)
            ok_pct = round(sum(1 for r in regs if r["calidad_sql"] in ("OK","OK_SIN_FILAS")) / len(regs) * 100)
            lines.append(f"| {agente} | {lat_prom} | ${costo} | {ok_pct}% |")

    # ── SQL generados ──
    lines.append("\n### SQL generados por query y agente\n")
    for qid, desc, query, _ in QUERIES_SQL:
        lines.append(f"\n#### {qid} — {desc}")
        lines.append(f"**Pregunta:** {query}\n")
        for agente in AGENTES_SQL:
            match = next((r for r in resultados_sql if r["query_id"]==qid and r["agente"]==agente), None)
            if match:
                lines.append(f"**{agente}** ({match['calidad_sql']} / {match['n_filas']} filas / {match['latencia_ms']}ms):")
                sql = match["sql_generado"] or "(sin SQL)"
                lines.append(f"```sql\n{sql}\n```")
                if match["error"]:
                    lines.append(f"> ⚠️ Error: {match['error']}")
            else:
                lines.append(f"**{agente}**: — (sin datos)")

    # ── Resumen RESPUESTA ──
    lines.append("\n---\n## FASE 2 — Calidad de Respuesta\n")
    todas_q_ids = [q[0] for q in QUERIES_SQL[:6]] + [q[0] for q in QUERIES_CONV]
    todas_q_desc = {q[0]: q[1] for q in QUERIES_SQL + QUERIES_CONV}

    lines.append("| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |")
    lines.append("|---|---|---|---|---|---|")
    for qid in todas_q_ids:
        row = [qid, todas_q_desc.get(qid,"")[:40]]
        for agente in AGENTES_RESPUESTA:
            match = next((r for r in resultados_resp if r["query_id"]==qid and r["agente"]==agente), None)
            if match:
                cal = match["calidad_resp"]
                lat = match["latencia_ms"]
                row.append(f"{cal} / {lat}ms")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n### Latencia y costo promedio — Respuesta\n")
    lines.append("| Agente | Latencia prom (ms) | Costo total USD | Resp OK% |")
    lines.append("|---|---|---|---|")
    for agente in AGENTES_RESPUESTA:
        regs = [r for r in resultados_resp if r["agente"]==agente]
        if regs:
            lat_prom = round(sum(r["latencia_ms"] for r in regs) / len(regs))
            costo = round(sum(r["costo_usd"] for r in regs), 6)
            ok_pct = round(sum(1 for r in regs if r["calidad_resp"] == "OK") / len(regs) * 100)
            lines.append(f"| {agente} | {lat_prom} | ${costo} | {ok_pct}% |")

    # ── Respuestas completas ──
    lines.append("\n### Respuestas completas por query y agente\n")
    todas_queries_obj = {q[0]: q for q in QUERIES_SQL + QUERIES_CONV}
    for qid in todas_q_ids:
        q = todas_queries_obj.get(qid)
        if not q:
            continue
        lines.append(f"\n#### {qid} — {q[1]}")
        lines.append(f"**Pregunta:** {q[2]}\n")
        for agente in AGENTES_RESPUESTA:
            match = next((r for r in resultados_resp if r["query_id"]==qid and r["agente"]==agente), None)
            if match:
                lines.append(f"**{agente}** ({match['calidad_resp']} / {match['latencia_ms']}ms):")
                lines.append(f"> {match['respuesta_completa'][:800]}")
                if match["error"]:
                    lines.append(f"> ⚠️ Error: {match['error']}")
            else:
                lines.append(f"**{agente}**: — (sin datos)")
        lines.append("")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown guardado: {OUTPUT_MD}")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Benchmark de Agentes IA — Origen Silvestre")
    print(f"   Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Agentes SQL: {AGENTES_SQL}")
    print(f"   Agentes Respuesta: {AGENTES_RESPUESTA}")
    print(f"   Queries SQL: {len(QUERIES_SQL)} | Conversación: {len(QUERIES_CONV)}")
    print(f"   Total llamadas estimadas: ~{len(AGENTES_SQL)*len(QUERIES_SQL) + len(AGENTES_RESPUESTA)*(len(QUERIES_SQL[:6])+len(QUERIES_CONV))}")

    try:
        res_sql  = fase1_sql()
        res_resp = fase2_respuesta()
        guardar_json(res_sql, res_resp)
        guardar_markdown(res_sql, res_resp)

        print("\n" + "="*70)
        print("✅ BENCHMARK COMPLETO")
        print(f"   Resultados: {OUTPUT_MD}")
        print(f"   JSON: {OUTPUT_JSON}")

    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido. Restaurando agente_sql original...")
        restore_agente_sql()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        restore_agente_sql()
        raise
    finally:
        restore_agente_sql()
