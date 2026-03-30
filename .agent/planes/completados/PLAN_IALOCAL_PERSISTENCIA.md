# Plan: Persistencia de conversaciones + Compactar contexto — ialocal

**Fecha inicio**: 2026-03-28
**Fecha completado**: 2026-03-29
**Estado**: ✅ Completado

## Contexto
Chat UI de Ollama en `ialocal.oscomunidad.com` sin persistencia. Santi pidió:
1. Guardar conversaciones y mensajes en BD
2. Historial navegable en sidebar
3. Botón "Compactar" cuando supera el 80% del contexto del modelo

## Lo implementado

### BD `ia_local` (MariaDB local, usuario osadmin)
- Tabla `conversaciones`: id, titulo (auto-60 chars), modelo, tokens_usados, contexto_max, activa
- Tabla `mensajes`: id, conversacion_id, rol (usuario/asistente/sistema/resumen), contenido, tokens_estimados, visible

### Archivos
| Archivo | Descripción |
|---------|-------------|
| `ialocal/server.js` | Express + proxy Ollama + 8 endpoints BD + compactación |
| `ialocal/public/index.html` | Chat UI sidebar + streaming + markdown + barra contexto |
| `ialocal/package.json` | express + mysql2 |
| `systemd/os-ialocal.service` | Puerto 9500, activo y habilitado |

### Endpoints API
GET/POST/PUT/DELETE `/api/conversaciones[/:id][/titulo][/compactar]` + POST `/api/mensajes`

### Compactación
- Barra uso de contexto verde/amarillo/rojo
- >80% → botón Compactar
- Modelo resume mensajes viejos → `visible=0` → inserta `rol='resumen'`

## Estado al completar
- 3 conversaciones, 26 mensajes en BD (sistema en uso)
- `os-ialocal.service` activo y habilitado
- `ialocal.oscomunidad.com` → puerto 9500
