# Contexto: Servicio IA — ia_service_os
**Actualizado**: 2026-03-23

## Scope y propósito

Este servicio NO es exclusivo de Integraciones_OS. Es el servicio de IA de TODA la empresa OS.
Sirve al bot de Telegram, ERP, futuras apps y cualquier proyecto OS.

## Arquitectura

| Componente | Detalle |
|---|---|
| Código | `scripts/ia_service/` — módulo Python, función principal `consultar()` |
| BD | `ia_service_os` en MariaDB local (17 tablas + 1 vista) |
| API Flask | Puerto 5100, systemd `ia-service.service` |
| Admin panel | Express puerto 9200, `os-ia-admin.service`, sirve frontend Quasar compilado |
| URL admin | ia.oscomunidad.com |

## Función principal

```python
resultado = consultar(
    pregunta="¿Cuánto vendimos ayer?",
    tipo=None,           # None = enrutar automático vía Groq
    agente=None,         # None = usar preferido del tipo
    usuario_id="santi",
    canal="telegram",
    empresa="ori_sil_2", # multi-empresa
    tema=None,           # None = enrutador detecta automáticamente
    conversacion_id=None,
    nombre_usuario=None,
    contexto_extra="",   # para ERP: contexto de pantalla activa
    cliente=None,        # dict {nombre, identificacion, tipo_id, telefono, email}
)
# Devuelve: ok, conversacion_id, respuesta, formato, tabla, sql, agente, tokens, costo_usd, log_id, tema, empresa
```

## Agentes activos (2026-03-22)

| slug | modelo | Estado | Nivel min | Costo input/M |
|---|---|---|---|---|
| groq-llama | llama-3.3-70b-versatile | ✅ Router principal | 1 | $0.00 |
| cerebras-llama | llama3.1-8b | ✅ Router suplente (2,200 t/s) | 1 | ~$0.10 |
| gemini-flash | gemini-2.5-flash | ✅ Default analítico | 1 | $0.075 |
| gemini-flash-lite | gemini-2.5-flash-lite | ✅ Router fallback 2 | 1 | $0.0375 |
| gpt-oss-120b | openai/gpt-oss-120b | ✅ Alternativo | 1 | — |
| deepseek-chat | deepseek-chat | ✅ Respaldo | 1 | $0.14 |
| gemini-pro | gemini-2.5-pro | ✅ Premium | 6 | $1.25 |
| claude-sonnet | claude-sonnet-4-6 | ✅ Documentos premium | 6 | $3.00 |
| deepseek-reasoner | deepseek-reasoner | ✅ Admin only | 7 | $0.55 |
| gemini-image | gemini-2.5-flash-image | ✅ Imágenes | 1 | $52.00 |
| gemma-router | gemma-3-27b-it | ❌ Desactivado (activo=0) | — | $0.00 |

**⚠️ cerebras-llama tiene 8,192 tokens máx de entrada** — NO sirve para `analisis_datos` (DDL = 28K-37K tokens). Solo para tareas con prompt pequeño.

## Tipos de consulta — configuración DEFINITIVA (2026-03-22)

| Tipo | agente_preferido | agente_fallback | agente_sql | Razón |
|---|---|---|---|---|
| analisis_datos | gemini-flash | gemini-flash-lite | gemini-flash | DDL 28K tokens, necesita contexto largo |
| conversacion | gemini-flash-lite | cerebras-llama | — | Razonamiento contextual, RPD ilimitado |
| redaccion | gemini-flash-lite | cerebras-llama | — | Prompt chico, barato |
| aprendizaje | gemini-flash-lite | cerebras-llama | — | Tarea simple |
| busqueda_web | gemini-flash-lite | cerebras-llama | — | Prompt chico |
| resumen | cerebras-llama | gemini-flash-lite | — | Prompt chico (~2K), rápido |
| generacion_documento | gemini-flash | gemini-flash-lite | — | Docs largos |
| clasificacion | groq-llama | cerebras-llama | — | Rápido, simple |
| enrutamiento | groq-llama | cerebras-llama | — | 300ms, gratis |

## Configuración ia_config (2026-03-22)

| Clave | Valor actual |
|---|---|
| rol_router_principal | groq-llama |
| rol_router_suplente_1 | cerebras-llama |
| rol_router_suplente_2 | gemini-flash-lite |
| rol_router_suplente_3 | gemini-flash |
| rol_resumen_agente | cerebras-llama |
| rol_depurador_agente | groq-llama |

Todos los roles son configurables desde **Roles de agentes** en ia.oscomunidad.com (no hardcodeados).

## Prioridad de selección de agente

`agente del caller` > `conv.agente_activo` > `tema.agente_preferido` > `tipo.agente_preferido` > default

**ia_temas.agente_preferido = NULL** — el tipo decide el agente (no el tema).

## Stack de contexto en 8 capas (2026-03-20)

```
CAPA 0 — Fecha/hora actual                  → inyectada siempre al inicio del prompt
CAPA 1 — Lógica de negocio                  → ia_logica_negocio (siempre_presente=1 + por keywords)
CAPA 2 — System prompt base del tipo        → ia_tipos_consulta.system_prompt
CAPA 3 — RAG (fragmentos relevantes)        → ia_rag_fragmentos (FULLTEXT search)
CAPA 4 — Schema BD (DDL tablas analíticas)  → esquema.py caché 1h desde Hostinger
CAPA 5 — Resumen conversación comprimido    → ia_conversaciones.resumen (≤600 palabras)
CAPA 6 — Últimos 5 mensajes verbatim        → ia_conversaciones.mensajes_recientes
CAPA 7 — Caché SQL                          → ia_conversaciones.metadata.cache_sql (último resultado)
CAPA 8 — Ejemplos SQL (few-shot)            → ia_ejemplos_sql (embeddings cosine similarity)
```

Todas las capas visibles y gestionables desde ia.oscomunidad.com.

## 17 tablas + 1 vista en ia_service_os

Manual completo: `.agent/manuales/ia_service_manual.md`

Tablas clave:
- `ia_agentes`, `ia_tipos_consulta`, `ia_temas`, `ia_conversaciones`, `ia_logs`, `ia_consumo_diario`
- `ia_ejemplos_sql` (303 ejemplos con embeddings)
- `ia_rag_documentos`, `ia_rag_fragmentos`
- `ia_usuarios`, `ia_empresas`, `ia_usuarios_empresas`
- `ia_config`, `ia_conexiones_bd`, `ia_esquemas`
- `bot_sesiones`, `bot_tablas_temp`
- `v_consumo_hoy` (vista)

## Multi-empresa (multi-tenant)

- Todas las tablas tienen campo `empresa` (excepto `ia_agentes` — config global)
- Empresa activa: `ori_sil_2` (Origen Silvestre)
- JWT 2 pasos: Google auth → JWT temporal con lista empresas → seleccionar empresa → JWT final con `empresa_activa`
- `empresa` NUNCA viene del cliente — siempre inyectada desde JWT en middleware `requireAuth`
- Santiago = admin, Jennifer = viewer
- Manual: `.agent/docs/MANUAL_EMPRESAS_USUARIOS.md`

## Bot Telegram

`scripts/telegram_bot/` — python-telegram-bot v20 async. Corre como proceso nohup.

### Autenticación
- Cualquier número desconocido es rechazado
- Flujo: usuario comparte teléfono → verifica contra `ia_usuarios.telefono` → nivel asignado
- `telegram_id` se vincula en el primer login

### Usuarios registrados
| Usuario | Teléfono | Nivel |
|---|---|---|
| Santiago | +573214550933 | 7 (admin total) |
| Jen | +572307085143 | 5 |

### Agentes disponibles según nivel
- Nivel 1–5: cerebras-llama ★ (default), gemini-flash, gpt-oss-120b, deepseek-chat
- Nivel 6–7: + gemini-pro, claude-sonnet

### Regla tabla bot — ABSOLUTA
- `MAX_FILAS_INLINE = 2` — más de 2 registros → botón "Ver tabla completa" SIEMPRE
- Solo 1-2 filas se muestran inline
- `_limpiar_tablas_texto()` elimina pipes markdown del texto del LLM en TODAS las respuestas
- LLM NUNCA escribe tablas markdown (prohibido en system prompt)

## Lógica de negocio (ia_logica_negocio)

- 16 fragmentos total; 13 activos
- `siempre_presente=1` se inyecta en toda consulta; resto filtra por keywords
- Depurador automático cuando supera 1000 palabras (target compresión: 900 palabras)
- Bug corregido (2026-03-22): el depurador comprime cada regla individualmente (UPDATE en BD), NUNCA borra ni desactiva

**Fragmentos inactivos a propósito:**
- 'Lógica de negocio consolidada' (455 palabras, superset de todos — mantener inactiva para no duplicar)
- 'Tarifa Miembros OS' (incluida en 'Tarifas de precio')
- 'Prioridad de costo' (duplicado de 'Manejo de costos')

## Protocolo de aprendizaje (Sócrates)

IA aprende lógica de negocio en tiempo real:
1. Activado por variaciones de "enseñar/aprender/memorizar" O automáticamente cuando no puede responder
2. IA pregunta → usuario explica → IA confirma → guarda en `ia_logica_negocio` + notifica Telegram

## Circuit breaker con fallback automático

- `verificar_limites()` retorna `capa` (1=budget global, 2=RPD agente, 3=circuit breaker)
- Capa 1 → bloqueo total (sin alternativa — presupuesto agotado)
- Capa 2 o 3 → busca siguiente agente disponible respetando nivel del usuario
- Si hay alternativa: fallback silencioso con notificación "Fallback automático: X → Y"

## SQL retry con columnas reales

- `_obtener_columnas_reales(sql)`: extrae tablas del SQL fallido con sqlglot, hace DESCRIBE contra Hostinger
- El prompt de retry incluye las columnas REALES (evita que el LLM invente nombres en el segundo intento)

## Sistema de notificaciones

- `_notificar(mensaje)` → @os_notificaciones_sys_bot
- Alertas cuando:
  - Gasto diario total > $2 USD
  - Gasto última hora > $0.5 USD
  - Fallback se activa

## Módulo RAG

- `scripts/ia_service/rag.py` — fragmentación + búsqueda FULLTEXT por empresa+tema
- `ia_rag_colecciones` fue eliminada — reemplazada por `ia_temas`
- 7 temas seeded para ori_sil_2: comercial, finanzas, produccion, administracion, marketing, estrategia, general

## Embeddings semánticos

- `scripts/ia_service/embeddings.py`: Google text-embedding-004 + cosine similarity
- Fallback a keywords LIKE si falla
- Generación en background al guardar ejemplos SQL

## Admin panel ia.oscomunidad.com — 15 páginas en 6 grupos

- **Dashboard + Playground**
- **Conocimiento**: Lógica de negocio, Documentos RAG, Ejemplos SQL
- **Comportamiento**: Agentes, Roles de agentes, Tipos de consulta
- **Base de Datos**: Esquemas BD, Conexiones BD
- **Usuarios & Sesiones**: Usuarios, Conversaciones, Bot Telegram
- **Sistema**: Configuración, Logs

## Mejora continua automatizada

- Script: `scripts/ia_service/mejora_continua.py` (o similar)
- Cron cada 6 horas
- Log: `logs/mejora_continua.log`
- Nuevos módulos: `scripts/ia_service/alertas.py`, `scripts/ia_service/utilidades_sql.py`

## System prompt analisis_datos

- Columna `system_prompt` es MEDIUMTEXT (ampliada de TEXT)
- Tamaño: 67,454 chars / ~74KB
- 53 tablas documentadas (todas Hostinger)
- Incluye `<reglas_sql>` con 8+ gotchas críticos

## Bugs corregidos críticos (historial)

- **BUG-A**: `zeffi_articulos_producidos` vigencia es `'Orden vigente'` (no `'Vigente'`)
- **BUG-B**: `zeffi_trazabilidad.tipo_de_movimiento` valores reales = `'Creación de transacción'`/`'Anulación'`
- **BUG-C**: `zeffi_trazabilidad.vigencia_de_transaccion` = `'Transacción vigente'`/`'Transacción anulada'`
- **BUG-D**: `zeffi_ordenes_compra_encabezados.estado` = `'Pendiente de recibir'` (no `'Vigente'`)
- **BUG-E**: Tiempos producción negativos → filtro `TIMESTAMPDIFF >= 0` en `<reglas_sql>`
- **Bug _get_config_simple** (2026-03-22): usaba `_db()` inexistente → siempre devolvía hardcoded. Corregido con `get_local_conn()`

## Groq token exhaustion — causa y fix

- 26 consultas/día → ~53 groq calls (router + resumen) → ~110K tokens > 100K límite diario
- Fix: `rol_resumen_agente = cerebras-llama` en ia_config
- Groq ahora EXCLUSIVO para routing (2.5K tokens/call)

## Archivos clave

| Archivo | Propósito |
|---|---|
| `scripts/ia_service/servicio.py` | Función principal `consultar()`, toda la lógica |
| `scripts/ia_service/esquema.py` | DDL caché 1h desde Hostinger |
| `scripts/ia_service/embeddings.py` | Embeddings semánticos |
| `scripts/ia_service/rag.py` | Módulo RAG fragmentación+búsqueda |
| `scripts/ia_service/app.py` | API Flask puerto 5100 |
| `scripts/ia_service/aprendizaje.py` | Protocolo de aprendizaje Sócrates |
| `scripts/ia_service/alertas.py` | Sistema de alertas (nuevo) |
| `scripts/ia_service/utilidades_sql.py` | Utilidades SQL (nuevo) |
| `scripts/telegram_bot/` | Bot Telegram completo |
| `ia-admin/` | Frontend admin Vue+Quasar |
| `ia-admin/api/server.js` | API Express puerto 9200 |
| `.agent/manuales/ia_service_manual.md` | Manual completo v2.7 |
| `.agent/docs/COMPARACION_AGENTES_IA.md` | Benchmark 3 rondas, 105 llamadas |
