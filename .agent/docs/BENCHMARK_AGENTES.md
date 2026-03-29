# Benchmark de Agentes IA — Origen Silvestre

> Resultados de rendimiento de todos los agentes del sistema.
> **Catálogo de agentes (precios, credenciales, capacidades)**: `CATALOGO_AGENTES.md`
> **Scripts de benchmark**: `scripts/benchmark_agentes.py`, `scripts/benchmark_ollama.py`, `scripts/benchmark_ollama_router.py`

---

## Tabla maestra — Todos los agentes

Consolidado de todos los benchmarks realizados. Última actualización: 2026-03-29.

### Generación de SQL

| Agente | Tipo | Tests | Éxito | Latencia avg | Costo/M input | Contexto | Benchmark |
|---|---|---|---|---|---|---|---|
| **Qwen Coder 14B** | local | 15 | **100%** | 15.5s | **$0** | 32K | 2026-03-29 |
| **Qwen 14B** | local | 15 | **100%** | 15.3s | **$0** | 32K | 2026-03-29 |
| **DeepSeek R1 14B** | local | 15 | **100%** | 24.2s | **$0** | 131K | 2026-03-29 |
| groq-llama 70B | cloud | 30 | 97% | 19.2s | $0 | 128K | 2026-03-20 |
| cerebras-llama 8B | cloud | 30 | 97% | 19.7s | $0.10 | 8K | 2026-03-20 |
| gemini-flash | cloud | 30 | 93% | 13.0s | $0.075 | 1M | 2026-03-20 |
| gpt-oss-120b | cloud | 30 | 93% | 19.2s | $0.15 | 131K | 2026-03-20 |
| gemini-flash-lite | cloud | 30 | 87% | 11.2s | $0.037 | 1M | 2026-03-20 |

**Nota sobre locales**: 15 preguntas limpias sin ambigüedad. Los cloud tienen 30 incluyendo queries complejas (múltiples CTEs, comparativos YoY). Los locales podrían bajar con queries más difíciles.

**Nota sobre contexto**: cada llamada individual usa ~9-10K tokens (DDL 8K + reglas + ejemplos). Los 32K de Qwen son suficientes (~22K de margen).

### Conversación / Respuesta

| Agente | Tipo | Tests | Éxito | Latencia avg | Benchmark |
|---|---|---|---|---|---|
| **Qwen Coder 14B** | local | 10 | **100%** | 15.5s | 2026-03-29 |
| gpt-oss-120b | cloud | 22 | **100%** | 15.1s | 2026-03-20 |
| cerebras-llama 8B | cloud | 22 | **100%** | 10.9s | 2026-03-20 |
| Qwen 14B | local | 10 | 90% | 20.9s | 2026-03-29 |
| gemini-flash | cloud | 22 | 91% | 9.5s | 2026-03-20 |
| groq-llama 70B | cloud | 22 | 91% | 9.8s | 2026-03-20 |
| gemini-flash-lite | cloud | 22 | 86% | 7.1s | 2026-03-20 |
| DeepSeek R1 14B | local | 10 | 80% | 25.2s | 2026-03-29 |

**Cerebras 100% en respuesta ≠ 100% en routing.** Cerebras sacó 100% cuando le dicen QUÉ hacer (responder). Pero cuando tiene que DECIDIR qué hacer (routing), falla — clasificó "¿Cuánto vendimos?" como `aprendizaje`. Son tareas distintas.

### Routing (clasificación de preguntas)

| Agente | Tipo | Tests | Precisión | Latencia avg | Benchmark |
|---|---|---|---|---|---|
| **groq-llama 70B** | cloud | ~500+ | **~95%** | 100ms | producción continua |
| Qwen 7B | local | 15 | 80% | 396ms | 2026-03-29 |
| Llama 3B | local | 15 | 60% | 452ms | 2026-03-29 |
| cerebras-llama 8B | cloud | ~500+ | ~70%* | <1s | producción (fallback) |

*Cerebras como router fallback: clasificó mal preguntas de ventas como `aprendizaje` (2026-03-29, durante rate limit de Groq).

---

## Configuración actual (2026-03-29)

| Rol | Principal | Fallback | Motivo |
|---|---|---|---|
| **SQL** | ollama-qwen-coder | gemini-flash | 100% éxito, $0, 15.5s. Flash de respaldo si GPU ocupada |
| **Conversación** | ollama-qwen-14b | gemini-flash-lite | 90-100%, $0. Flash-lite de respaldo |
| **Redacción** | ollama-qwen-14b | gemini-flash-lite | Generalista, buen español |
| **Aprendizaje** | ollama-qwen-14b | gemini-flash-lite | |
| **Router** | groq-llama | cerebras-llama | Groq imbatible: 95%, 100ms, gratis |
| **Resumen** | gemini-flash-lite | cerebras-llama | Prompts chicos, rápido |

---

## Hallazgos clave

### Cerebras ≠ Groq para routing
- Cerebras (Llama 3.1 8B, 8K contexto) funciona bien para responder y resumir (prompts chicos, tarea clara)
- Para routing necesita CLASIFICAR con un prompt complejo de 9 tipos — un modelo 8B no tiene la sofisticación suficiente
- Groq (Llama 3.3 70B) tiene 9x más parámetros y clasifica mucho mejor
- **Acción**: cerebras queda como fallback de emergencia del router, no como alternativa real

### Modelos locales sorprendentemente buenos para SQL
- Los 3 modelos 14B (Qwen Coder, Qwen, DeepSeek R1) sacaron 100% en SQL
- El DDL de 53 tablas cabe en ~8K tokens — bien dentro del contexto de 32K
- Latencia comparable a Flash (15s vs 13.8s)
- Costo $0 vs $0.005/consulta de Flash

### DeepSeek R1 — bueno pero lento
- Chain-of-thought agrega ~9s extra (24s vs 15s)
- 80% en conversación (2 timeouts HTTP)
- Mejor para razonamiento complejo, no para consultas rutinarias

### Limitaciones de modelos locales
- **Concurrencia**: solo 1 modelo 14B en VRAM a la vez (RTX 3060 12GB)
- **Identidad**: Qwen se identifica como "creado por Alibaba", DeepSeek como "DeepSeek-R1" — no asumen el rol de Lara/OS automáticamente (el system prompt lo corrige pero a veces se filtra)

---

## Historial de benchmarks

| Fecha | Alcance | Tests | Script | Detalle |
|---|---|---|---|---|
| 2026-03-20 | 5 agentes cloud (SQL + respuesta) | 105 | `benchmark_agentes.py` | Ronda 1-3. Definió config original |
| 2026-03-29 | 5 modelos Ollama (SQL + conv + router) | 135 | `benchmark_ollama.py` + `benchmark_ollama_router.py` | Validó locales como principales |

---

## Cuándo re-ejecutar

- Al agregar un agente nuevo
- Si un modelo se actualiza (nueva versión de Gemini, Qwen, etc.)
- Si la calidad percibida baja en producción
- Sugerido: cada 2-3 meses o al cambiar config
