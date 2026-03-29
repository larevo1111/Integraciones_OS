# Catálogo de APIs — OS

> Referencia de todos los servicios HTTP internos del ecosistema OS.
> Cualquier módulo nuevo puede llamar estas APIs directamente.
> **Actualizar cada vez que se cree o modifique un endpoint.**

---

## Convenciones globales

- Todos los servicios corren en `localhost` — no están expuestos a internet directamente
- Body y respuestas siempre JSON (`Content-Type: application/json`)
- Respuesta siempre incluye `"ok": true|false`
- Errores retornan campo `"error"` con descripción

---

## 1. Servicio IA — `ia_service`

**Base URL**: `http://localhost:5100`
**Proceso**: systemd `ia-service.service`
**BD**: `ia_service_os` (MariaDB local)
**Propósito**: Motor de IA central para toda la empresa. Consultas en lenguaje natural, análisis SQL, redacción, búsqueda web, etc.

### Cómo llamarlo desde Python

```python
import requests

resp = requests.post('http://localhost:5100/ia/consultar', json={
    'pregunta':       '¿Cuánto vendimos ayer?',
    'usuario_id':     'santi',           # identificador del usuario
    'canal':          'erp',             # telegram | erp | api | crm | whatsapp
    'empresa':        'ori_sil_2',       # empresa activa
    'nombre_usuario': 'Santiago',        # nombre legible (para contexto)
    # opcionales:
    'tipo':            None,             # None = el enrutador lo detecta automáticamente
    'agente':          None,             # None = usa el preferido del tipo
    'conversacion_id': None,             # para continuar conversación existente
    'tema':            None,             # None = el enrutador lo detecta
    'contexto_extra':  '',               # texto libre con contexto de pantalla (ERP)
    'cliente': {                         # si es atención al cliente
        'nombre':         'Juan Pérez',
        'identificacion': '12345678',
        'tipo_id':        'CC',
        'telefono':       '3001234567',
        'email':          'juan@email.com',
    },
    'imagen_base64':  None,              # imagen adjunta (visión multimodal)
    'imagen_mime':    'image/jpeg',
})
data = resp.json()
# data = {
#   'ok': True,
#   'respuesta': 'Las ventas de ayer fueron...',
#   'formato': 'texto|tabla|lista',
#   'tabla': { 'columnas': [...], 'filas': [...] },  # si formato=tabla
#   'sql': 'SELECT ...',                              # si ejecutó SQL
#   'conversacion_id': 42,
#   'agente': 'gemini-flash',
#   'tokens': 1234,
#   'costo_usd': 0.000092,
# }
```

### Endpoints completos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ia/health` | Health check — `{"ok": true}` |
| POST | `/ia/consultar` | Consulta principal (ver body arriba) |
| GET | `/ia/agentes` | Lista agentes activos con capacidades |
| GET | `/ia/tipos` | Lista tipos de consulta activos |
| GET | `/ia/consumo?periodo=hoy\|ayer\|semana\|mes` | Consumo por agente |
| GET | `/ia/consumo/historico?dias=30` | Histórico día a día |
| POST | `/ia/conexion/test` | Prueba conexión BD `{conexion_id}` |
| POST | `/ia/esquema/sync` | Sincroniza schema BD `{tema_id, empresa}` |
| GET | `/ia/logica-negocio?empresa=ori_sil_2` | Lista fragmentos de lógica activos |
| POST | `/ia/logica-negocio` | Crea/actualiza fragmento `{concepto, explicacion, keywords}` |

### Agentes disponibles

**Catálogo completo**: `.agent/docs/CATALOGO_AGENTES.md`

**Cloud:**
| slug | Modelo | Mejor para |
|------|--------|------------|
| `gemini-flash` | gemini-2.5-flash | Análisis SQL, docs largos (default analítico) |
| `gemini-flash-lite` | gemini-2.5-flash-lite | Conversación, redacción (barato y rápido) |
| `groq-llama` | llama-3.3-70b | Enrutamiento, clasificación (gratis) |
| `cerebras-llama` | llama3.1-8b | Tareas simples, resúmenes (2,200 t/s, 8K ctx) |
| `gemini-pro` | gemini-2.5-pro | Análisis complejos (nivel 6+) |
| `claude-sonnet` | claude-sonnet-4-6 | Documentos premium (nivel 6+) |
| `deepseek-chat` | deepseek-chat | Respaldo |

**Locales (Ollama — GPU, costo $0):**
| slug | Modelo | Mejor para |
|------|--------|------------|
| `ollama-qwen-coder` | qwen2.5-coder:14b | SQL, código |
| `ollama-qwen-14b` | qwen2.5:14b | Conversación, español |
| `ollama-qwen-7b` | qwen2.5:7b | Router versátil, tareas rápidas |
| `ollama-deepseek-r1` | deepseek-r1:14b | Razonamiento paso a paso |
| `ollama-llama-3b` | llama3.2:3b | Router ultra liviano |

---

## 2. WA Bridge — `wa_bridge`

**Base URL**: `http://localhost:3100`
**Proceso**: systemd `wa-bridge.service`
**BD**: `os_whatsapp` (MariaDB local)
**Propósito**: Servicio transversal de WhatsApp. Envío y recepción de mensajes para cualquier módulo OS.

### Cómo llamarlo desde Python

```python
# Instalar: pip install requests
# O usar wa_bridge/wa_bridge.py directamente:
from wa_bridge.wa_bridge import wa_send_text, wa_send_image, wa_send_document

# Enviar texto
wa_send_text('573001234567', 'Hola! Tu pedido fue despachado.')

# Con caller_service para registro de quién lo mandó
requests.post('http://localhost:3100/api/send/text', json={
    'to':             '573001234567',  # número sin +
    'message':        'Hola!',
    'caller_service': 'crm',           # quién lo pidió (para auditoría)
    'caller_user':    'santi',
})
```

### Endpoints

| Método | Ruta | Body | Descripción |
|--------|------|------|-------------|
| GET | `/api/status` | — | Estado conexión + QR si pendiente |
| POST | `/api/send/text` | `{to, message, caller_service?, caller_user?}` | Enviar texto |
| POST | `/api/send/image` | `{to, filePath\|base64, caption?, caller_service?, caller_user?}` | Enviar imagen |
| POST | `/api/send/audio` | `{to, filePath\|base64, ptt?, caller_service?, caller_user?}` | Enviar audio/nota de voz |
| POST | `/api/send/document` | `{to, filePath\|base64, fileName?, mimetype?, caller_service?, caller_user?}` | Enviar documento |
| POST | `/api/send/video` | `{to, filePath\|base64, caption?, caller_service?, caller_user?}` | Enviar video |
| GET | `/api/mensajes?numero=573...&limite=50` | — | Consultar mensajes entrantes |
| GET | `/api/contactos` | — | Lista contactos conocidos |

### Respuesta de envío

```json
{ "ok": true, "to": "573001234567@s.whatsapp.net", "message_id": "ABCD1234..." }
```

### Formato webhook entrante (si WA_WEBHOOK_URL está configurado)

El bridge hace POST a `WA_WEBHOOK_URL` por cada mensaje entrante:

```json
{
  "messageId":      "ABC123",
  "fromJid":        "573001234567@s.whatsapp.net",
  "fromNumber":     "573001234567",
  "fromName":       "Juan Pérez",
  "esGrupo":        false,
  "groupJid":       null,
  "tipo":           "text | image | audio | voice | video | document | sticker | location | contact | reaction",
  "texto":          "Hola!",
  "caption":        null,
  "mediaPath":      "/ruta/local/archivo",
  "mediaMime":      "image/jpeg",
  "mediaSizeBytes": 45231,
  "mediaDuracion":  null,
  "mediaFilename":  null,
  "latitude":       null,
  "longitude":      null,
  "locationName":   null,
  "reactionEmoji":  null,
  "quotedId":       null,
  "quotedTexto":    null,
  "esReenviado":    false,
  "tsWa":           1774576646
}
```

### BD `os_whatsapp` — tablas

| Tabla | Descripción |
|-------|-------------|
| `wa_mensajes_entrantes` | Todo lo que llega al número vinculado (todos los tipos y campos) |
| `wa_mensajes_salientes` | Todo lo que se manda (con `caller_service` para saber quién lo pidió) |
| `wa_contactos` | Directorio de números conocidos con nombre, contadores entrada/salida |

### Notas operativas

- `to` siempre es número sin `+` (ej: `'573001234567'`)
- `filePath` debe ser ruta absoluta en el servidor donde corre el bridge
- `ptt=true` → nota de voz (ícono micrófono); `ptt=false` → archivo de audio
- `caller_service` es libre: `'crm'`, `'ia_service'`, `'pipeline'`, etc.
- Credenciales WhatsApp en `wa_bridge/auth/` — nunca commitear
- Log: `logs/wa_bridge.log`

---

## 3. Admin IA — `ia-admin`

**Base URL**: `http://localhost:9200`
**URL pública**: `ia.oscomunidad.com`
**Proceso**: systemd `os-ia-admin.service`
**Propósito**: Panel de administración del ia_service (agentes, prompts, logs, conversaciones, super agente).
**Nota**: API interna del panel — no se llama desde otros módulos.

---

## 4. Sistema Gestión OS

**Base URL**: `http://localhost:9300`
**URL pública**: `gestion.oscomunidad.com`
**Proceso**: systemd `os-gestion.service`
**Propósito**: App de tareas y jornadas del equipo.
**Nota**: API interna del sistema — ver `.agent/contextos/sistema_gestion.md` para endpoints completos.

---

## 5. Ollama — Modelos IA Locales

**Base URL**: `http://localhost:11434`
**URL pública**: `ollama.oscomunidad.com`
**Proceso**: systemd `ollama.service`
**Hardware**: NVIDIA RTX 3060 12GB VRAM, CUDA 13.1
**Propósito**: Modelos de IA locales (costo $0). 5 modelos instalados.

### Cómo llamarlo desde Python

```python
import requests

# API OpenAI-compatible (recomendada — misma que usa ia_service)
resp = requests.post('http://localhost:11434/v1/chat/completions', json={
    'model': 'qwen2.5-coder:14b',
    'messages': [{'role': 'user', 'content': '¿Cuánto es 2+2?'}],
})
data = resp.json()
print(data['choices'][0]['message']['content'])

# API nativa Ollama (más simple para prompts directos)
resp = requests.post('http://localhost:11434/api/generate', json={
    'model': 'qwen2.5-coder:14b',
    'prompt': 'Escribe una query SQL...',
    'stream': False,
})
print(resp.json()['response'])
```

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/tags` | Lista modelos instalados |
| GET | `/api/ps` | Modelos cargados en VRAM |
| POST | `/api/generate` | Generar texto (API nativa) |
| POST | `/api/chat` | Chat con historial (API nativa) |
| POST | `/v1/chat/completions` | Chat OpenAI-compatible |
| POST | `/api/pull` | Descargar modelo nuevo |
| DELETE | `/api/delete` | Eliminar modelo |

### Modelos instalados

| modelo | Tamaño | VRAM | Mejor para |
|--------|--------|------|------------|
| `qwen2.5-coder:14b` | 9.0 GB | ~9 GB | SQL, código |
| `qwen2.5:14b` | 9.0 GB | ~9 GB | Conversación, español |
| `qwen2.5:7b` | 4.7 GB | ~4.7 GB | Router, tareas rápidas |
| `deepseek-r1:14b` | 9.0 GB | ~9 GB | Razonamiento |
| `llama3.2:3b` | 2.0 GB | ~2.8 GB | Router ultra liviano |

### Notas operativas

- Solo un modelo de 14B cabe en VRAM a la vez (~9 GB de 12 GB disponibles)
- `llama3.2:3b` puede correr simultáneo con cualquier 14B
- Ollama carga/descarga modelos automáticamente (timeout 5 min inactividad)
- Gestión: `ollama list`, `ollama ps`, `ollama pull <modelo>`, `ollama rm <modelo>`

---

## Cómo agregar un servicio nuevo

1. Crear sección con número siguiente
2. Incluir: Base URL, proceso systemd, BD, propósito
3. Ejemplo de llamada desde Python/JS
4. Tabla de endpoints
5. Notas operativas relevantes
6. Mencionar en `MANIFESTO.md` sección 11
