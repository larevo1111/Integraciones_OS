---
name: ia-service
description: >
  Servicio Central de IA de Origen Silvestre. Triggers: ia_service, servicio ia, agente, consultar, ollama, qwen, gemini, bot telegram, ia_service_os.
---

Carga el contexto completo del Servicio Central de IA de Origen Silvestre.

## ¿Qué es?

`ia_service_os` es el servicio de IA centralizado de OS. Corre en el servidor principal en el puerto 5100 y sirve a TODOS los proyectos de la empresa. No es exclusivo de Integraciones_OS.

## Archivos clave

- **Código**: `scripts/ia_service/` — módulo Python completo
  - `servicio.py` — orquestador principal, función `consultar()`
  - `app.py` — Flask API (puerto 5100)
  - `proveedores/google.py` — Gemini + Imagen + Gemma
  - `proveedores/openai_compat.py` — Groq, DeepSeek
  - `proveedores/anthropic_prov.py` — Claude
  - `contexto.py` — manejo de conversaciones y resumen vivo
  - `ejecutor_sql.py` — ejecución segura de SQL en Hostinger
  - `esquema.py` — DDL de tablas analíticas (caché 1h)
  - `formateador.py` — parseo de respuestas y SQL
- **BD**: `ia_service_os` en MariaDB local
- **Servicio**: `systemd ia-service.service`
- **Manual**: `.agent/manuales/ia_service_manual.md`
- **Skill arquitectura**: `.agent/skills/manejo_ia.md`

## Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/ia/consultar` | Consulta principal |
| GET | `/ia/agentes` | Lista agentes (sin exponer keys) |
| GET | `/ia/tipos` | Lista tipos de consulta |
| GET | `/ia/health` | Health check |
| GET | `/ia/consumo` | Consumo hoy/semana/mes con % límite |
| GET | `/ia/consumo/historico` | Histórico día a día |

## BD — 17 tablas + 1 vista

```sql
ia_agentes           -- modelos IA configurados con API key
ia_tipos_consulta    -- flujos por tipo (SQL, RAG, imagen, etc.)
ia_temas             -- áreas de negocio con agente_preferido por tema
ia_conversaciones    -- contexto vivo por usuario+canal (resumen + mensajes)
ia_logs              -- auditoría completa por llamada
ia_consumo_diario    -- agregado diario: llamadas, tokens, costo
ia_ejemplos_sql      -- pares pregunta→SQL (few-shot learning + embeddings)
ia_rag_documentos    -- documentos de negocio para RAG
ia_rag_fragmentos    -- chunks ~500 palabras con FULLTEXT index
ia_usuarios          -- usuarios del servicio con nivel 1–7
ia_empresas          -- empresas registradas (multi-tenant)
ia_usuarios_empresas -- relación usuario↔empresa con rol
ia_config            -- parámetros globales (rate limits, circuit breaker, costo max)
ia_conexiones_bd     -- conexiones a BDs externas por empresa
ia_esquemas          -- DDL personalizado por tema+conexión
bot_sesiones         -- agente preferido por telegram_user_id
bot_tablas_temp      -- datasets temporales para mini app web del bot
v_consumo_hoy        -- vista: consumo del día actual
```

## Comandos de operación

```bash
# Estado del servicio
sudo systemctl status ia-service.service

# Reiniciar (usar kill+start — restart a veces se cuelga)
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2) && sudo systemctl start ia-service.service

# Logs en tiempo real
journalctl -u ia-service.service -f

# Health check
curl -s http://localhost:5100/ia/health

# Consumo de hoy
curl -s "http://localhost:5100/ia/consumo" | python3 -m json.tool

# Ver agentes activos
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, nombre, modelo_id, activo, LENGTH(api_key)>0 AS tiene_key, rate_limit_rpd FROM ia_agentes ORDER BY orden;" 2>/dev/null

# Ver consumo en BD
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT fecha, agente_slug, llamadas, tokens_total, costo_usd FROM ia_consumo_diario ORDER BY fecha DESC LIMIT 20;" 2>/dev/null
```

## Agregar una API key

```bash
# Groq (gratis — console.groq.com)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='gsk_...', activo=1 WHERE slug='groq-llama';" 2>/dev/null

# DeepSeek (platform.deepseek.com — requiere $5)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='sk-...', activo=1 WHERE slug='deepseek-chat';" 2>/dev/null

# Anthropic Claude (console.anthropic.com — requiere $5)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='sk-ant-...', activo=1 WHERE slug='claude-sonnet';" 2>/dev/null
```

También agregar en `scripts/.env` como backup.

## Probar una consulta

```bash
# Consulta de análisis de datos (usa gemini-pro)
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"¿Cuánto vendimos este mes?","usuario_id":"santi","canal":"api"}'

# Forzar un agente específico
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"Redacta un email de bienvenida","agente":"gemini-flash","usuario_id":"santi"}'

# Generar imagen
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"Genera imagen de árbol ceiba","tipo":"generacion_imagen","usuario_id":"santi"}'
```

## Estado de agentes (marzo 2026)

| Agente | Key | RPD | Para qué |
|---|---|---|---|
| gemini-pro | ✅ | 1,000 | SQL complejo — principal |
| gemini-flash | ✅ | 10,000 | Redacción, resumen |
| gemini-flash-lite | ✅ | 150,000 | Alto volumen |
| gemma-router | ✅ | 14,400 | Enrutador |
| gemini-image | ✅ | 70 | Imágenes |
| groq-llama | ✅ | 14,400 | Enrutador principal (llama-3.3-70b-versatile) |
| deepseek-chat | ✅ | — | Análisis — recomendado para uso diario |
| deepseek-reasoner | ✅ | — | Razonamiento complejo (nivel_minimo=7 — solo admin) |
| claude-sonnet | ✅ | — | Documentos premium (claude-sonnet-4-6) |

## Reset de contexto de conversación

```bash
# Reiniciar conversación de un usuario
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_conversaciones SET resumen=NULL, updated_at=NOW() WHERE usuario_id='santi' AND canal='telegram';" 2>/dev/null
```

## Latencias reales (medido 2026-03-15)

| Flujo | Agente | Tiempo | Tokens entrada |
|---|---|---|---|
| SIN SQL (conversacion) | gemini-flash-lite | **~2.2–3.1s** | ~230 |
| SIN SQL (conversacion) | gemini-pro | ~20–26s | ~230–550 |
| SIN SQL (conversacion) | deepseek-chat | ~18s | ~450 |
| CON SQL (analisis_datos) | gemini-pro | **~20–23s** | ~27,600 (DDL) |

**Reglas del flujo** (arquitectura vigente 2026-03-15):
- **SIN SQL**: `enrutar (groq ~300ms)` → `redactar (agente analítico)` — 1 llamada LLM
- **CON SQL**: `enrutar` → `generar_sql (gemini-flash)` → `ejecutar BD` → `redactar (agente analítico)` — hasta 4 llamadas
  - Hasta 3 verificaciones SQL: 1 inicial + retry por error + retry por vacío
  - Agente final siempre es el analítico seleccionado (NUNCA groq-llama)
- **groq-llama**: enrutador exclusivo — NO responde como agente final
- **gemini-pro latencia base**: ~20s independientemente del tamaño del prompt (característica del modelo)

## Gotchas críticos

- **API keys**: SOLO en BD + scripts/.env. NUNCA en código o documentos del repo.
- **Gemini 2.5 Pro**: 1,000 RPD — reservar para análisis reales, no para enrutador
- **Reset cuota Gemini**: 3:00 AM Colombia (medianoche Pacific Time)
- **Nivel de pago 1 activo**: billing vinculado en Google Cloud — los límites son 500x superiores al free tier
- **gemini-pro tarda ~20s siempre** — con 228 o con 27,625 tokens, misma latencia. Para respuestas conversacionales simples es overkill.
