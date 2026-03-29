# Catálogo de Agentes IA — Origen Silvestre

> Referencia completa de todos los agentes disponibles en el ecosistema OS.
> **Fuente de verdad**: tabla `ia_agentes` en BD `ia_service_os`.
> **Actualizar este documento cada vez que se agregue, modifique o desactive un agente.**

---

## Resumen rápido

| # | Slug | Modelo | Ubicación | Costo | Estado |
|---|------|--------|-----------|-------|--------|
| 1 | `gemini-flash` | Gemini 2.5 Flash | Google Cloud | $0.075/$0.30 M | ✅ Activo |
| 2 | `gemini-flash-lite` | Gemini 2.5 Flash Lite | Google Cloud | $0.037/$0.15 M | ✅ Activo |
| 3 | `deepseek-chat` | DeepSeek Chat V3 | DeepSeek API | $0.14/$0.28 M | ✅ Activo |
| 4 | `deepseek-reasoner` | DeepSeek R1 Reasoner | DeepSeek API | $0.55/$2.19 M | ✅ Activo |
| 5 | `groq-llama` | Llama 3.3 70B | Groq Cloud | **$0 / $0** | ✅ Activo |
| 6 | `claude-sonnet` | Claude Sonnet 4.6 | Anthropic API | $3.00/$15.00 M | ✅ Activo |
| 7 | `gemini-image` | Gemini 2.5 Flash Image | Google Cloud | $52.00/$0 M | ✅ Activo |
| 8 | `gemma-router` | Gemma 3 27B | Google Cloud | $0 / $0 | ❌ Desactivado |
| 9 | `gemini-pro` | Gemini 2.5 Pro | Google Cloud | $1.25/$10.00 M | ✅ Activo |
| 10 | `cerebras-llama` | Llama 3.1 8B | Cerebras Cloud | $0.10/$0.10 M | ✅ Activo |
| 11 | `gpt-oss-120b` | GPT-OSS 120B | Groq Cloud | $0.15/$0.60 M | ✅ Activo |
| 12 | `ollama-qwen-coder` | Qwen 2.5 Coder 14B | **Local (GPU)** | **$0 / $0** | ✅ Activo |
| 13 | `ollama-qwen-14b` | Qwen 2.5 14B | **Local (GPU)** | **$0 / $0** | ✅ Activo |
| 14 | `ollama-qwen-7b` | Qwen 2.5 7B | **Local (GPU)** | **$0 / $0** | ✅ Activo |
| 15 | `ollama-deepseek-r1` | DeepSeek R1 14B | **Local (GPU)** | **$0 / $0** | ✅ Activo |
| 16 | `ollama-llama-3b` | Llama 3.2 3B | **Local (GPU)** | **$0 / $0** | ✅ Activo |

Costos en USD por millón de tokens (input/output).

---

## Agentes Cloud (APIs externas)

### gemini-flash
- **Modelo**: Gemini 2.5 Flash
- **Proveedor**: Google (API Generative Language)
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta`
- **Formato API**: google
- **Contexto máx**: 1,048,576 tokens entrada / 8,192 salida
- **Rate limit**: 1,000 RPM / 10,000 RPD
- **Nivel mínimo**: 1
- **Capacidades**: vision, sql, codigo, documentos, contexto_largo
- **Rol actual**: Default para `analisis_datos` y `generacion_documento`. Agente SQL principal.
- **Cuándo usarlo**: Consultas SQL complejas, documentos largos, análisis que requieran mucho contexto de entrada (DDL ~28K tokens).

### gemini-flash-lite
- **Modelo**: Gemini 2.5 Flash Lite
- **Proveedor**: Google
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta`
- **Formato API**: google
- **Contexto máx**: 1,048,576 tokens entrada / 8,192 salida
- **Rate limit**: 4,000 RPM / ilimitado RPD
- **Nivel mínimo**: 1
- **Capacidades**: vision, enrutamiento
- **Rol actual**: Default para `conversacion`, `redaccion`, `aprendizaje`, `busqueda_web`. Fallback de gemini-flash.
- **Cuándo usarlo**: Tareas de prompt chico, conversación general, redacción. Barato y rápido.

### gemini-pro
- **Modelo**: Gemini 2.5 Pro
- **Proveedor**: Google
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta`
- **Formato API**: google
- **Contexto máx**: 1,000,000 tokens entrada / 8,192 salida
- **Rate limit**: 150 RPM / 1,000 RPD
- **Nivel mínimo**: 6 (premium)
- **Capacidades**: vision, sql, codigo, razonamiento, documentos, contexto_largo
- **Rol actual**: Análisis complejos para usuarios premium.
- **Cuándo usarlo**: Cuando necesitas máxima calidad y contexto largo. Solo Santiago y usuarios nivel 6+.

### gemini-image
- **Modelo**: Gemini 2.5 Flash Image (Imagen 4 Fast Generate)
- **Proveedor**: Google
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta`
- **Formato API**: google
- **Rate limit**: 2 RPM / 70 RPD
- **Nivel mínimo**: 1
- **Capacidades**: imagen_generacion
- **Rol actual**: Generación de imágenes.

### gemma-router
- **Modelo**: Gemma 3 27B IT
- **Proveedor**: Google
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta`
- **Formato API**: google
- **Estado**: ❌ **Desactivado** (activo=0)
- **Nota**: Reemplazado por groq-llama como router principal.

### groq-llama
- **Modelo**: Llama 3.3 70B Versatile
- **Proveedor**: Groq Cloud
- **Endpoint**: `https://api.groq.com/openai/v1`
- **Formato API**: openai
- **Contexto máx**: 128,000 tokens entrada / 8,192 salida
- **Rate limit**: 30 RPM / 14,400 RPD
- **Nivel mínimo**: 1
- **Costo**: **GRATIS**
- **Capacidades**: enrutamiento
- **Rol actual**: Router principal (`enrutamiento`, `clasificacion`). Responde en ~300ms.
- **Cuándo usarlo**: Enrutamiento y clasificación. Entrada pequeña (~500 tokens), salida corta. Ultra rápido.

### gpt-oss-120b
- **Modelo**: GPT-OSS 120B (MoE 5.1B activos / 116.8B total)
- **Proveedor**: Groq Cloud
- **Endpoint**: `https://api.groq.com/openai/v1`
- **Formato API**: openai
- **Contexto máx**: 131,072 tokens entrada / 16,384 salida
- **Rate limit**: 30 RPM / 1,000 RPD
- **Nivel mínimo**: 1
- **Capacidades**: texto
- **Rol actual**: Alternativo general. 500 t/s en Groq.

### cerebras-llama
- **Modelo**: Llama 3.1 8B
- **Proveedor**: Cerebras Cloud
- **Endpoint**: `https://api.cerebras.ai/v1`
- **Formato API**: openai
- **Contexto máx**: 8,192 tokens entrada / 8,192 salida
- **Rate limit**: 30 RPM / ilimitado RPD
- **Nivel mínimo**: 1
- **Capacidades**: texto
- **Rol actual**: Default para `resumen`. Router suplente. 2,200 t/s.
- **⚠️ Limitación**: 8K tokens de contexto — **NO sirve para analisis_datos** (DDL = 28K-37K tokens).

### deepseek-chat
- **Modelo**: DeepSeek Chat V3
- **Proveedor**: DeepSeek API
- **Endpoint**: `https://api.deepseek.com`
- **Formato API**: openai
- **Contexto máx**: 65,536 tokens entrada / 8,192 salida
- **Nivel mínimo**: 1
- **Capacidades**: sql, codigo, razonamiento
- **Rol actual**: Respaldo general. Muy barato ($0.14/M).

### deepseek-reasoner
- **Modelo**: DeepSeek R1 Reasoner
- **Proveedor**: DeepSeek API
- **Endpoint**: `https://api.deepseek.com`
- **Formato API**: openai
- **Contexto máx**: 65,536 tokens entrada / 8,192 salida
- **Nivel mínimo**: 7 (solo admin)
- **Capacidades**: sql, codigo, razonamiento
- **Rol actual**: Razonamiento profundo. Solo Santiago.

### claude-sonnet
- **Modelo**: Claude Sonnet 4.6
- **Proveedor**: Anthropic API
- **Endpoint**: `https://api.anthropic.com`
- **Formato API**: anthropic
- **Contexto máx**: 200,000 tokens entrada / 8,192 salida
- **Nivel mínimo**: 6 (premium)
- **Capacidades**: vision, sql, codigo, razonamiento, documentos, contexto_largo
- **Rol actual**: Documentos premium. El mejor para SQL complejo y análisis profundo.

---

## Agentes Locales (Ollama — GPU RTX 3060 12GB)

**Infraestructura**:
- **Hardware**: NVIDIA RTX 3060 — 12 GB VRAM
- **Software**: Ollama v0.18.3, CUDA 13.1, driver 590.48
- **Servicio**: systemd `ollama.service` (arranca con el sistema)
- **API local**: `http://localhost:11434` (nativa) / `http://localhost:11434/v1` (OpenAI-compatible)
- **API externa**: `https://ollama.oscomunidad.com` (Cloudflare Tunnel)
- **Costo**: **$0 total** — corren en hardware propio
- **Gestión**: `ollama list`, `ollama ps`, `ollama pull`, `ollama rm`

**Reglas de VRAM (12 GB disponibles)**:
- Solo **un modelo de 14B** puede estar cargado a la vez (~9 GB VRAM)
- `llama3.2:3b` (2 GB) puede correr **simultáneo** con cualquier otro
- `qwen2.5:7b` (4.7 GB) + `llama3.2:3b` (2 GB) = caben juntos
- Dos modelos de 14B **NO caben** juntos
- Ollama carga/descarga modelos automáticamente según uso (5 min timeout)

### ollama-qwen-coder
- **Modelo**: Qwen 2.5 Coder 14B (Q4_K_M)
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto máx**: 32,768 tokens
- **Capacidades**: sql, codigo
- **Mejor para**: Generación de SQL, código Python/JS, debugging. Modelo entrenado específicamente para código.
- **Comando directo**: `ollama run qwen2.5-coder:14b`

### ollama-qwen-14b
- **Modelo**: Qwen 2.5 14B (Q4_K_M)
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto máx**: 32,768 tokens
- **Capacidades**: sql, codigo, conversacion
- **Mejor para**: Conversación general, buen español, tareas mixtas. Versión generalista del Qwen.
- **Comando directo**: `ollama run qwen2.5:14b`

### ollama-qwen-7b
- **Modelo**: Qwen 2.5 7B (Q4_K_M)
- **Tamaño disco**: 4.7 GB
- **VRAM**: ~4.7 GB
- **Contexto máx**: 32,768 tokens
- **Capacidades**: conversacion, enrutamiento
- **Mejor para**: Router versátil, tareas rápidas, respuestas cortas. Cabe fácil en VRAM con otro modelo.
- **Comando directo**: `ollama run qwen2.5:7b`

### ollama-deepseek-r1
- **Modelo**: DeepSeek R1 14B (Q4_K_M — destilado de DeepSeek R1)
- **Tamaño disco**: 9.0 GB
- **VRAM**: ~9 GB
- **Contexto máx**: 32,768 tokens
- **Capacidades**: razonamiento, sql, codigo
- **Mejor para**: Razonamiento paso a paso (chain-of-thought). Muestra su proceso de pensamiento.
- **Comando directo**: `ollama run deepseek-r1:14b`

### ollama-llama-3b
- **Modelo**: Llama 3.2 3B (Q4_K_M)
- **Tamaño disco**: 2.0 GB
- **VRAM**: ~2.8 GB
- **Contexto máx**: 8,192 tokens
- **Capacidades**: enrutamiento
- **Mejor para**: Router ultra liviano. Puede correr SIMULTÁNEO con cualquier modelo de 14B.
- **Comando directo**: `ollama run llama3.2:3b`

---

## Cómo usar los agentes

### Desde el ia_service (API interna)

```python
import requests

resp = requests.post('http://localhost:5100/ia/consultar', json={
    'pregunta': '¿Cuánto vendimos ayer?',
    'agente':   'ollama-qwen-coder',   # ← slug del agente
    'usuario_id': 'santi',
    'canal': 'telegram',
    'empresa': 'ori_sil_2',
})
```

Si `agente` es `None`, el sistema elige automáticamente según el tipo de consulta.

### Desde Ollama directamente (terminal)

```bash
# Interactivo
ollama run qwen2.5-coder:14b

# Una pregunta
echo "¿Qué es SQL?" | ollama run qwen2.5:7b

# API REST nativa
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:14b",
  "prompt": "SELECT top 5 productos...",
  "stream": false
}'

# API OpenAI-compatible (la que usa ia_service)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:14b",
    "messages": [{"role":"user","content":"Hola"}]
  }'
```

### Desde fuera de la red (Cloudflare Tunnel)

```bash
# Misma API pero por HTTPS público
curl https://ollama.oscomunidad.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:14b",
    "messages": [{"role":"user","content":"Hola"}]
  }'
```

### Cambiar de agente rápido

```bash
# Ver cuál está corriendo
ollama ps

# Ver todos los disponibles
ollama list

# Cambiar: solo usa otro nombre de modelo — Ollama carga automáticamente
ollama run qwen2.5:14b        # cambia a conversación
ollama run deepseek-r1:14b    # cambia a razonamiento
ollama run qwen2.5-coder:14b  # vuelve a código
```

### Gestión de modelos

```bash
# Descargar modelo nuevo
ollama pull <modelo>

# Eliminar modelo
ollama rm <modelo>

# Ver modelos instalados
ollama list

# Ver modelos corriendo (en VRAM)
ollama ps

# Parar servicio
sudo systemctl stop ollama

# Reiniciar
sudo systemctl restart ollama
```

---

## Configuración actual del ia_service (NO modificar sin aprobación)

### Asignación por tipo de consulta

| Tipo | Agente preferido | Fallback | Agente SQL |
|------|-----------------|----------|------------|
| analisis_datos | gemini-flash | gemini-flash-lite | gemini-flash |
| conversacion | gemini-flash-lite | cerebras-llama | — |
| redaccion | gemini-flash-lite | cerebras-llama | — |
| aprendizaje | gemini-flash-lite | cerebras-llama | — |
| busqueda_web | gemini-flash-lite | cerebras-llama | — |
| resumen | cerebras-llama | gemini-flash-lite | — |
| generacion_documento | gemini-flash | gemini-flash-lite | — |
| clasificacion | groq-llama | cerebras-llama | — |
| enrutamiento | groq-llama | cerebras-llama | — |

### Roles de sistema

| Rol | Agente actual |
|-----|--------------|
| Router principal | groq-llama |
| Router suplente 1 | cerebras-llama |
| Router suplente 2 | gemini-flash-lite |
| Router suplente 3 | gemini-flash |
| Resumen | cerebras-llama |
| Depurador | groq-llama |

### Prioridad de selección

```
agente del caller > conv.agente_activo > tema.agente_preferido > tipo.agente_preferido > default
```

---

## Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-03-28 | Instalación Ollama v0.18.3 + 5 modelos locales. Borrado text-generation-webui (Mistral 7B v0.1). Dominio ollama.oscomunidad.com. |
| 2026-03-20 | Benchmark 3 rondas, 105 llamadas. cerebras-llama promovido a agente respuesta default. |
| 2026-03-17 | gpt-oss-120b agregado (reemplazo de Maverick en Groq). |
| 2026-03-16 | Configuración inicial de 11 agentes cloud. |
