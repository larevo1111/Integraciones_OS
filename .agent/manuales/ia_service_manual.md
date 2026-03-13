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

> **Estado actual OS (2026-03-12)**: **Nivel de pago 1 activo** ✅ — límites pagados desbloqueados.

### Endpoint base

```
https://generativelanguage.googleapis.com/v1beta
```

Llamada: `POST /models/{modelo_id}:generateContent?key={API_KEY}`

### Límites — Nivel de pago 1 (tier pagado — estado actual del proyecto OS)

> Fuente: Google AI Studio → "Límite de frecuencia de la API de Gemini" → proyecto OS — 2026-03-12
> El tier pago es DRÁSTICAMENTE superior al free tier — vale la pena absolutamente.

| Modelo (display) | modelo_id para API | RPM | TPM | RPD | Uso en OS |
|---|---|---|---|---|---|
| **Gemini 2.5 Pro** | `gemini-2.5-pro` | 150 | 2M | **1K** | ✅ `gemini-pro` — análisis SQL complejo |
| **Gemini 2.5 Flash** | `gemini-2.5-flash` | 1K | 1M | **10K** | ✅ `gemini-flash` — consultas generales |
| **Gemini 2 Flash** | `gemini-2.0-flash` | 2K | 4M | **Ilimitado** | Disponible si se necesita |
| **Gemini 2 Flash Lite** | `gemini-2.0-flash-lite` | 4K | 4M | **Ilimitado** | Disponible si se necesita |
| **Gemini 2.5 Flash Lite** | `gemini-2.5-flash-lite-preview` | 4K | 4M | **Ilimitado** | Disponible si se necesita |
| **Gemini 3 Flash** | `gemini-3.0-flash` | 1K | 2M | **10K** | Similar a 2.5 Flash |
| **Gemini 3.1 Flash Lite** | `gemini-3.1-flash-lite` | 4K | 4M | **150K** | ✅ `gemini-flash-lite` — volumen alto |
| **Gemini 3.1 Pro** | `gemini-3.1-pro` | 25 | 2M | **250** | Disponible |
| **Gemma 3 27B** | `gemma-3-27b-it` | 30 | 15K | **14.4K** | ✅ `gemma-router` — enrutador |
| **Gemma 3 12B/4B/2B/1B** | `gemma-3-12b-it` etc. | 30 | 15K | **14.4K** | Alternativas |
| **Imagen 4 Generate** | `imagen-4.0-generate-preview` | 10 | — | **70** | Imágenes alta calidad |
| **Imagen 4 Fast Generate** | `imagen-4.0-fast-generate-preview` | 10 | — | **70** | ✅ `gemini-image` — imágenes |
| **Imagen 4 Ultra Generate** | `imagen-4.0-ultra-generate-preview` | 5 | — | **30** | Máxima calidad imágenes |
| **Nano Banana (2.5 Flash Image)** | `gemini-2.5-flash-preview-image-generation` | 500 | 500K | **2K** | Preview — mucho mejor que Imagen 4 en RPD |
| **Gemini 2.5 Flash TTS** | `gemini-2.5-flash-tts` | 10 | 10K | 100 | Texto a voz |
| **Gemini Embedding 1** | `text-embedding-004` | 3K | 1M | Ilimitado | Embeddings |

> **Los límites son por PROYECTO**, no por API key. Crear más keys del mismo proyecto no aumenta los límites.

### Comparativa free tier vs nivel de pago

| Modelo | RPD free tier | RPD **nivel pago 1** |
|---|---|---|
| Gemini 2.5 Flash | 20 | **10,000** (500x más) |
| Gemini 2.5 Flash Lite | 20 | **Ilimitado** |
| Gemini 3.1 Flash Lite | 500 | **150,000** (300x más) |
| Gemini 2.5 Pro | ~0 | **1,000** |
| Imagen 4 Fast | 25 | **70** |

> **Conclusión**: El tier gratuito no tiene casi nada en la práctica. El nivel de pago es el correcto para OS.

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

### Estrategia recomendada (nivel de pago 1)

Con el tier pagado, la estrategia cambia: ahora el modelo Pro está disponible para lo que importa.

| Tarea | Agente en BD | Modelo | RPD | Por qué |
|---|---|---|---|---|
| **Enrutador** (clasificar intención) | `gemma-router` → `groq-llama` | gemma-3-27b-it | 14,400 | Tarea simple, no gastar RPD de Pro |
| **Análisis de datos SQL** | `gemini-pro` | gemini-2.5-pro | **1,000** | ✅ El mejor para SQL complejo, JOINs, aggregaciones |
| **Conversación / redacción** | `gemini-flash` | gemini-2.5-flash | **10,000** | Excelente para texto, más que suficiente |
| **Alto volumen / bot** | `gemini-flash-lite` | gemini-3.1-flash-lite | **150,000** | Prácticamente ilimitado |
| **Generación de imágenes** | `gemini-image` | imagen-4.0-fast-generate-preview | **70** | Correcto para imágenes |
| **SQL muy complejo futuro** | `claude-sonnet` (cuando esté activo) | claude-sonnet-4-6 | — | Máxima calidad, reservar para edge cases |

### Configuración actual de ia_agentes (marzo 2026 — nivel pago 1)

```
gemini-pro        → gemini-2.5-pro          → analisis_datos ← PRINCIPAL para SQL
gemini-flash      → gemini-2.5-flash        → redaccion, resumen (10K RPD)
gemini-flash-lite → gemini-3.1-flash-lite   → alto volumen, bot (150K RPD)
gemma-router      → gemma-3-27b-it          → enrutador (14.4K RPD)
gemini-image      → imagen-4.0-fast-...     → generacion_imagen (70 RPD)
groq-llama        → llama-3.1-8b-instant    → enrutador alternativo (pendiente key)
claude-sonnet     → claude-sonnet-4-6       → generacion_documento (pendiente key)
```

### ¿Cómo funciona la selección de modelo? (respuesta a la pregunta de Santi)

```
Cada modelo = una fila en ia_agentes con su modelo_id
                        ↓
El tipo de consulta (ia_tipos_consulta) tiene un agente_preferido
  analisis_datos → gemini-pro
  redaccion      → gemini-flash
  enrutamiento   → groq-llama (fallback: gemma-router)
                        ↓
Si ese agente no tiene key o está inactivo → fallback automático al
primero activo con key en orden de columna `orden`
                        ↓
El caller puede forzar cualquier agente pasando agente='gemini-pro'
```

---

## 8. Monitoreo del consumo {#monitoreo}

### Opción A — Endpoints propios (consumo real desde ia_consumo_diario)

**Tabla `ia_consumo_diario`**: se actualiza automáticamente con cada llamada al servicio.
Guarda: llamadas, errores, tokens_in/out, costo_usd, latencia promedio — por día y por agente.

```bash
# Consumo de hoy (todos los agentes)
curl -s "http://localhost:5100/ia/consumo"

# Consumo de la semana
curl -s "http://localhost:5100/ia/consumo?periodo=semana"

# Consumo de hoy solo para gemini-pro
curl -s "http://localhost:5100/ia/consumo?agente=gemini-pro"

# Histórico últimos 30 días
curl -s "http://localhost:5100/ia/consumo/historico"

# Histórico últimos 7 días para un agente
curl -s "http://localhost:5100/ia/consumo/historico?dias=7&agente=gemini-flash"
```

**Respuesta del endpoint `/ia/consumo`:**
```json
{
  "ok": true,
  "periodo": "hoy",
  "totales": {
    "llamadas": 5,
    "tokens_total": 45000,
    "costo_usd": 0.056,
    "errores": 0
  },
  "por_agente": [{
    "agente_slug": "gemini-pro",
    "modelo_id": "gemini-2.5-pro",
    "llamadas": 3,
    "tokens_total": 40000,
    "costo_usd": 0.050,
    "limite_rpd_diario": 1000,
    "pct_limite_hoy": 0.3,
    "estado": "ok"   // ok | advertencia (70%) | critico (90%) | ilimitado
  }],
  "alertas": []  // agentes en estado critico o advertencia
}
```

**Periodos disponibles**: `hoy`, `ayer`, `semana`, `mes`, `todo`

### Opción B — SQL directo en ia_consumo_diario

```sql
-- Resumen de hoy
SELECT agente_slug, llamadas, tokens_total, costo_usd,
       ROUND(llamadas * 100.0 / a.rate_limit_rpd, 1) AS pct_limite
FROM ia_consumo_diario c JOIN ia_agentes a ON a.slug = c.agente_slug
WHERE fecha = CURDATE() ORDER BY llamadas DESC;

-- Costo acumulado del mes
SELECT SUM(costo_usd) AS costo_mes FROM ia_consumo_diario
WHERE fecha >= DATE_FORMAT(CURDATE(), '%Y-%m-01');
```

### Opción C — Google AI Studio (consumo Gemini en tiempo real)

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

> Capturado desde Google AI Studio → "Límite de frecuencia de la API de Gemini" — 2026-03-12
> **Tier: Nivel de pago 1** (billing activo — límites DRÁSTICAMENTE superiores al free tier)

| Modelo (display) | Categoría | RPM | TPM | RPD |
|---|---|---|---|---|
| **Gemini 2.5 Flash** | Texto | 1,000 | 1M | **10,000** |
| **Gemini 2.5 Pro** | Texto | 150 | 2M | **1,000** |
| **Gemini 2 Flash** | Texto | 2,000 | 4M | **Ilimitado** |
| Gemini 2 Flash Exp | Texto | 10 | 250K | 500 |
| **Gemini 2 Flash Lite** | Texto | 4,000 | 4M | **Ilimitado** |
| Gemini 2.5 Flash TTS | Multimodal | 10 | 10K | 100 |
| Gemini 2.5 Pro TTS | Multimodal | 10 | 10K | 50 |
| Gemma 3 1B | Otros | 30 | 15K | 14,400 |
| Gemma 3 2B | Otros | 30 | 15K | 14,400 |
| Gemma 3 4B | Otros | 30 | 15K | 14,400 |
| Gemma 3 12B | Otros | 30 | 15K | 14,400 |
| **Gemma 3 27B** | Otros | 30 | 15K | **14,400** |
| **Imagen 4 Generate** | Multimodal | 10 | — | **70** |
| Imagen 4 Ultra Generate | Multimodal | 5 | — | 30 |
| **Imagen 4 Fast Generate** | Multimodal | 10 | — | **70** |
| Gemini Embedding 1 | Otros | 3,000 | 1M | Ilimitado |
| **Gemini 3 Flash** | Texto | 1,000 | 2M | **10,000** |
| **Gemini 2.5 Flash Lite** | Texto | 4,000 | 4M | **Ilimitado** |
| Gemini 3.1 Pro | Texto | 25 | 2M | 250 |
| **Nano Banana** (Gemini 2.5 Flash Preview Image) | Multimodal | 500 | 500K | **2,000** |
| **Gemini 3.1 Flash Lite** | Texto | 4,000 | 4M | **150,000** |
| Nano Banana Pro (Gemini 3 Pro Image) | Multimodal | 20 | 100K | 250 |
| Nano Banana 2 (Gemini 3.1 Flash Image) | Multimodal | 100 | 200K | 1,000 |

> **Negrita** = modelos relevantes para el proyecto OS.
> "Nano Banana" = código interno de modelos de generación de imágenes en preview. Interesante: 2K RPD vs 70 de Imagen 4.
> Para referencia oficial: [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits?hl=es-419)

---

*Última actualización: 2026-03-12*
