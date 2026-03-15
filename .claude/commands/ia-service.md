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

## BD — 5 tablas

```sql
ia_agentes          -- modelos configurados con API key
ia_tipos_consulta   -- reglas por tipo (SQL, redaccion, imagen, etc.)
ia_conversaciones   -- resumen vivo por usuario+canal (≤1000 palabras)
ia_logs             -- auditoría completa por llamada
ia_consumo_diario   -- agregado diario: llamadas, tokens, costo, % límite
```

## Comandos de operación

```bash
# Estado del servicio
sudo systemctl status ia-service.service

# Reiniciar
sudo systemctl restart ia-service.service

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

## Gotchas críticos

- **API keys**: SOLO en BD + scripts/.env. NUNCA en código o documentos del repo.
- **Gemini 2.5 Pro**: 1,000 RPD — reservar para análisis reales, no para enrutador
- **Reset cuota Gemini**: 3:00 AM Colombia (medianoche Pacific Time)
- **Nivel de pago 1 activo**: billing vinculado en Google Cloud — los límites son 500x superiores al free tier
