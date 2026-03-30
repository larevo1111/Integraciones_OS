# Plan: ialocal multimodal — Audio, Visión e Imágenes

**Fecha**: 2026-03-30
**Estado**: ✅ Completado — 2026-03-30

## Objetivo
Agregar 3 capacidades al Chat UI (`ialocal.oscomunidad.com`):
1. **Audio → texto** (whisper-medium): botón micrófono + subir archivo → transcribe y llena input
2. **Visión** (llama3.2-vision:11b): adjuntar imagen → modelo analiza visualmente
3. **Generación de imágenes** (flux1-schnell): prompt de texto → ComfyUI genera imagen

## Decisiones de diseño
- VRAM: server para Ollama automáticamente antes de generar imagen con ComfyUI. Sin orquestador complejo.
- Audio: texto transcrito va al input para que el usuario edite antes de enviar.
- Visión: botón 📎 aparece solo cuando el modelo seleccionado es `llama3.2-vision:11b`.
- flux1-schnell aparece como opción en el dropdown de modelos. Cuando se selecciona, el flujo es distinto (POST a ComfyUI en vez de Ollama).

## Checklist

### Backend (server.js)
- [ ] `POST /api/transcribir` — recibe audio (multipart), guarda en /tmp, corre whisper subprocess, devuelve texto
- [ ] `POST /api/generar-imagen` — recibe prompt, para Ollama, manda workflow a ComfyUI, devuelve imagen base64
- [ ] Proxy `/api/chat` — ya funciona, verificar que pasa `images[]` cuando viene del frontend (visión)
- [ ] Instalar dependencia `multer` para manejar uploads de audio
- [ ] `GET /api/vram` — endpoint para saber estado VRAM (qué está cargado, cuánto libre)

### Frontend (index.html)
- [ ] Botón micrófono (🎤) en barra de input — graba con MediaRecorder, envía a /api/transcribir
- [ ] Botón adjuntar archivo de audio (📎🎵) — alterna con micrófono para subir mp3/wav
- [ ] Botón adjuntar imagen (📎) — visible solo con modelo vision, convierte a base64
- [ ] Preview de imagen adjuntada antes de enviar
- [ ] Mostrar imagen en bubble del usuario al enviar
- [ ] Enviar `images[]` en payload cuando hay imagen adjuntada
- [ ] `flux1-schnell` en dropdown de modelos (inyectado manualmente, no viene de Ollama /api/tags)
- [ ] Cuando modelo=flux1-schnell: enviar a `/api/generar-imagen` en vez de `/api/chat`
- [ ] Mostrar imagen generada en bubble con preview y botón descargar
- [ ] Indicador de estado VRAM en la UI (qué modelo está cargado)

### Gestión VRAM (server.js)
- [ ] Función `pararOllama()` — llama `ollama stop` a todos los modelos cargados
- [ ] Antes de generar imagen: parar Ollama automáticamente
- [ ] Warning en UI si se cambia de flux1-schnell a LLM y ComfyUI sigue ocupando VRAM

### Pruebas
- [ ] Grabar audio desde el browser → transcribir correctamente en español
- [ ] Subir mp3 → transcribir
- [ ] Adjuntar imagen + enviar con llama3.2-vision → respuesta visual
- [ ] Generar imagen con flux1-schnell → imagen se muestra en chat
- [ ] Cambiar de flux1-schnell a LLM → funciona sin errores

### Documentación
- [ ] Actualizar catálogo de agentes con instrucciones de uso desde ialocal
- [ ] Commit + push

## Tareas para Subagentes Claude
Ninguna — tarea secuencial, requiere ir probando cada paso.

## Tareas para Antigravity (Google Labs)
Ninguna.
