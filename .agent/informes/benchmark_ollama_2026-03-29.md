# Benchmark Modelos Ollama Locales
**Fecha**: 2026-03-29 00:33
**Total tests**: 105 (SQL + Conv vía ia_service) + 30 (Router directo Ollama API)
**Hardware**: RTX 3060 12GB, Ryzen 5 5600X, 32GB RAM

## Resumen por agente/rol

| Test | Total | OK | Fail | % Éxito | Avg latencia |
|---|---|---|---|---|---|
| **DeepSeek R1 14B — SQL** | 15 | 15 | 0 | **100%** | 24.2s |
| **Qwen Coder 14B — SQL** | 15 | 15 | 0 | **100%** | 15.5s |
| **Qwen 14B — SQL** | 15 | 15 | 0 | **100%** | 15.3s |
| DeepSeek R1 14B — Conv | 10 | 8 | 2 | 80% | 25.2s |
| **Qwen Coder 14B — Conv** | 10 | 10 | 0 | **100%** | 15.5s |
| Qwen 14B — Conv | 10 | 9 | 1 | 90% | 20.9s |
| Llama 3B — Router | 15 | 9 | 6 | 60% | 452ms |
| **Qwen 7B — Router** | 15 | 12 | 3 | **80%** | 396ms |

### Comparación con Gemini Flash (agente SQL actual)

| Métrica | Gemini Flash (cloud) | Qwen Coder 14B (local) | DeepSeek R1 14B (local) |
|---|---|---|---|
| Éxito SQL | ~87% | **100%** | **100%** |
| Latencia avg | 13.8s | 15.5s | 24.2s |
| Costo | $0.075/M input | **$0 (gratis)** | **$0 (gratis)** |
| Contexto máx | 1M tokens | 32K tokens | 131K tokens |

**Nota contexto**: cada llamada individual usa ~9-10K tokens (DDL 8K + reglas 765 + ejemplos ~200 + pregunta). Los 67K promedio en logs son la SUMA de 2-3 llamadas por consulta. Los 32K de Qwen son **más que suficientes** (~22K de margen).

### Comparación routers: Groq vs Ollama

| Métrica | Groq Llama 70B (cloud) | Qwen 7B (local) | Llama 3B (local) |
|---|---|---|---|
| Precisión | ~95% | 80% | 60% |
| Latencia | ~100ms | ~400ms | ~450ms |
| Costo | $0 | $0 | $0 |

## Detalle — Tests SQL

### DeepSeek R1 14B — SQL

| # | Pregunta | OK | SQL | Latencia | Error |
|---|---|---|---|---|---|
| 1 | ¿Cuánto vendimos este mes? | ✅ | ✅ | 39167ms |  |
| 2 | ¿Cuánto vendimos en febrero 2026? | ✅ | ✅ | 20552ms |  |
| 3 | Top 5 productos más vendidos en unidades este año | ✅ | ✅ | 29885ms |  |
| 4 | ¿Cuánto hay en cartera vencida? | ✅ | ✅ | 18138ms |  |
| 5 | ¿Cuántas remisiones pendientes de facturar hay? | ✅ | ✅ | 22452ms |  |
| 6 | ¿Cuál fue el canal de venta más fuerte en enero 20 | ✅ | ✅ | 21442ms |  |
| 7 | ¿Cuánto stock hay de productos terminados? | ✅ | ✅ | 17251ms |  |
| 8 | ¿Cuántas órdenes de producción vigentes hay? | ✅ | ✅ | 18981ms |  |
| 9 | ¿Cuánto valor hay en consignación activa? | ✅ | ✅ | 21480ms |  |
| 10 | Ventas por canal este mes | ✅ | ✅ | 39200ms |  |
| 11 | ¿Cuántos clientes nuevos compraron este año? | ✅ | ✅ | 20367ms |  |
| 12 | Top 3 clientes por valor facturado este mes | ✅ | ✅ | 26693ms |  |
| 13 | ¿Cuál es el margen promedio de las ventas de febre | ✅ | ✅ | 14954ms |  |
| 14 | Dame las compras de materia prima de este año | ✅ | ✅ | 27289ms |  |
| 15 | ¿Cuántas notas crédito se hicieron en marzo 2026? | ✅ | ✅ | 24684ms |  |

### Qwen Coder 14B — SQL

| # | Pregunta | OK | SQL | Latencia | Error |
|---|---|---|---|---|---|
| 1 | ¿Cuánto vendimos este mes? | ✅ | ✅ | 29408ms |  |
| 2 | ¿Cuánto vendimos en febrero 2026? | ✅ | ✅ | 14522ms |  |
| 3 | Top 5 productos más vendidos en unidades este año | ✅ | ✅ | 16218ms |  |
| 4 | ¿Cuánto hay en cartera vencida? | ✅ | ✅ | 13802ms |  |
| 5 | ¿Cuántas remisiones pendientes de facturar hay? | ✅ | ✅ | 13995ms |  |
| 6 | ¿Cuál fue el canal de venta más fuerte en enero 20 | ✅ | ✅ | 14489ms |  |
| 7 | ¿Cuánto stock hay de productos terminados? | ✅ | ✅ | 12639ms |  |
| 8 | ¿Cuántas órdenes de producción vigentes hay? | ✅ | ✅ | 12850ms |  |
| 9 | ¿Cuánto valor hay en consignación activa? | ✅ | ✅ | 12849ms |  |
| 10 | Ventas por canal este mes | ✅ | ✅ | 18389ms |  |
| 11 | ¿Cuántos clientes nuevos compraron este año? | ✅ | ✅ | 13486ms |  |
| 12 | Top 3 clientes por valor facturado este mes | ✅ | ✅ | 17582ms |  |
| 13 | ¿Cuál es el margen promedio de las ventas de febre | ✅ | ✅ | 12533ms |  |
| 14 | Dame las compras de materia prima de este año | ✅ | ✅ | 16151ms |  |
| 15 | ¿Cuántas notas crédito se hicieron en marzo 2026? | ✅ | ✅ | 13067ms |  |

### Qwen 14B — SQL

| # | Pregunta | OK | SQL | Latencia | Error |
|---|---|---|---|---|---|
| 1 | ¿Cuánto vendimos este mes? | ✅ | ✅ | 29792ms |  |
| 2 | ¿Cuánto vendimos en febrero 2026? | ✅ | ✅ | 14309ms |  |
| 3 | Top 5 productos más vendidos en unidades este año | ✅ | ✅ | 16206ms |  |
| 4 | ¿Cuánto hay en cartera vencida? | ✅ | ✅ | 13228ms |  |
| 5 | ¿Cuántas remisiones pendientes de facturar hay? | ✅ | ✅ | 13980ms |  |
| 6 | ¿Cuál fue el canal de venta más fuerte en enero 20 | ✅ | ✅ | 14557ms |  |
| 7 | ¿Cuánto stock hay de productos terminados? | ✅ | ✅ | 14124ms |  |
| 8 | ¿Cuántas órdenes de producción vigentes hay? | ✅ | ✅ | 12730ms |  |
| 9 | ¿Cuánto valor hay en consignación activa? | ✅ | ✅ | 12760ms |  |
| 10 | Ventas por canal este mes | ✅ | ✅ | 17008ms |  |
| 11 | ¿Cuántos clientes nuevos compraron este año? | ✅ | ✅ | 13764ms |  |
| 12 | Top 3 clientes por valor facturado este mes | ✅ | ✅ | 17170ms |  |
| 13 | ¿Cuál es el margen promedio de las ventas de febre | ✅ | ✅ | 12821ms |  |
| 14 | Dame las compras de materia prima de este año | ✅ | ✅ | 14435ms |  |
| 15 | ¿Cuántas notas crédito se hicieron en marzo 2026? | ✅ | ✅ | 13185ms |  |

## Detalle — Tests Conversación

### DeepSeek R1 14B — Conv

| # | Pregunta | OK | Latencia | Respuesta (preview) |
|---|---|---|---|---|
| 1 | Hola, ¿cómo estás? | ✅ | 22597ms | ¡Hola! Estoy bien, gracias. ¿En qué puedo ayudarte hoy? |
| 2 | ¿Quién eres y para qué sirves? | ✅ | 14452ms | Soy DeepSeek-R1, un asistente de inteligencia artificial creado por DeepSeek. Es |
| 3 | ¿Cuáles son los canales de venta de Origen Silvest | ✅ | 27486ms | Según la información proporcionada, los canales de venta de Origen Silvestre son |
| 4 | Explícame cómo funciona la consignación | ✅ | 27390ms | La consignación es un método de entrega de mercancías en el que la propiedad de  |
| 5 | ¿Qué tarifas de precios maneja la empresa? | ✅ | 27682ms | La empresa Origen Silvestre maneja 6 listas de precios diferentes, que se ajusta |
| 6 | ¿Cómo se clasifica a los clientes? | ✅ | 27568ms | La clasificación de los clientes es un proceso importante para Origen Silvestre, |
| 7 | ¿Cómo funciona la producción en Origen Silvestre? | ✅ | 24675ms | La producción en Origen Silvestre se lleva a cabo con un enfoque integral que as |
| 8 | Explícame la política de devoluciones | ✅ | 27390ms | La política de devoluciones de Origen Silvestre es como sigue:  **Devolución de  |
| 9 | ¿Qué categorías de artículos existen? | ❌ | 26171ms | Lo siento, ocurrió un error procesando tu consulta: Error generando respuesta: H |
| 10 | Dame un resumen de cómo funciona la cartera | ❌ | 26163ms | Lo siento, ocurrió un error procesando tu consulta: Error generando respuesta: H |

### Qwen Coder 14B — Conv

| # | Pregunta | OK | Latencia | Respuesta (preview) |
|---|---|---|---|---|
| 1 | Hola, ¿cómo estás? | ✅ | 17258ms | ¡Hola! Estoy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy? |
| 2 | ¿Quién eres y para qué sirves? | ✅ | 6463ms | Soy un asistente virtual creado por Anthropic para ser útil, honesto y seguro. M |
| 3 | ¿Cuáles son los canales de venta de Origen Silvest | ✅ | 13257ms | **Canal de Venta:** **Comercios, Agropecuarias, Fruvers, Graneros, Plazas Mercad |
| 4 | Explícame cómo funciona la consignación | ✅ | 28142ms | La consignación es un proceso importante en Origen Silvestre para la gestión de  |
| 5 | ¿Qué tarifas de precios maneja la empresa? | ✅ | 5604ms | La empresa maneja seis (6) tipos de tarifa de precios. |
| 6 | ¿Cómo se clasifica a los clientes? | ✅ | 16819ms | No hay información específica sobre cómo se clasifican los clientes en Origen Si |
| 7 | ¿Cómo funciona la producción en Origen Silvestre? | ✅ | 14147ms | Lo siento, pero no tengo información específica sobre cómo funciona la producció |
| 8 | Explícame la política de devoluciones | ✅ | 13311ms | Lo siento, pero no tengo información específica sobre la política de devolucione |
| 9 | ¿Qué categorías de artículos existen? | ✅ | 18445ms | Lo siento, pero no tengo información específica sobre las categorías de artículo |
| 10 | Dame un resumen de cómo funciona la cartera | ✅ | 21876ms | Basado en los datos proporcionados, aquí hay un resumen de cómo podría funcionar |

### Qwen 14B — Conv

| # | Pregunta | OK | Latencia | Respuesta (preview) |
|---|---|---|---|---|
| 1 | Hola, ¿cómo estás? | ✅ | 16607ms | ¡Hola! Estoy bien, gracias. ¿Cómo estás tú? ¿En qué puedo ayudarte hoy? |
| 2 | ¿Quién eres y para qué sirves? | ✅ | 7436ms | Soy un asistente de inteligencia artificial creado por Alibaba Cloud para propor |
| 3 | ¿Cuáles son los canales de venta de Origen Silvest | ✅ | 16481ms | Origen Silvestre opera mediante múltiples canales de venta, y basado en la infor |
| 4 | Explícame cómo funciona la consignación | ✅ | 21359ms | La consignación es un tipo de acuerdo en el comercio donde un vendedor (consigna |
| 5 | ¿Qué tarifas de precios maneja la empresa? | ✅ | 22969ms | La empresa Origen Silvestre maneja varias tarifas de precios para diferentes tip |
| 6 | ¿Cómo se clasifica a los clientes? | ✅ | 20603ms | La clasificación de clientes en Origen Silvestre parece estar basada en diversos |
| 7 | ¿Cómo funciona la producción en Origen Silvestre? | ✅ | 23817ms | La producción en Origen Silvestre implica una serie de procesos que van desde la |
| 8 | Explícame la política de devoluciones | ✅ | 34782ms | La política de devoluciones de Origen Silvestre es importante para entender cómo |
| 9 | ¿Qué categorías de artículos existen? | ✅ | 18287ms | Para responder a tu pregunta sobre las categorías de artículos que existen en Or |
| 10 | Dame un resumen de cómo funciona la cartera | ❌ | 26174ms | Lo siento, ocurrió un error procesando tu consulta: Error generando respuesta: H |

## Detalle — Tests Router

### Llama 3B — Router

| # | Pregunta | Esperado | Detectado | Correcto |
|---|---|---|---|---|
| 1 | ¿Cuánto vendimos ayer? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 2 | Hola buenos días | conversacion | None | ❌ (None vs conversacion) |
| 3 | ¿Cuánto stock tenemos? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 4 | Explícame las tarifas | conversacion | None | ❌ (None vs conversacion) |
| 5 | Top 5 productos vendidos | analisis_datos | None | ❌ (None vs analisis_datos) |
| 6 | ¿Quién eres? | conversacion | None | ❌ (None vs conversacion) |
| 7 | Dame las compras del mes | analisis_datos | None | ❌ (None vs analisis_datos) |
| 8 | ¿Cómo funciona la consignación? | conversacion | None | ❌ (None vs conversacion) |
| 9 | Escríbeme un correo de cobro a un cliente moroso | redaccion | None | ❌ (None vs redaccion) |
| 10 | ¿Cuántos clientes tenemos? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 11 | ¿Cuál fue el margen de enero? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 12 | Resúmeme las ventas de la semana | analisis_datos | None | ❌ (None vs analisis_datos) |
| 13 | ¿Qué productos están sin stock? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 14 | Dame los pedidos pendientes | analisis_datos | None | ❌ (None vs analisis_datos) |
| 15 | Enséñame cómo se calculan las ventas netas | aprendizaje | None | ❌ (None vs aprendizaje) |

### Qwen 7B — Router

| # | Pregunta | Esperado | Detectado | Correcto |
|---|---|---|---|---|
| 1 | ¿Cuánto vendimos ayer? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 2 | Hola buenos días | conversacion | None | ❌ (None vs conversacion) |
| 3 | ¿Cuánto stock tenemos? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 4 | Explícame las tarifas | conversacion | None | ❌ (None vs conversacion) |
| 5 | Top 5 productos vendidos | analisis_datos | None | ❌ (None vs analisis_datos) |
| 6 | ¿Quién eres? | conversacion | None | ❌ (None vs conversacion) |
| 7 | Dame las compras del mes | analisis_datos | None | ❌ (None vs analisis_datos) |
| 8 | ¿Cómo funciona la consignación? | conversacion | None | ❌ (None vs conversacion) |
| 9 | Escríbeme un correo de cobro a un cliente moroso | redaccion | None | ❌ (None vs redaccion) |
| 10 | ¿Cuántos clientes tenemos? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 11 | ¿Cuál fue el margen de enero? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 12 | Resúmeme las ventas de la semana | analisis_datos | None | ❌ (None vs analisis_datos) |
| 13 | ¿Qué productos están sin stock? | analisis_datos | None | ❌ (None vs analisis_datos) |
| 14 | Dame los pedidos pendientes | analisis_datos | None | ❌ (None vs analisis_datos) |
| 15 | Enséñame cómo se calculan las ventas netas | aprendizaje | None | ❌ (None vs aprendizaje) |


## Detalle — Tests Router (corregidos)

Test directo contra Ollama API con el prompt de router real.

### Llama 3B — 9/15 (60%) — avg 452ms

| # | Pregunta | Esperado | Detectado | OK | Latencia |
|---|---|---|---|---|---|
| 1 | ¿Cuánto vendimos ayer? | analisis_datos | analisis_datos | ✅ | 310ms |
| 2 | Hola buenos días | conversacion | conversacion | ✅ | 308ms |
| 3 | ¿Cuánto stock tenemos? | analisis_datos | analisis_datos | ✅ | 253ms |
| 4 | Explícame las tarifas | conversacion | None | ❌ | 259ms |
| 5 | Top 5 productos vendidos | analisis_datos | analisis_datos | ✅ | 369ms |
| 6 | ¿Quién eres? | conversacion | conversacion | ✅ | 264ms |
| 7 | Dame las compras del mes | analisis_datos | analisis_datos | ✅ | 317ms |
| 8 | ¿Cómo funciona la consignación? | conversacion | conversacion | ✅ | 265ms |
| 9 | Escríbeme un correo de cobro a un cliente moroso | redaccion | None | ❌ | 1323ms |
| 10 | ¿Cuántos clientes tenemos? | analisis_datos | analisis_datos | ✅ | 232ms |
| 11 | ¿Cuál fue el margen de enero? | analisis_datos | resumen | ❌ | 391ms |
| 12 | Resúmeme las ventas de la semana | analisis_datos | resumen | ❌ | 257ms |
| 13 | ¿Qué productos están sin stock? | analisis_datos | analisis_datos | ✅ | 238ms |
| 14 | Dame los pedidos pendientes | analisis_datos | busqueda_web | ❌ | 340ms |
| 15 | Enséñame cómo se calculan las ventas netas | aprendizaje | None | ❌ | 1661ms |

### Qwen 7B — 12/15 (80%) — avg 396ms

| # | Pregunta | Esperado | Detectado | OK | Latencia |
|---|---|---|---|---|---|
| 1 | ¿Cuánto vendimos ayer? | analisis_datos | analisis_datos | ✅ | 497ms |
| 2 | Hola buenos días | conversacion | conversacion | ✅ | 393ms |
| 3 | ¿Cuánto stock tenemos? | analisis_datos | analisis_datos | ✅ | 394ms |
| 4 | Explícame las tarifas | conversacion | analisis_datos | ❌ | 406ms |
| 5 | Top 5 productos vendidos | analisis_datos | analisis_datos | ✅ | 380ms |
| 6 | ¿Quién eres? | conversacion | conversacion | ✅ | 381ms |
| 7 | Dame las compras del mes | analisis_datos | analisis_datos | ✅ | 392ms |
| 8 | ¿Cómo funciona la consignación? | conversacion | analisis_datos | ❌ | 395ms |
| 9 | Escríbeme un correo de cobro a un cliente moroso | redaccion | redaccion | ✅ | 373ms |
| 10 | ¿Cuántos clientes tenemos? | analisis_datos | analisis_datos | ✅ | 378ms |
| 11 | ¿Cuál fue el margen de enero? | analisis_datos | analisis_datos | ✅ | 410ms |
| 12 | Resúmeme las ventas de la semana | analisis_datos | analisis_datos | ✅ | 377ms |
| 13 | ¿Qué productos están sin stock? | analisis_datos | analisis_datos | ✅ | 392ms |
| 14 | Dame los pedidos pendientes | analisis_datos | analisis_datos | ✅ | 392ms |
| 15 | Enséñame cómo se calculan las ventas netas | aprendizaje | analisis_datos | ❌ | 379ms |

