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
7. [Referencia de tipos de consulta](#tipos)
8. [Troubleshooting](#troubleshooting)

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
- `"google"` → `proveedores/google.py` (Gemini)
- `"anthropic"` → `proveedores/anthropic_prov.py` (Claude)

---

## 2. Google Gemini {#gemini}

### Obtener API key

1. Ir a [aistudio.google.com](https://aistudio.google.com) → Get API Key → Create API Key
2. Seleccionar proyecto de Google Cloud (o crear uno)
3. **No requiere tarjeta de crédito para el tier gratuito**
4. La key empieza con `AIzaSy...`

> **Nota billing**: Google Gemini API tiene tier gratuito sin necesidad de cuenta de facturación. Si superas los límites gratuitos y quieres más, ahí sí se activa billing. Para el uso actual de OS, el tier gratuito es más que suficiente.

### Endpoint base

```
https://generativelanguage.googleapis.com/v1beta
```

Llamada: `POST /models/{modelo}:generateContent?key={API_KEY}`

### Modelos disponibles (2026)

| slug en ia_agentes | modelo_id | Notas |
|---|---|---|
| gemini-flash | gemini-2.5-flash | Mejor balance velocidad/calidad. Default recomendado |
| gemini-flash-lite | gemini-2.0-flash-lite | Más rápido, para enrutador y clasificaciones |
| gemini-pro | gemini-2.5-pro | Máxima calidad, más lento y costoso |
| gemini-imagen | gemini-2.5-flash-image | Genera imágenes (500/día gratis) |

### Límites del tier gratuito (por proyecto, NO por key)

| Modelo | RPM | TPM | RPD |
|---|---|---|---|
| gemini-2.5-flash | 10 | 250,000 | 250 |
| gemini-2.0-flash-lite | 30 | 1,000,000 | 1,500 |
| gemini-2.5-pro | 5 | 250,000 | 25 |
| gemini-2.5-flash-image | 10 img | — | 500 img |

**RPM** = requests por minuto | **TPM** = tokens por minuto | **RPD** = requests por día

**Reset**: medianoche Pacific Time = **3:00 AM Colombia** (UTC-5)

**Importante**: Los límites son por PROYECTO de Google Cloud, no por API key. Crear más keys del mismo proyecto no aumenta los límites.

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

Modelo: `gemini-2.5-flash-image` (free: 500/día)

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
| Respuesta vacía con max_tokens bajo | Gemini 2.5 es "thinking" — usa tokens internos para razonar antes de responder | Usar mínimo 200 max_tokens para enrutador, 4096 para respuestas normales |
| Error 429 "quota exceeded" | RPM o RPD superado | Esperar 1 min (RPM) o hasta las 3 AM Colombia (RPD) |
| Error 400 "imagen model not available" | Usando modelo de imagen con plan gratuito incorrecto | Usar `gemini-2.5-flash-image` (no "imagen-4.0" ni "imagen-3") |
| Key bloqueada por GitHub | Key expuesta en un commit | Crear nueva key en AI Studio, actualizar BD y .env |

### Costos (tier pago, referencia)

| Modelo | Input | Output |
|---|---|---|
| gemini-2.5-flash | $0.15/M tokens | $0.60/M tokens |
| gemini-2.5-pro | $1.25/M tokens | $10.00/M tokens |
| gemini-2.5-flash-image | $0.039/imagen | — |

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

| slug | modelo_id | Tokens contexto | Velocidad |
|---|---|---|---|
| groq-llama | llama-3.3-70b-versatile | 128k | ~800 tok/s |
| groq-llama-fast | llama-3.1-8b-instant | 128k | ~2000 tok/s |
| groq-mixtral | mixtral-8x7b-32768 | 32k | ~500 tok/s |

**Recomendado para enrutador**: `llama-3.1-8b-instant` — el más rápido del ecosistema IA.

### Límites del tier gratuito

| Modelo | RPM | TPM | RPD |
|---|---|---|---|
| llama-3.3-70b | 30 | 6,000 | 1,000 |
| llama-3.1-8b | 30 | 6,000 | 14,400 |
| mixtral-8x7b | 30 | 5,000 | 14,400 |

**Reset**: cada día calendario UTC

### Gotchas

- **Groq no genera imágenes** — solo texto
- Velocidad es su diferencial: ideal para enrutador, clasificador, respuestas cortas
- Si el modelo está "ocupado" devuelve 503 — el servicio hace fallback automático a Gemini

---

## 4. DeepSeek {#deepseek}

### Obtener API key

1. Ir a [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create Key
2. **Requiere recarga mínima de $5 USD** (no hay tier completamente gratuito en producción)
3. Tier gratuito: solo disponible en el chat web, no por API

### Endpoint

```
https://api.deepseek.com/v1/chat/completions
```

Formato 100% compatible con OpenAI. Usar proveedor `"openai"` en `ia_agentes`.

### Modelos

| slug | modelo_id | Uso ideal |
|---|---|---|
| deepseek-chat | deepseek-chat | Conversación, redacción, análisis (más barato) |
| deepseek-r1 | deepseek-reasoner | Razonamiento complejo, SQL difícil |

### Precios (muy económicos)

| Modelo | Input | Output |
|---|---|---|
| deepseek-chat | $0.07/M tokens | $1.10/M tokens |
| deepseek-reasoner (R1) | $0.55/M tokens | $2.19/M tokens |

**DeepSeek es el más barato** del mercado para razonamiento complejo (R1 vs GPT-o1/Claude Opus).

### Gotchas

- **DeepSeek-R1** tiene "thinking tokens" internos (similar a Gemini 2.5) — pueden aparecer en `<think>...</think>` tags en la respuesta. El formateador los ignora.
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

### Modelos actuales (Agosto 2025)

| slug | modelo_id | Uso ideal |
|---|---|---|
| claude-sonnet | claude-sonnet-4-6 | Default — mejor balance |
| claude-opus | claude-opus-4-6 | Máxima calidad, SQL complejo |
| claude-haiku | claude-haiku-4-5-20251001 | Rápido y barato |

### Precios

| Modelo | Input | Output |
|---|---|---|
| claude-haiku-4-5 | $0.80/M tokens | $4.00/M tokens |
| claude-sonnet-4-6 | $3.00/M tokens | $15.00/M tokens |
| claude-opus-4-6 | $15.00/M tokens | $75.00/M tokens |

### Rate limits (dependen del tier)

- **Tier 1** ($0–$50 gastados): 50 RPM, 40,000 TPM
- **Tier 2** ($50–$500 gastados): 1,000 RPM, 80,000 TPM
- **Tier 4** (>$5,000): sin límites prácticos

### Gotchas

- El sistema message va en campo `"system"` separado (no en el array `messages`)
- Nuestro proveedor `anthropic_prov.py` ya maneja esto: extrae el role `system` del array
- No genera imágenes (API de texto/análisis únicamente)
- El más caro del grupo — reservar para análisis complejos donde calidad importa

---

## 6. Cómo agregar una API key {#agregar-api-key}

### Paso 1 — Insertar/actualizar en BD local

```sql
-- Verificar el slug del agente:
SELECT slug, nombre, proveedor, activo, api_key != '' AS tiene_key FROM ia_agentes ORDER BY orden;

-- Agregar key (reemplazar VALUES según el agente):
UPDATE ia_agentes
SET api_key = 'TU_KEY_AQUÍ', activo = 1
WHERE slug = 'groq-llama';
```

Correr en terminal:
```bash
mysql -u osadmin -pEpist2487. ia_service_os -e "UPDATE ia_agentes SET api_key='TU_KEY', activo=1 WHERE slug='groq-llama';" 2>/dev/null
```

### Paso 2 — Backup en scripts/.env

Agregar al archivo `scripts/.env` (no commiteado — está en .gitignore):
```
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
```

El archivo `.env` es el backup de emergencia. La BD es la fuente de verdad operativa.

### Paso 3 — Verificar

```bash
curl -s http://localhost:5100/ia/agentes | python3 -m json.tool | grep -A3 '"slug"'
```

### Qué NUNCA hacer

- ❌ Escribir la key en un `.md`, comentario de código, o mensaje de commit
- ❌ Hacer `git add scripts/.env`
- ❌ Copiar la key en este manual u otro documento del repo
- ✅ La key va SOLO en la BD y en `scripts/.env`

---

## 7. Referencia de tipos de consulta {#tipos}

| slug | Descripción | Pasos | Agente preferido |
|---|---|---|---|
| `analisis_datos` | Pregunta sobre ventas/datos → SQL → respuesta | generar_sql → ejecutar → redactar | claude-sonnet o gemini-flash |
| `redaccion` | Redactar texto, email, documento | redactar | gemini-flash |
| `clasificacion` | Clasificar/etiquetar información | clasificar | groq-llama |
| `resumen` | Resumir texto largo | resumir | gemini-flash |
| `generacion_documento` | Crear documentos estructurados | generar_doc | claude-sonnet |
| `generacion_imagen` | Crear imagen con IA | generar_imagen | gemini-imagen |

---

## 8. Troubleshooting {#troubleshooting}

### Error 429 — Rate limit superado

```
HTTP 429: quota exceeded
```

**Gemini**: Esperar 60 segundos (RPM) o hasta las 3 AM Colombia (RPD diario).
**Groq**: Esperar 60 segundos.
El servicio hace fallback automático al siguiente agente activo con key.

### Respuesta vacía

Causa probable: `max_tokens` muy bajo en modelo "thinking" (Gemini 2.5, DeepSeek R1).
El servicio usa 200 tokens para el enrutador y 4096 para respuestas — no debería ocurrir en producción.

### Key inválida / Error 401

```
HTTP 401: API key not valid
```

La key fue revocada o es incorrecta. Generar nueva en la consola del proveedor y actualizar la BD.

### Imagen no generada — Error 400

```
HTTP 400: imagen model not available
```

Usar solo `gemini-2.5-flash-image`. Otros modelos de imagen (imagen-3, imagen-4.0) requieren plan pago.

### El enrutador clasifica mal

Síntoma: preguntas de ventas se clasifican como `redaccion`.
Causa: Groq sin key → fallback a Gemini → Gemini 2.5 Flash necesita más tokens que el mínimo.
Verificar: `SELECT slug, activo, api_key != '' AS tiene_key FROM ia_agentes WHERE slug LIKE 'groq%';`

### Servicio caído

```bash
systemctl status ia-service.service
journalctl -u ia-service.service -n 50
systemctl restart ia-service.service
```

### Health check rápido

```bash
curl -s http://localhost:5100/ia/health
# Respuesta esperada: {"ok":true,"servicio":"ia_service_os","version":"1.0"}
```

---

*Última actualización: 2026-03-12*
