# Catálogo de Agentes IA — Origen Silvestre

> Referencia de todos los agentes de IA disponibles en el ecosistema OS.
> **Fuente de verdad**: tabla `ia_agentes` en BD `ia_service_os` (MariaDB local).
> **Actualizar este documento cada vez que se agregue, modifique o desactive un agente.**
> Benchmark de rendimiento: `.agent/docs/COMPARACION_AGENTES_IA.md`

---

## Agentes Cloud

### 1. gemini-flash — Gemini 2.5 Flash
- **Proveedor**: Google (Generative Language API)
- **Modelo**: `gemini-2.5-flash`
- **Contexto**: 1M tokens entrada / 8K salida
- **Costo**: $0.075 input / $0.30 output por millón de tokens
- **Rate limit**: 1,000 RPM / 10,000 RPD
- **Nivel mínimo**: 1
- **Credenciales**: API key Google AI en `ia_agentes.api_key` (slug `gemini-flash`). Misma key compartida con todos los agentes Google.
- **Capacidades**: vision, sql, codigo, documentos, contexto_largo
- **Rol actual**: Agente SQL principal. Default para `analisis_datos` y `generacion_documento`. Procesa DDL de 28K tokens bien.
- **Notas**: Mejor optimizado que Groq para entrada masiva (13s vs 19s en benchmark SQL).

### 2. gemini-flash-lite — Gemini 2.5 Flash Lite
- **Proveedor**: Google
- **Modelo**: `gemini-2.5-flash-lite`
- **Contexto**: 1M tokens entrada / 8K salida
- **Costo**: $0.037 input / $0.15 output por millón de tokens
- **Rate limit**: 4,000 RPM / ilimitado RPD
- **Nivel mínimo**: 1
- **Credenciales**: misma API key Google AI
- **Capacidades**: vision, enrutamiento
- **Rol actual**: Default para `conversacion`, `redaccion`, `aprendizaje`, `busqueda_web`. Fallback de gemini-flash.
- **Notas**: RPD ilimitado lo hace ideal como fallback. Más directo que flash, pero menos elaborado en queries complejas.

### 3. gemini-pro — Gemini 2.5 Pro
- **Proveedor**: Google
- **Modelo**: `gemini-2.5-pro`
- **Contexto**: 1M tokens entrada / 8K salida
- **Costo**: $1.25 input / $10.00 output por millón de tokens
- **Rate limit**: 150 RPM / 1,000 RPD
- **Nivel mínimo**: 6 (premium — solo Santiago y nivel 6+)
- **Credenciales**: misma API key Google AI
- **Capacidades**: vision, sql, codigo, razonamiento, documentos, contexto_largo
- **Rol actual**: Máxima calidad para análisis complejos.

### 4. gemini-image — Gemini 2.5 Flash Image
- **Proveedor**: Google
- **Modelo**: `gemini-2.5-flash-image`
- **Costo**: $52.00 input por millón de tokens
- **Rate limit**: 2 RPM / 70 RPD
- **Nivel mínimo**: 1
- **Credenciales**: misma API key Google AI
- **Capacidades**: generación de imágenes
- **Rol actual**: Único agente de imágenes.

### 5. gemma-router — Gemma 3 27B IT
- **Proveedor**: Google
- **Modelo**: `gemma-3-27b-it`
- **Costo**: $0
- **Estado**: ❌ **Desactivado** (activo=0)
- **Credenciales**: misma API key Google AI
- **Notas**: Reemplazado por groq-llama como router. Se mantiene por si se necesita reactivar.

### 6. groq-llama — Llama 3.3 70B Versatile
- **Proveedor**: Groq Cloud
- **Modelo**: `llama-3.3-70b-versatile`
- **Contexto**: 128K tokens entrada / 8K salida
- **Costo**: **$0 / $0** (gratis)
- **Rate limit**: 30 RPM / 14,400 RPD
- **Nivel mínimo**: 1
- **Credenciales**: API key Groq en `ia_agentes.api_key` (slug `groq-llama`). Compartida con gpt-oss-120b.
- **Capacidades**: enrutamiento
- **Rol actual**: Router principal (`enrutamiento`, `clasificacion`). ~300ms respuesta. EXCLUSIVO para routing — no usar para respuestas largas (consume 2.5K tokens/call).
- **Notas**: Token output a 2,000+ t/s. Pero cuello de botella en entrada masiva (DDL 28K es lento).

### 7. gpt-oss-120b — GPT-OSS 120B
- **Proveedor**: Groq Cloud
- **Modelo**: `openai/gpt-oss-120b` (MoE: 5.1B activos / 116.8B total)
- **Contexto**: 131K tokens entrada / 16K salida
- **Costo**: $0.15 input / $0.60 output por millón de tokens
- **Rate limit**: 30 RPM / 1,000 RPD
- **Nivel mínimo**: 1
- **Credenciales**: misma API key Groq
- **Capacidades**: texto
- **Rol actual**: Alternativo general. 500 t/s en Groq.
- **Notas**: Reemplazo de Maverick. Razonamiento variable low/med/high.

### 8. cerebras-llama — Llama 3.1 8B
- **Proveedor**: Cerebras Cloud
- **Modelo**: `llama3.1-8b`
- **Contexto**: 8,192 tokens entrada / 8K salida
- **Costo**: $0.10 input / $0.10 output por millón de tokens
- **Rate limit**: 30 RPM / ilimitado RPD
- **Nivel mínimo**: 1
- **Credenciales**: API key Cerebras en `ia_agentes.api_key` (slug `cerebras-llama`). Obtener en cloud.cerebras.ai.
- **Capacidades**: texto
- **Rol actual**: Default para `resumen`. Router suplente 1. 2,200 t/s.
- **⚠️ Limitación crítica**: 8K contexto — **NO sirve para analisis_datos** (DDL = 28K-37K tokens).
- **Notas**: 100% éxito en benchmark de respuesta (22/22). Ideal para prompt chico.

### 9. deepseek-chat — DeepSeek Chat V3
- **Proveedor**: DeepSeek API
- **Modelo**: `deepseek-chat`
- **Contexto**: 65K tokens entrada / 8K salida
- **Costo**: $0.14 input / $0.28 output por millón de tokens
- **Nivel mínimo**: 1
- **Credenciales**: API key DeepSeek en `ia_agentes.api_key` (slug `deepseek-chat`). Compartida con deepseek-reasoner.
- **Capacidades**: sql, codigo, razonamiento
- **Rol actual**: Respaldo general. Compatible OpenAI. Muy barato.

### 10. deepseek-reasoner — DeepSeek R1 Reasoner
- **Proveedor**: DeepSeek API
- **Modelo**: `deepseek-reasoner`
- **Contexto**: 65K tokens entrada / 8K salida
- **Costo**: $0.55 input / $2.19 output por millón de tokens
- **Nivel mínimo**: 7 (solo admin — Santiago)
- **Credenciales**: misma API key DeepSeek
- **Capacidades**: sql, codigo, razonamiento
- **Rol actual**: Razonamiento profundo chain-of-thought. Solo para análisis muy complejos.

### 11. claude-sonnet — Claude Sonnet 4.6
- **Proveedor**: Anthropic API
- **Modelo**: `claude-sonnet-4-6`
- **Contexto**: 200K tokens entrada / 8K salida
- **Costo**: $3.00 input / $15.00 output por millón de tokens
- **Nivel mínimo**: 6 (premium — solo Santiago y nivel 6+)
- **Credenciales**: API key Anthropic en `ia_agentes.api_key` (slug `claude-sonnet`)
- **Capacidades**: vision, sql, codigo, razonamiento, documentos, contexto_largo
- **Rol actual**: Documentos premium. El mejor para SQL complejo y análisis profundo.
- **Notas**: El más caro pero el más capaz. 200K contexto.

---

## Agentes Locales (Ollama)

**Instalados**: 2026-03-28
**Hardware**: NVIDIA RTX 3060 — 12 GB VRAM, AMD Ryzen 5 5600X, 32 GB RAM
**Software**: Ollama v0.18.3, CUDA 13.1, driver 590.48
**Servicio**: systemd `ollama.service` (arranca con el sistema, habilitado)
**API**: `http://localhost:11434` (nativa) / `http://localhost:11434/v1` (OpenAI-compatible)
**Acceso externo**: `https://ialocal.oscomunidad.com` (Cloudflare Tunnel — pendiente CNAME en dashboard)
**Credenciales**: no requiere — campo `api_key = 'ollama'` en BD (placeholder, el campo es NOT NULL)
**Costo**: $0 total — hardware propio
**Formato API en BD**: `openai` (usa el proveedor `openai_compat.py` existente)

### Reglas de VRAM

| Combo | VRAM | ¿Cabe? |
|---|---|---|
| Cualquier 14B solo | ~9 GB | ✅ |
| llama3.2:3b + cualquier 14B | ~12 GB | ✅ Justo |
| qwen2.5:7b + llama3.2:3b | ~7.5 GB | ✅ Sobrado |
| qwen2.5:7b + cualquier 14B | ~14 GB | ❌ |
| Dos 14B | ~18 GB | ❌ |

Ollama carga/descarga modelos de VRAM automáticamente (timeout 5 min inactividad).

### 12. ollama-qwen-coder — Qwen 2.5 Coder 14B
- **Modelo Ollama**: `qwen2.5-coder:14b`
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto**: 32K tokens
- **Capacidades**: sql, codigo
- **Mejor para**: Generación de SQL, código Python/JS, debugging. Entrenado específicamente para código.
- **Terminal**: `ollama run qwen2.5-coder:14b`

### 13. ollama-qwen-14b — Qwen 2.5 14B
- **Modelo Ollama**: `qwen2.5:14b`
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto**: 32K tokens
- **Capacidades**: sql, codigo, conversacion
- **Mejor para**: Conversación general, buen español, tareas mixtas. Versión generalista.
- **Terminal**: `ollama run qwen2.5:14b`

### 14. ollama-qwen-7b — Qwen 2.5 7B
- **Modelo Ollama**: `qwen2.5:7b`
- **Tamaño disco**: 4.7 GB
- **VRAM**: ~4.7 GB
- **Contexto**: 32K tokens
- **Capacidades**: conversacion, enrutamiento
- **Mejor para**: Router versátil, tareas rápidas, respuestas cortas. Liviano.
- **Terminal**: `ollama run qwen2.5:7b`

### 15. ollama-deepseek-r1 — DeepSeek R1 14B
- **Modelo Ollama**: `deepseek-r1:14b`
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto**: 131K tokens (pero en 12GB VRAM, contexto largo degrada rendimiento)
- **Capacidades**: razonamiento, sql, codigo
- **Mejor para**: Razonamiento paso a paso (chain-of-thought). Muestra su proceso de pensamiento. Destilado del R1 completo.
- **Terminal**: `ollama run deepseek-r1:14b`

### 16. ollama-vision — Llama 3.2 Vision 11B
- **Modelo Ollama**: `llama3.2-vision:11b`
- **Tamaño disco**: 7.8 GB
- **VRAM**: ~8 GB
- **Contexto**: 32K tokens
- **Capacidades**: vision (análisis de imágenes, OCR, screenshots, gráficos)
- **Mejor para**: Entender imágenes, leer texto en fotos, interpretar gráficos, describir capturas de pantalla.
- **Terminal**: `ollama run llama3.2-vision:11b`
- **Nota**: Enviar imágenes como base64 en el campo `images[]` de la API.

### 17. ollama-llama-3b — Llama 3.2 3B
- **Modelo Ollama**: `llama3.2:3b`
- **Tamaño disco**: 2.0 GB
- **VRAM**: ~2.8 GB
- **Contexto**: 131K tokens (teórico, en la práctica limitado por VRAM)
- **Capacidades**: enrutamiento
- **Mejor para**: Router ultra liviano. Puede correr simultáneo con cualquier 14B.
- **Terminal**: `ollama run llama3.2:3b`

---

---

## Herramientas locales de IA (no LLMs)

### Chat UI Ollama — ialocal
- **Qué hace**: Interfaz web para conversar con cualquier modelo Ollama. Guarda todas las conversaciones y mensajes en BD. Sidebar con historial agrupado por fecha. Botón "Compactar" que resume mensajes viejos cuando el contexto supera el 80%, liberando espacio sin perder información.
- **Instalado**: 2026-03-28 en `ialocal/` del repo
- **Servicio systemd**: `os-ialocal.service` — activo y habilitado (arranca con el sistema)
- **Puerto**: 9500
- **URL externa**: `https://ialocal.oscomunidad.com`
- **VRAM**: 0 — es solo un proxy. El VRAM lo consume el modelo Ollama que se use.
- **BD**: `ia_local` (MariaDB local, usuario `osadmin`). Tablas: `conversaciones` + `mensajes`.
- **Ejecutar / gestionar**:
```bash
sudo systemctl status os-ialocal.service   # ver estado
sudo systemctl restart os-ialocal.service  # reiniciar
sudo journalctl -u os-ialocal.service -f   # ver logs en vivo
```
- **API interna** (para integrar desde otros servicios):
```bash
# Proxy a Ollama — formato nativo
curl http://localhost:9500/api/chat \
  -d '{"model":"qwen2.5-coder:14b","messages":[{"role":"user","content":"Hola"}],"stream":false}'

# Listar conversaciones guardadas
curl http://localhost:9500/api/conversaciones

# Crear conversación nueva
curl -X POST http://localhost:9500/api/conversaciones \
  -H "Content-Type: application/json" \
  -d '{"modelo":"qwen2.5:14b","contexto_max":32768}'
```

---

### Whisper — Transcripción de audio
- **Qué hace**: Transcribe audio a texto. Detecta idioma automáticamente. Soporta 99 idiomas. Usa GPU cuando está disponible.
- **Instalado**: 2026-03-28, `openai-whisper` v20250625 vía pip
- **Servicio systemd**: ninguno — se llama como CLI o librería Python directamente
- **VRAM**:
  - `tiny` / `base` / `small`: <1 GB — pueden correr con cualquier LLM
  - `medium` (~2 GB): **recomendado** — puede correr simultáneo con un LLM de 7B
  - `large-v3` (~5 GB): alta calidad — liberar modelos 14B antes de usar
- **Ejecutar desde terminal**:
```bash
# Transcripción básica (español)
whisper audio.mp3 --model medium --language Spanish

# Sin especificar idioma (detección automática)
whisper audio.mp3 --model medium

# Salida en formato SRT (subtítulos)
whisper audio.mp3 --model medium --output_format srt

# Formatos soportados: mp3, mp4, wav, m4a, ogg, flac, mkv, avi, mov...
```
- **Desde Python**:
```python
import whisper
modelo = whisper.load_model("medium")
resultado = modelo.transcribe("audio.mp3", language="es")
print(resultado["text"])
```
- **Ver qué modelo hay cargado en VRAM**: `nvidia-smi` (aparece como proceso python3)

---

### ComfyUI — Generación de imágenes con FLUX.1
- **Qué hace**: Genera imágenes a partir de texto (text-to-image). Interfaz web con nodos visuales. Soporta workflows complejos (img2img, inpainting, upscaling). Modelo actual: FLUX.1-schnell (generación rápida, ~4 pasos).
- **Instalado**: 2026-03-28 en `/home/osserver/ComfyUI/`
- **Servicio systemd**: `os-comfyui.service` — activo y habilitado (arranca con el sistema)
- **Puerto**: 8188
- **URL externa**: `https://comfyui.oscomunidad.com` (pendiente CNAME en Cloudflare dashboard)
- **VRAM**: ~10–11 GB al generar (carga UNet 6.4GB + T5 4.6GB + CLIP + VAE). **NO corre simultáneo con ningún LLM de 14B.**
- **⚠️ Antes de generar imágenes**: liberar modelos Ollama con `ollama stop <modelo>` (o esperar 5 min de inactividad).
- **Ejecutar / gestionar**:
```bash
sudo systemctl status os-comfyui.service   # ver estado
sudo systemctl restart os-comfyui.service  # reiniciar
sudo journalctl -u os-comfyui.service -f   # ver logs en vivo

# Ver VRAM en tiempo real
watch -n1 nvidia-smi
```
- **Uso**: Abrir `http://localhost:8188` → cargar workflow → conectar nodos UNet (GGUF), T5, CLIP, VAE, KSampler → Queue Prompt.

**Modelos FLUX.1-schnell instalados** (en `/home/osserver/ComfyUI/models/`):
| Archivo | Carpeta | Tamaño en disco | Función | VRAM |
|---|---|---|---|---|
| `flux1-schnell-Q4_K_S.gguf` | `unet/` | 6.4 GB | Modelo principal (UNet cuantizado Q4) | ~6 GB |
| `t5xxl_fp8_e4m3fn.safetensors` | `clip/` | 4.6 GB | Text encoder T5 XXL fp8 | ~4 GB |
| `clip_l.safetensors` | `clip/` | 235 MB | CLIP-L text encoder | <1 GB |
| `ae.safetensors` | `vae/` | 9.4 MB | VAE TAEF1 (compresión/decompresión latente) | <1 GB |

**Nodo custom**: `ComfyUI-GGUF` en `ComfyUI/custom_nodes/ComfyUI-GGUF/` — imprescindible para cargar `.gguf`.

- **API** (para integrar desde otros servicios):
```bash
# Encolar un prompt (requiere workflow JSON completo)
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": { ... workflow JSON ... }}'

# Ver cola actual
curl http://localhost:8188/queue

# Ver historial de generaciones
curl http://localhost:8188/history
```

---

## Cómo usar

### Desde terminal (directo a Ollama)
```bash
ollama run qwen2.5-coder:14b          # interactivo
echo "pregunta" | ollama run qwen2.5:7b  # una pregunta
ollama ps                               # qué está cargado en VRAM
ollama list                             # modelos instalados
```

### Desde el ia_service (API — cualquier agente cloud o local)
```bash
curl -s http://localhost:5100/ia/consultar -d '{
  "pregunta": "¿Cuánto vendimos ayer?",
  "agente": "ollama-qwen-coder",
  "usuario_id": "santi",
  "canal": "api",
  "empresa": "ori_sil_2"
}'
```
Si `agente` es `null`, el sistema elige automáticamente según el tipo de consulta (ver configuración en `.agent/contextos/ia_service.md`).

### Desde fuera de la red
`ialocal.oscomunidad.com` → **Chat UI web** (puerto 9500). Acceder desde el navegador.

Para usar la API desde fuera con cURL (el Chat UI proxea a Ollama con formato nativo):
```bash
curl https://ialocal.oscomunidad.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:14b","messages":[{"role":"user","content":"Hola"}],"stream":false}'
```

Para imágenes: `comfyui.oscomunidad.com` → **ComfyUI web** (puerto 8188). Requiere CNAME en Cloudflare.

### Gestión de modelos Ollama
```bash
ollama pull <modelo>          # descargar nuevo
ollama rm <modelo>            # eliminar
sudo systemctl restart ollama # reiniciar servicio
```

---

## Dónde están las credenciales

| Proveedor | Ubicación de API key |
|---|---|
| Google (Gemini, Gemma) | `ia_agentes.api_key` donde slug = `gemini-flash`. Misma key para todos los Google. |
| Groq (Llama, GPT-OSS) | `ia_agentes.api_key` donde slug = `groq-llama`. Compartida con gpt-oss-120b. |
| Cerebras | `ia_agentes.api_key` donde slug = `cerebras-llama`. |
| DeepSeek | `ia_agentes.api_key` donde slug = `deepseek-chat`. Compartida con deepseek-reasoner. |
| Anthropic (Claude) | `ia_agentes.api_key` donde slug = `claude-sonnet`. |
| Ollama (locales) | No requiere. `api_key = 'ollama'` es placeholder. |

Todas las keys están en la tabla `ia_agentes` de la BD `ia_service_os`. No hay `.env` ni archivos de configuración separados para keys de IA.

---

## Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-03-29 | FLUX.1-schnell-Q4_K_S.gguf descargado (6.4GB). ComfyUI habilitado como servicio permanente (os-comfyui.service). comfyui.oscomunidad.com agregado al túnel Cloudflare (pendiente CNAME en dashboard). |
| 2026-03-28 | Whisper instalado (openai-whisper v20250625). ComfyUI instalado en /home/osserver/ComfyUI. llama3.2-vision:11b agregado a Ollama (7.8GB). |
| 2026-03-28 | Ollama v0.18.3 instalado. 5 modelos locales (qwen-coder 14B, qwen 14B, qwen 7B, deepseek-r1 14B, llama 3B). Borrado text-generation-webui + Mistral 7B v0.1 (27 GB liberados). |
| 2026-03-20 | Benchmark 3 rondas, 105 llamadas. cerebras-llama promovido a default respuesta. |
| 2026-03-17 | gpt-oss-120b agregado (reemplazo Maverick en Groq). |
| 2026-03-16 | Configuración inicial de 11 agentes cloud. |
