# Manual del Servicio Central de IA — ia_service_os

> **REGLA DE SEGURIDAD ABSOLUTA**: Las API keys van SOLO en la BD (`ia_agentes.api_key`) y en `scripts/.env`.
> NUNCA en archivos .md, código commiteado, ni en ningún otro lugar.

---

## Índice

1. [Arquitectura del servicio](#arquitectura)
2. [Agente: Google Gemini](#gemini)
3. [Agente: Groq](#groq)
4. [Agente: DeepSeek](#deepseek)
5. [Agente: Anthropic Claude](#anthropic)
6. [Cómo agregar una API key](#agregar-api-key)
7. [Estrategia de uso — qué modelo para qué](#estrategia)
8. [Monitoreo del consumo](#monitoreo)
9. [Referencia de tipos de consulta](#tipos)
10. [Troubleshooting](#troubleshooting)

---

## 1. Arquitectura del servicio {#arquitectura}

```
POST /ia/consultar (Flask :5100)
        ↓
  consultar() — servicio.py
        ↓
  _enrutar() → detecta tipo (Groq → Gemini fallback)
        ↓
  obtiene agente de ia_agentes (por tipo o slug)
        ↓
  proveedores/google.py | openai_compat.py | anthropic_prov.py
        ↓
  formateador.py → extrae SQL / resumen / imagen
        ↓
  ejecutor_sql.py → corre SQL en Hostinger (solo SELECT)
        ↓
  segunda llamada al LLM → redacta respuesta humana
        ↓
  contexto.py → guarda resumen vivo en ia_conversaciones
        ↓
  retorna dict: ok, respuesta, imagen_b64, tabla, sql, tokens, costo...
```

**BD local**: `ia_service_os` en MariaDB — 4 tablas: `ia_agentes`, `ia_tipos_consulta`, `ia_conversaciones`, `ia_logs`

**Puerto**: 5100 (systemd `ia-service.service`)

**Proveedor format field** en `ia_agentes`:
- `"openai"` → `proveedores/openai_compat.py` (Groq, DeepSeek)
- `"google"` → `proveedores/google.py` (Gemini, Gemma, Imagen)
- `"anthropic"` → `proveedores/anthropic_prov.py` (Claude)

---

## 2. Google Gemini {#gemini}

### Obtener API key

1. Ir a [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API Key
2. Seleccionar proyecto de Google Cloud
3. **Vincular una Billing Account al proyecto** (obligatorio para desbloquear los límites del free tier)
   - Sin billing: la API funciona pero los límites reales son 0 o casi nada ("bucket no validado")
   - Con billing vinculado (Tier 1): se activan los límites generosos del free tier
   - **No cobran mientras no superes los límites gratuitos**
   - Configurar billing: [console.cloud.google.com/billing](https://console.cloud.google.com/billing)
4. La key empieza con `AIzaSy...`

> **Estado actual OS (2026-03-12)**: Billing vinculado ✅ — todos los límites del free tier activos.

### Endpoint base

```
https://generativelanguage.googleapis.com/v1beta
```

Llamada: `POST /models/{modelo_id}:generateContent?key={API_KEY}`

### Límites reales del Tier 1 (free con billing vinculado)

> Fuente: datos directos de Google AI Studio del proyecto OS — 2026-03-12

| Modelo (display) | modelo_id para API | RPM | TPM | RPD | Notas |
|---|---|---|---|---|---|
| **Gemini 2.5 Flash** | `gemini-2.5-flash` | 5 | 250K | **20** | ⚠️ Muy restrictivo — 20/día |
| **Gemini 2.5 Flash Lite** | `gemini-2.5-flash-lite-preview` | 10 | 250K | **20** | ⚠️ También 20/día |
| **Gemini 3 Flash** | `gemini-3-flash` | 5 | 250K | **20** | Igual de restrictivo |
| **Gemini 3.1 Flash Lite** | `gemini-3.1-flash-lite` | 15 | 250K | **500** | ✅ Recomendado — 500/día |
| **Gemma 3 27B** | `gemma-3-27b-it` | 30 | 15K | **14,400** | ✅ Enrutador ideal — casi ilimitado |
| **Gemma 3 12B** | `gemma-3-12b-it` | 30 | 15K | **14,400** | ✅ Alternativa ligera |
| **Gemma 3 4B** | `gemma-3-4b-it` | 30 | 15K | **14,400** | ✅ El más rápido/ligero |
| **Imagen 4 Generate** | `imagen-4.0-generate-preview` | — | — | **25** | Imágenes alta calidad |
| **Imagen 4 Fast Generate** | `imagen-4.0-fast-generate-preview` | — | — | **25** | Imágenes rápidas |
| **Gemini 2.5 Flash TTS** | `gemini-2.5-flash-tts` | 3 | 10K | 10 | Texto a voz |
| **Gemini Embedding 1** | `text-embedding-004` | 100 | 30K | 1K | Embeddings |
| **Gemini Embedding 2** | `gemini-embedding-exp` | 100 | 30K | 1K | Embeddings v2 |
| **Gemini 2.5 Flash Audio** | `gemini-2.5-flash-exp-native-audio-dialog` | Ilimitado | 1M | Ilimitado | Solo audio live |

> **⚠️ Insight crítico**: Los modelos "principales" (2.5 Flash, 3 Flash) tienen solo **20 RPD** en el free tier. Para el bot de Telegram y uso diario, usar **Gemini 3.1 Flash Lite (500 RPD)** o **Gemma 3 (14,400 RPD)**.

> **Los límites son por PROYECTO**, no por API key. Crear más keys del mismo proyecto no aumenta los límites.

> **Reset**: medianoche Pacific Time = **3:00 AM Colombia** (UTC-5)

### Tiers de uso

| Tier | Requisito | Diferencia |
|---|---|---|
| **Free sin billing** | Solo crear key | Límites reales: 0 — NO USAR |
| **Tier 1 (free con billing)** | Billing account vinculada | Límites generosos del free tier ✅ |
| **Tier 2** | Gasto acumulado > $250 + 30 días | Límites mayores |
| **Tier 3** | Gasto acumulado > $1,000 + 30 días | Límites enterprise |

El upgrade de Free → Tier 1 es instantáneo. Tier 1 → 2 o 3 tarda máx 10 minutos tras cumplir requisitos.

### Formato del payload

```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "Hola"}]},
    {"role": "model", "parts": [{"text": "Hola, ¿cómo te puedo ayudar?"}]}
  ],
  "systemInstruction": {
    "parts": [{"text": "Eres un asistente..."}]
  },
  "generationConfig": {
    "temperature": 0.3,
    "maxOutputTokens": 4096
  }
}
```

**Diferencia con OpenAI**: role `"assistant"` → `"model"` | system va separado en `systemInstruction`

### Generación de imágenes

**Modelos disponibles (Tier 1):**
- `imagen-4.0-generate-preview` — 25/día, mejor calidad
- `imagen-4.0-fast-generate-preview` — 25/día, más rápido

```json
{
  "contents": [{"role": "user", "parts": [{"text": "Genera imagen de árbol ceiba"}]}],
  "generationConfig": {
    "responseModalities": ["IMAGE", "TEXT"],
    "temperature": 1.0
  }
}
```

**Respuesta**: partes con `inlineData.data` (base64) y `inlineData.mimeType` ("image/png" o "image/jpeg")

Para probar:
```bash
curl -X POST "http://localhost:5100/ia/consultar" \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "Genera una imagen de un árbol ceiba colombiano", "tipo": "generacion_imagen"}'
```

### Gotchas críticos

| Problema | Causa | Solución |
|---|---|---|
| Límite `0` con error `generate_content_free_tier_requests` | Proyecto GCP sin billing vinculado — "bucket no validado" | Vincular billing account en console.cloud.google.com/billing |
| Respuesta vacía con max_tokens bajo | Gemini 2.5 es "thinking" — usa tokens internos antes de responder | Usar mínimo 200 max_tokens para enrutador, 4096 para respuestas normales |
| Error 429 "quota exceeded" | RPM o RPD superado | Esperar 60s (RPM) o hasta 3 AM Colombia (RPD diario) |
| RPD de 20 agotado rápido | Gemini 2.5 Flash solo tiene 20/día | Cambiar al modelo `gemini-3.1-flash-lite` (500/día) para uso general |
| Key bloqueada por GitHub | Key expuesta en un commit | Crear nueva key, actualizar BD y .env |

### Costos (si se supera el free tier — referencia)

| Modelo | Input | Output |
|---|---|---|
| gemini-2.5-flash | $0.15/M tokens | $0.60/M tokens |
| gemini-2.5-pro | $1.25/M tokens | $10.00/M tokens |
| imagen-4.0-generate | $0.04/imagen | — |

---

## 3. Groq {#groq}

### Obtener API key

1. Ir a [console.groq.com](https://console.groq.com) → API Keys → Create API Key
2. **100% gratuito, sin tarjeta de crédito**
3. La key empieza con `gsk_...`

### Endpoint

```
https://api.groq.com/openai/v1/chat/completions
```

Formato 100% compatible con OpenAI. Usar proveedor `"openai"` en `ia_agentes`.

### Modelos disponibles

| slug | modelo_id | Tokens contexto | RPM | RPD | Velocidad |
|---|---|---|---|---|---|
| groq-llama | `llama-3.3-70b-versatile` | 128k | 30 | 1,000 | ~800 tok/s |
| groq-llama-fast | `llama-3.1-8b-instant` | 128k | 30 | 14,400 | ~2000 tok/s |
| groq-mixtral | `mixtral-8x7b-32768` | 32k | 30 | 14,400 | ~500 tok/s |

**Recomendado para enrutador**: `llama-3.1-8b-instant` — el más rápido del ecosistema, 14,400 RPD.

### Gotchas

- **Groq no genera imágenes** — solo texto
- Ideal para: enrutador, clasificador, respuestas cortas de conversación
- Si el modelo está "ocupado" devuelve 503 — el servicio hace fallback automático a Gemini

---

## 4. DeepSeek {#deepseek}

### Obtener API key

1. Ir a [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create Key
2. **Requiere recarga mínima de $5 USD**
3. No hay tier completamente gratuito en producción (el chat web sí es gratis pero no la API)

### Endpoint

```
https://api.deepseek.com/v1/chat/completions
```

Formato 100% compatible con OpenAI. Usar proveedor `"openai"` en `ia_agentes`.

### Modelos

| slug | modelo_id | Uso ideal |
|---|---|---|
| deepseek-chat | `deepseek-chat` | Conversación, redacción, análisis (más barato) |
| deepseek-r1 | `deepseek-reasoner` | Razonamiento complejo, SQL difícil, problemas multi-paso |

### Precios (muy económicos)

| Modelo | Input | Output |
|---|---|---|
| deepseek-chat | $0.07/M tokens | $1.10/M tokens |
| deepseek-reasoner (R1) | $0.55/M tokens | $2.19/M tokens |

**DeepSeek es el más barato para razonamiento** — R1 vs GPT-o1/Claude Opus es 10–30x más económico.

### Gotchas

- **DeepSeek-R1** tiene "thinking tokens" internos — aparecen como `<think>...</think>` en la respuesta
- Latencia más alta que Groq (servidores en China)
- No genera imágenes

---

## 5. Anthropic Claude {#anthropic}

### Obtener API key

1. Ir a [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key
2. **Requiere tarjeta de crédito** — mínimo $5 USD de recarga
3. La key empieza con `sk-ant-...`

### Endpoint

```
https://api.anthropic.com/v1/messages
```

**Formato distinto a OpenAI** — usar proveedor `"anthropic"` en `ia_agentes`.

### Payload

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "system": "Eres un asistente...",
  "messages": [
    {"role": "user", "content": "¿Cuánto vendimos?"},
    {"role": "assistant", "content": "Según los datos..."}
  ]
}
```

Header requerido: `anthropic-version: 2023-06-01`

### Modelos actuales

| slug | modelo_id | Uso ideal |
|---|---|---|
| claude-sonnet | `claude-sonnet-4-6` | Default — mejor balance |
| claude-opus | `claude-opus-4-6` | Máxima calidad, SQL muy complejo |
| claude-haiku | `claude-haiku-4-5-20251001` | Rápido y barato |

### Precios

| Modelo | Input | Output |
|---|---|---|
| claude-haiku-4-5 | $0.80/M tokens | $4.00/M tokens |
| claude-sonnet-4-6 | $3.00/M tokens | $15.00/M tokens |
| claude-opus-4-6 | $15.00/M tokens | $75.00/M tokens |

### Gotchas

- El system message va en campo `"system"` separado (no en el array `messages`)
- `anthropic_prov.py` ya maneja esto: extrae el role `system` del array automáticamente
- No genera imágenes (solo texto/análisis)
- El más caro — reservar para análisis complejos donde la calidad es crítica

---

## 6. Cómo agregar una API key {#agregar-api-key}

### Paso 1 — Insertar/actualizar en BD local

```bash
# Ver estado actual de keys
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, nombre, activo, LENGTH(api_key) > 0 AS tiene_key FROM ia_agentes ORDER BY orden;" 2>/dev/null

# Agregar key (cambiar slug y key según corresponda)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='TU_KEY_AQUI', activo=1 WHERE slug='groq-llama';" 2>/dev/null
```

### Paso 2 — Backup en scripts/.env

Agregar al archivo `scripts/.env` (no commiteado — `.gitignore`):
```
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
```

### Paso 3 — Verificar

```bash
curl -s http://localhost:5100/ia/agentes | python3 -m json.tool
```

### Qué NUNCA hacer

- ❌ Escribir la key en un `.md`, comentario de código, o mensaje de commit
- ❌ Hacer `git add scripts/.env`
- ❌ Copiar la key en este manual u otro documento del repo
- ✅ La key va SOLO en la BD y en `scripts/.env`

---

## 7. Estrategia de uso — qué modelo para qué {#estrategia}

### El problema con Gemini 2.5 Flash como modelo único

Solo tiene **20 RPD**. Para un bot de Telegram con uso diario normal (10–20 consultas/día) eso se agota rápido. Solución: usar el modelo correcto para cada tarea.

### Estrategia recomendada

| Tarea | Modelo | RPD disponible | Por qué |
|---|---|---|---|
| **Enrutador** (clasificar intención) | `gemma-3-27b-it` (Groq: `llama-3.1-8b-instant`) | 14,400 | Ultra-rápido, tarea simple, no necesita calidad premium |
| **Conversación general** | `gemini-3.1-flash-lite` | 500 | Buen balance, 500 RPD suficientes para uso diario |
| **Análisis de datos SQL** | `gemini-2.5-flash` | 20 | La mejor calidad para SQL complejo — usar con moderación |
| **Generación de imágenes** | `imagen-4.0-fast-generate-preview` | 25 | Modelo correcto para imágenes |
| **SQL muy complejo** | `claude-sonnet-4-6` (cuando esté activo) | Rate limit bajo | Máxima calidad, reservar para casos difíciles |

### Configuración actual de ia_agentes (marzo 2026)

```
gemini-flash       → gemini-2.5-flash     → Para análisis complejos (20 RPD — usar con cuidado)
gemini-flash-lite  → gemini-3.1-flash-lite → Para conversación/redacción (500 RPD) ← PRINCIPAL
gemma-router       → gemma-3-27b-it        → Para enrutador (14,400 RPD) ← ENRUTADOR IDEAL
gemini-image       → imagen-4.0-fast-...   → Para imágenes (25 RPD)
groq-llama         → llama-3.1-8b-instant  → Enrutador alternativo (14,400 RPD)
```

---

## 8. Monitoreo del consumo {#monitoreo}

### Opción A — Google AI Studio (consumo Gemini en tiempo real)

URL: [aistudio.google.com/u/0/usage](https://aistudio.google.com/u/0/usage)

Muestra: uso de los últimos 28 días por modelo (RPM pico, TPM pico, RPD acumulado).
Ver: columnas `uso / límite` para saber qué tan cerca estás del techo.

> **Señal de alarma**: Si Gemini 2.5 Flash muestra >15/20 RPD, cambiar temporalmente el agente de análisis a `gemini-3.1-flash-lite` hasta que se resetee (3 AM Colombia).

### Opción B — Tabla ia_logs (consumo por llamada)

```sql
-- Consumo del día de hoy por agente
SELECT
  agente_slug,
  COUNT(*) AS llamadas,
  SUM(tokens_in) AS tokens_entrada,
  SUM(tokens_out) AS tokens_salida,
  SUM(costo_usd) AS costo_total_usd,
  ROUND(AVG(latencia_ms)/1000, 1) AS latencia_prom_seg,
  SUM(CASE WHEN ok=0 THEN 1 ELSE 0 END) AS errores
FROM ia_logs
WHERE DATE(created_at) = CURDATE()
GROUP BY agente_slug
ORDER BY llamadas DESC;
```

```sql
-- Consumo de los últimos 7 días
SELECT
  DATE(created_at) AS dia,
  agente_slug,
  COUNT(*) AS llamadas,
  SUM(tokens_in + tokens_out) AS tokens_total,
  SUM(costo_usd) AS costo_usd
FROM ia_logs
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(created_at), agente_slug
ORDER BY dia DESC, llamadas DESC;
```

```sql
-- Errores recientes
SELECT created_at, agente_slug, tipo_consulta, error_msg
FROM ia_logs
WHERE ok = 0
ORDER BY created_at DESC
LIMIT 20;
```

### Opción C — Endpoint de salud rápido

```bash
# Health check del servicio
curl -s http://localhost:5100/ia/health

# Ver agentes activos
curl -s http://localhost:5100/ia/agentes

# Llamada de prueba
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "Hola, ¿cuántos meses de datos tenemos?", "usuario_id": "santi"}'
```

---

## 9. Referencia de tipos de consulta {#tipos}

| slug | Descripción | Pasos | Agente preferido |
|---|---|---|---|
| `analisis_datos` | Pregunta sobre ventas/datos → SQL → respuesta | generar_sql → ejecutar → redactar | gemini-flash (2.5) |
| `redaccion` | Redactar texto, email, documento | redactar | gemini-flash-lite (3.1) |
| `clasificacion` | Clasificar/etiquetar información | clasificar | groq-llama o gemma |
| `resumen` | Resumir texto largo | resumir | gemini-flash-lite (3.1) |
| `generacion_documento` | Crear documentos estructurados | generar_doc | claude-sonnet (cuando esté activo) |
| `generacion_imagen` | Crear imagen con IA | generar_imagen | gemini-image (Imagen 4) |

---

## 10. Troubleshooting {#troubleshooting}

### Error: limit 0 / `generate_content_free_tier_requests`

**Causa**: Proyecto GCP sin billing vinculado ("bucket no validado").
**Solución**: [console.cloud.google.com/billing](https://console.cloud.google.com/billing) → vincular billing account al proyecto.
El upgrade a Tier 1 es instantáneo.

### Error 429 — Rate limit superado

```
HTTP 429: quota exceeded
```

**RPM**: Esperar 60 segundos. El servicio hace fallback al siguiente agente activo con key.
**RPD diario**: El límite se resetea a las 3:00 AM Colombia. Para Gemini 2.5 Flash (20 RPD) es el escenario más probable.

**Solución inmediata en BD**:
```sql
-- Temporalmente hacer que gemini-flash-lite sea el preferido del tipo analisis_datos
UPDATE ia_tipos_consulta SET agente_preferido = 'gemini-flash-lite' WHERE slug = 'analisis_datos';
```

### Respuesta vacía / texto truncado

Causa: `max_tokens` muy bajo en modelo "thinking" (Gemini 2.5, DeepSeek R1).
El servicio usa 200 tokens para el enrutador y 4096 para respuestas — no debería ocurrir en producción.
Si ocurre, revisar `ia_logs` para ver tokens_out = 0.

### Key inválida / Error 401

La key fue revocada. Generar nueva en la consola del proveedor:
```bash
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='NUEVA_KEY' WHERE slug='gemini-flash';" 2>/dev/null
```

### El servicio no responde

```bash
systemctl status ia-service.service
journalctl -u ia-service.service -n 50
systemctl restart ia-service.service
```

### Health check rápido

```bash
curl -s http://localhost:5100/ia/health
# Esperado: {"ok":true,"servicio":"ia_service_os","version":"1.0"}
```

---

## Anexo — Tabla completa de límites Gemini (datos reales del proyecto OS)

> Capturado desde Google AI Studio → Rate Limits — 2026-03-12
> Tier: **1 (free con billing vinculado)**

| Modelo (display) | Categoría | RPM | TPM | RPD |
|---|---|---|---|---|
| Gemini 2.5 Flash | Texto | 5 | 250K | 20 |
| Gemini 2.5 Pro | Texto | 0 | 0 | 0 |
| Gemini 2 Flash | Texto | 0 | 0 | 0 |
| Gemini 2 Flash Exp | Texto | 0 | 0 | 0 |
| Gemini 2 Flash Lite | Texto | 0 | 0 | 0 |
| Gemini 2.5 Flash TTS | Multimodal | 3 | 10K | 10 |
| Gemini 2.5 Pro TTS | Multimodal | 0 | 0 | 0 |
| Gemma 3 1B | Otros | 30 | 15K | 14,400 |
| Gemma 3 2B | Otros | 30 | 15K | 14,400 |
| Gemma 3 4B | Otros | 30 | 15K | 14,400 |
| Gemma 3 12B | Otros | 30 | 15K | 14,400 |
| Gemma 3 27B | Otros | 30 | 15K | 14,400 |
| Imagen 4 Generate | Multimodal | — | — | 25 |
| Imagen 4 Ultra Generate | Multimodal | — | — | 25 |
| Imagen 4 Fast Generate | Multimodal | — | — | 25 |
| Gemini Embedding 1 | Otros | 100 | 30K | 1K |
| Gemini Embedding 2 | Otros | 100 | 30K | 1K |
| Gemini 3 Flash | Texto | 5 | 250K | 20 |
| Gemini 2.5 Flash Lite | Texto | 10 | 250K | 20 |
| Gemini 3.1 Flash Lite | Texto | 15 | 250K | 500 |
| Gemini 3.1 Pro | Texto | 0 | 0 | 0 |
| Nano Banana (2.5 Flash Preview Image) | Multimodal | 0 | 0 | 0 |
| Nano Banana Pro (3 Pro Image) | Multimodal | 0 | 0 | 0 |
| Nano Banana 2 (3.1 Flash Image) | Multimodal | 0 | 0 | 0 |
| Gemini Robotics ER 1.5 Preview | Otros | 10 | 250K | 20 |
| Computer Use Preview | Otros | 0 | 0 | 0 |
| Deep Research Pro Preview | Agentes | 0 | 0 | 0 |
| Gemini 2.5 Flash Native Audio Dialog | Live API | Ilimitado | 1M | Ilimitado |
| Veo 3 Generate | Multimodal | 0 | — | 0 |
| Veo 3 Fast Generate | Multimodal | 0 | — | 0 |

> Los modelos con 0/0/0 no están disponibles en este tier o son preview cerrada.
> "Nano Banana" es el código interno de modelos de imagen en preview — no usar por ahora.
> Para referencia oficial: [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits?hl=es-419)

---

*Última actualización: 2026-03-12*
