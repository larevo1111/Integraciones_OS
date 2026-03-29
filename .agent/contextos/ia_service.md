# Contexto: Servicio IA — ia_service_os
**Actualizado**: 2026-03-24

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

## Agentes activos (2026-03-28)

**Catálogo completo**: `.agent/docs/CATALOGO_AGENTES.md`

### Cloud (APIs externas)
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

### Locales (Ollama — GPU RTX 3060 12GB, costo $0)
| slug | modelo | VRAM | Mejor para |
|---|---|---|---|
| ollama-qwen-coder | qwen2.5-coder:14b | ~9 GB | SQL, código |
| ollama-qwen-14b | qwen2.5:14b | ~9 GB | Conversación, español |
| ollama-qwen-7b | qwen2.5:7b | ~4.7 GB | Router versátil |
| ollama-deepseek-r1 | deepseek-r1:14b | ~9 GB | Razonamiento |
| ollama-llama-3b | llama3.2:3b | ~2.8 GB | Router ultra liviano |

API local: `http://localhost:11434/v1` | Externa: `https://ollama.oscomunidad.com`

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
- `ia_ejemplos_sql` (431 ejemplos con embeddings, 0 duplicados, 0 con CURDATE)
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

### Regla tabla bot — ABSOLUTA (confirmada 2026-03-28)
- **A**: SIEMPRE poner información en el mensaje con viñetas y texto
- **B**: Si >2 registros → ADEMÁS adjuntar botón "Ver tabla completa" (mini app web)
- NUNCA dibujar tablas ASCII/Unicode/markdown en el chat
- `MAX_FILAS_INLINE = 2` en tabla.py
- `_limpiar_tablas_texto()` elimina pipes markdown como red de seguridad

## Lógica de negocio (ia_logica_negocio)

- **16 reglas activas** (~1059 palabras totales)
- `siempre_presente=1` (reglas 1, 32, 38) se inyectan en TODA consulta; resto por keywords
- Depurador automático: comprime cuando >1000 palabras (target 900). NUNCA borra ni desactiva.

**Depuración 2026-03-28:**
- Desactivadas 3 duplicadas (#16, #30, #31)
- Corregidos keywords en 5 reglas (#2, #6, #8, #29, #36) para evitar falsos positivos
- Creadas 3 reglas nuevas: #37 (métricas ventas), #38 (gotchas SQL — SP), #39 (margen/utilidad)
- Completada regla #4 (canales faltantes), actualizada #1 (stack agentes)

**Protección contra patrones prohibidos (2026-03-28):**
- `guardar_ejemplo_sql()` ahora RECHAZA SQL con CURDATE(), NOW(), CURRENT_DATE() antes de guardar
- Evita ciclo vicioso: LLM genera patrón prohibido → se guarda → LLM lo copia del ejemplo

## Protocolo de aprendizaje (Sócrates)

IA aprende lógica de negocio en tiempo real:
1. Activado por variaciones de "enseñar/aprender/memorizar" O automáticamente cuando no puede responder
2. IA pregunta → usuario explica → IA confirma → guarda en `ia_logica_negocio` + notifica Telegram

## Circuit breaker con fallback automático

- `verificar_limites()` retorna `capa` (1=budget global, 2=RPD agente, 3=circuit breaker)
- Capa 1 → bloqueo total (sin alternativa — presupuesto agotado)
- Capa 2 o 3 → busca siguiente agente disponible respetando nivel del usuario
- Si hay alternativa: fallback silencioso con notificación "Fallback automático: X → Y"

## Detección de pedido de detalle (_pide_detalle)

Cuando el tipo es `analisis_datos` y el router dice `requiere_sql=False` (reusar caché), hay una segunda verificación: si el usuario pide "detalle", "tabla adjunta", "desglose", "listado completo", etc., fuerza `requiere_sql=True` para generar SQL nuevo en lugar de reusar datos agregados del caché.

Esto evita que "Dame las ventas" → 1 fila SUM → follow-up "La tabla con el detalle" → reutilice la misma 1 fila.

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
| `scripts/telegram_bot/bot.py` | Bot Telegram — handler principal |
| `scripts/telegram_bot/superagente.py` | Super Agente — sesiones + llamada claude -p |
| `scripts/telegram_bot/handlers_sa.py` | Super Agente — handlers Telegram |
| `ia-admin/` | Frontend admin Vue+Quasar |
| `ia-admin/api/server.js` | API Express puerto 9200 |
| `.agent/manuales/ia_service_manual.md` | Manual completo v2.7 |
| `.agent/docs/COMPARACION_AGENTES_IA.md` | Benchmark 3 rondas, 105 llamadas |

## Super Agente (activo — 2026-03-28)

Claude Code CLI corre en paralelo al ia_service. El usuario selecciona `🦾 Super Agente` en el menú.

**Principio**: Es algo MUY SIMPLE — solo enviar prompts a `claude -p` y devolver la respuesta. Sin API keys, sin logging.

**Detalles técnicos**:
- `superagente.py` hace `subprocess.run([claude, '-p', prompt, '--output-format', 'json'])`
- Fuerza OAuth Pro: `env.pop('ANTHROPIC_API_KEY')` para no usar API key del .env
- Sesiones persistentes con `--resume SESSION_ID` (5-30s vs 2min sin resume)
- Sin logging — ni import logging ni log.info/error/warning
- Tablas: `sa_sesiones`, `sa_config`, `sa_cambios` en ia_service_os
- Menú propio: [📝 Nueva] [📋 Conversaciones] [⚙️ Ajustes]
- Aprobación de código: Claude envía JSON tipo "aprobacion" → bot notifica nivel 7 con ✅/❌
