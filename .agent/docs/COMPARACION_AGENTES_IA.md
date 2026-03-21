# Comparación de Agentes IA — Origen Silvestre

**Fecha del benchmark:** 2026-03-20
**Ejecutado por:** Claude Code (Sonnet 4.6)
**Script:** `scripts/benchmark_agentes.py`
**Datos crudos:** `.agent/benchmark_agentes_2026-03-20.json` + `.agent/benchmark_agentes_ronda3.json`

---

## Objetivo

Determinar el mejor agente para cada rol del sistema:
1. **Generador de SQL** — convierte preguntas en lenguaje natural a SQL ejecutable contra Hostinger
2. **Agente de respuesta** — interpreta los datos y redacta la respuesta final al usuario

---

## Agentes evaluados

| Agente | Modelo | Proveedor | Costo input | Costo output | RPD |
|---|---|---|---|---|---|
| gemini-flash | Gemini 2.5 Flash | Google | $0.075/M | $0.30/M | 10,000 |
| gemini-flash-lite | Gemini 2.5 Flash Lite | Google | $0.0375/M | $0.15/M | ilimitado |
| groq-llama | Llama 3.3 70B | Groq | **$0.00** | **$0.00** | 14,400 |
| gpt-oss-120b | GPT-OSS 120B | Groq | $0.15/M | $0.60/M | 1,000 |
| cerebras-llama | Llama 3.1 8B | Cerebras | $0.10/M | $0.10/M | ilimitado |

---

## Metodología

### Rondas
- **Ronda 1 + 2**: 12 queries SQL + 3 conversación → 4 agentes iniciales (sin cerebras)
- **Ronda 3**: 18 queries SQL + 5 conversación → 5 agentes (incluye cerebras)
- **Total acumulado**: 30 pruebas SQL + 22 pruebas de respuesta por agente

### Tipos de query testeados

**SQL (18 queries):**
- Ventas mes actual, top canales, producto más vendido
- Cartera vencida (top 5 clientes)
- Stock inventario, órdenes producción vigentes
- Remisiones pendientes, consignación activa
- Comparativo año anterior, margen por canal
- Clientes nuevos, compras materia prima
- Top 5 productos más rentables *(compleja)*
- Evolución mensual 6 meses *(compleja)*
- Clientes nuevos vs año anterior *(compleja)*
- Canal con mayor crecimiento YoY *(compleja)*
- Productos sin movimiento 60 días *(compleja)*
- Ticket promedio por canal *(compleja)*

**Conversación/redacción (5 queries):**
- Estrategia de precios (tarifas OS)
- Redacción mensaje WhatsApp despacho
- Explicación del sistema IA
- Propuesta comercial chocolates
- Análisis estratégico canal mayorista

### Calificación SQL
- `OK` — SQL ejecutado con filas reales
- `ERROR` — SQL ejecutado pero error de sintaxis/columna
- `NO_SQL` — agente respondió sin generar SQL (usó caché o contexto)

### Calificación Respuesta
- `OK` — respuesta completa y elaborada
- `CORTA` — respuesta correcta pero muy breve (menos de 100 chars)
- `FALLO` — error o sin respuesta

---

## Resultados — Generación de SQL

**30 pruebas por agente (rondas 1+2+3)**

| Agente | OK | ERR | NO_SQL | **Éxito %** | Lat. prom | Gratis |
|---|---|---|---|---|---|---|
| **gemini-flash** | 28 | 0 | 2 | **93%** | **13.0s** ✅ | No |
| gemini-flash-lite | 26 | 0 | 4 | 87% | **11.2s** ✅ | No |
| **groq-llama** | 29 | 0 | 1 | **97%** | 19.2s | **Sí** ✅ |
| gpt-oss-120b | 28 | 1 | 1 | 93% | 19.2s | No |
| **cerebras-llama** | 29 | 1 | 0 | **97%** | 19.7s | No |

### Errores específicos SQL

| Agente | Query | Fallo | Explicación |
|---|---|---|---|
| gemini-flash | Clientes nuevos | NO_SQL | Responde sin SQL cuando la pregunta involucra comparación con año anterior (usa caché) |
| gemini-flash-lite | Stock, Clientes nuevos | NO_SQL (×2) | Responde desde contexto más frecuentemente — modelo más conservador |
| gemini-flash-lite | Cartera vencida | ERROR (ronda 1) | Subquery con múltiples columnas donde solo se permite 1 — error de sintaxis |
| groq-llama | Canal crecimiento YoY | NO_SQL | No genera SQL para comparativos muy complejos con múltiples CTEs |
| groq-llama | Compras materia prima | ERROR (ronda 1) | Inventó columna `fcd.categoria_articulo` inexistente |
| gpt-oss-120b | Compras materia prima | ERROR (×2) | Misma columna inventada — patrón consistente en esta query |
| cerebras-llama | Compras materia prima | ERROR (ronda 3) | Mismo patrón — tabla con múltiples JOINs compleja para modelos 8B |

### ¿Por qué Groq no es más rápido en SQL?

Groq genera tokens de SALIDA a 2,000+ t/s — eso es su ventaja. Pero para generar SQL el agente recibe **~28,000 tokens de ENTRADA** (DDL de 53 tablas). El cuello de botella es procesar esa entrada masiva, no escribir la salida. Gemini Flash está mejor optimizado para contextos de entrada grandes, por eso es 6s más rápido.

Para el enrutador (entrada ~500 tokens, salida ~50 tokens), Groq SÍ domina — responde en 300ms.

---

## Resultados — Calidad de Respuesta

**22 pruebas por agente (rondas 2+3)**

| Agente | OK | CORTA | **Éxito %** | Lat. prom | Lat. solo conv. | Costo/22q |
|---|---|---|---|---|---|---|
| gemini-flash | 20 | 2 | 91% | 9.5s | 8.6s | $0.076 |
| gemini-flash-lite | 19 | 3 | 86% | **7.1s** ✅ | **4.4s** ✅ | **$0.034** ✅ |
| groq-llama | 20 | 2 | 91% | 9.8s | 7.8s | $0.069 |
| gpt-oss-120b | **22** | 0 | **100%** | 15.1s | 9.3s | $0.157 |
| **cerebras-llama** | **22** | 0 | **100%** | 10.9s | **5.6s** ✅ | $0.081 |

### Observaciones de calidad

| Agente | Fortalezas | Debilidades |
|---|---|---|
| gemini-flash | Respuestas bien estructuradas | Empieza con "¡Hola!" innecesario. CORTA en respuestas de 1 dato |
| gemini-flash-lite | Más directo, tablas markdown nativas | Respuestas insuficientemente elaboradas en queries complejas (3 CORTA) |
| groq-llama | Correcto para datos simples | Usa ``` code blocks en vez de tablas markdown nativas |
| gpt-oss-120b | Mejor formato, incluye IDs y contexto extra | Más lento (15s), más caro ($0.157/22q) |
| **cerebras-llama** | 100% éxito, tablas markdown, conversación en 5.6s | Modelo 8B — puede ser menos sofisticado en análisis muy complejos |

### El caso de las respuestas CORTA

Las 2–3 respuestas "CORTA" de flash/flash-lite/groq ocurrieron principalmente en **"Stock inventario"** — donde la respuesta correcta es simplemente `"1,098 unidades de productos terminados"`. El evaluador automático marcó estas como CORTA por longitud, pero la respuesta ERA correcta. En la práctica el impacto es menor.

---

## Decisión Final (2026-03-20)

### Configuración aplicada

| Rol | Antes | Después | Motivo |
|---|---|---|---|
| Enrutador | groq-llama | groq-llama *(sin cambio)* | Perfecto para entrada pequeña, 300ms, gratis |
| Generador SQL | gemini-flash | gemini-flash *(sin cambio)* | Más rápido (13s), 93% éxito, confiable |
| **Agente respuesta** | **gemini-flash** | **cerebras-llama** | 100% vs 91%, mismo costo (~$0.08 vs $0.076), conversación 5.6s |
| **Fallback respuesta** | **deepseek-chat** | **gemini-flash-lite** | RPD ilimitado, más barato ($0.034 vs deepseek), cubre emergencias |

### Cómo se aplicó

**BD `ia_service_os`:**
```sql
-- Agente respuesta
UPDATE ia_tipos_consulta
SET agente_preferido = 'cerebras-llama',
    agente_fallback  = 'gemini-flash-lite'
WHERE slug IN ('analisis_datos','conversacion','redaccion','resumen',
               'aprendizaje','busqueda_web','generacion_documento');
```

**Bot Telegram (`teclado.py`):**
- cerebras-llama agregado como `★ recomendado` en menú de ajustes
- gemini-flash pasa a segunda opción

---

## Cuándo revisar este benchmark

- Si se agrega un agente nuevo al sistema
- Si hay cambios mayores en los modelos (nueva versión de Gemini, Llama, etc.)
- Si la calidad percibida baja notablemente en producción
- Sugerido: cada 3 meses

**Para re-ejecutar:**
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts
python3 benchmark_agentes.py
```
