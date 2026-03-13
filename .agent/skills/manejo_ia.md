---
description: Arquitectura del Servicio Central de IA — ia_service_os (multi-proyecto)
---

# Skill: Servicio Central de IA — ia_service_os

> **ACTUALIZADO 2026-03-12**: Este documento reemplaza la versión anterior (Regla de los 3 Pasos simple).
> El servicio está implementado y operativo. Ver implementación en `scripts/ia_service/`.

## ¿Qué es ia_service_os?

Es el **servicio de IA centralizado de Origen Silvestre** — corre en el servidor OS y sirve a TODOS los proyectos de la empresa (bot de Telegram, ERP, integraciones, futuros proyectos). No es exclusivo de Integraciones_OS.

- **Puerto**: 5100 (systemd `ia-service.service`)
- **BD**: `ia_service_os` en MariaDB local
- **Código**: `scripts/ia_service/` en este repo
- **Admin panel (pendiente)**: app separada en `ia.oscomunidad.com`

## Punto de entrada único

```python
from ia_service import consultar

resultado = consultar(
    pregunta     = "¿Cuánto vendimos ayer?",
    tipo         = None,           # None = enrutador detecta automáticamente
    agente       = None,           # None = usa agente preferido del tipo
    usuario_id   = "santi",
    canal        = "telegram",     # telegram | erp | api | script
    conversacion_id = None,        # None = busca por usuario+canal
)
# resultado = {ok, conversacion_id, respuesta, formato, tabla, sql, imagen_b64, agente, tokens, costo_usd}
```

O vía HTTP desde cualquier proyecto:
```bash
POST http://localhost:5100/ia/consultar
{"pregunta": "¿Cuánto vendimos?", "usuario_id": "santi", "canal": "telegram"}
```

## Regla de los 3 Pasos (Anti-Alucinaciones) — sigue vigente

El servicio implementa esto internamente para `analisis_datos`:

1. **Generar SQL**: LLM recibe pregunta + DDL de tablas → devuelve SQL puro
2. **Ejecutar SQL**: Sistema ejecuta en Hostinger (solo SELECT, MAX 500 filas)
3. **Redactar respuesta**: LLM recibe datos reales → redacta respuesta humana

**NUNCA la IA responde con cifras de negocio inventadas.** Solo con datos reales de la BD.

## Arquitectura de 4 tablas (BD ia_service_os)

| Tabla | Propósito |
|---|---|
| `ia_agentes` | Catálogo de modelos con API key, endpoint, límites RPD/RPM, costos |
| `ia_tipos_consulta` | Reglas por tipo: pasos, system_prompt, agente_preferido, temperatura |
| `ia_conversaciones` | Contexto vivo: resumen ≤1000 palabras + agente activo por usuario/canal |
| `ia_logs` | Auditoría completa por llamada: SQL, tokens, costo, latencia, error |
| `ia_consumo_diario` | Agregado diario: llamadas, tokens, costo, % del límite RPD |

## Resumen Vivo (reemplaza historial de mensajes)

En lugar de guardar todos los mensajes, cada conversación tiene un **resumen vivo de ≤1000 palabras** que se actualiza en cada turno. El LLM extrae el resumen entre tags `[RESUMEN_CONTEXTO]...[/RESUMEN_CONTEXTO]`.

Ventaja: contexto compacto, sin límites de tokens acumulados.

## Agentes activos (marzo 2026 — Nivel Pago 1 Gemini)

| slug | modelo | RPD | Uso |
|---|---|---|---|
| `gemini-pro` | gemini-2.5-pro | 1,000 | **analisis_datos** — SQL complejo |
| `gemini-flash` | gemini-2.5-flash | 10,000 | redaccion, resumen |
| `gemini-flash-lite` | gemini-3.1-flash-lite | 150,000 | alto volumen, bot |
| `gemma-router` | gemma-3-27b-it | 14,400 | **enrutador** — clasificar intención |
| `gemini-image` | imagen-4.0-fast-generate-preview | 70 | generacion_imagen |
| `groq-llama` | llama-3.1-8b-instant | 14,400 | enrutador alternativo (pendiente key) |
| `claude-sonnet` | claude-sonnet-4-6 | — | documentos (pendiente key) |

## Enrutamiento automático

El servicio detecta el tipo de consulta automáticamente sin que el caller lo especifique.
Flujo del enrutador: `groq-llama` → `gemma-router` → `gemini-flash-lite` → `gemini-flash` (primero con key activa).
**Gemini Pro NO se usa para enrutar** — se reservan sus 1,000 RPD para análisis reales.

## Selección de modelo — cómo funciona

```
Cada modelo = una fila en ia_agentes
                    ↓
ia_tipos_consulta.agente_preferido define qué modelo usa cada tipo
  analisis_datos → gemini-pro
  redaccion      → gemini-flash
  enrutamiento   → groq-llama / gemma-router
                    ↓
Si ese agente no tiene key → fallback al primero activo con key (ORDER BY orden)
                    ↓
El caller puede forzar: agente='gemini-pro' en la llamada
```

## Monitoreo de consumo

```bash
# Ver consumo de hoy con % del límite usado
curl http://localhost:5100/ia/consumo

# Histórico 30 días
curl http://localhost:5100/ia/consumo/historico

# SQL directo
mysql ia_service_os -e "SELECT agente_slug, llamadas, costo_usd FROM ia_consumo_diario WHERE fecha=CURDATE();"
```

## Dónde van las API keys

**SOLO** en la BD (`ia_agentes.api_key`) y en `scripts/.env`.
NUNCA en código, manuales, comentarios o commits.

Para agregar una key:
```bash
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='TU_KEY', activo=1 WHERE slug='groq-llama';" 2>/dev/null
```

## Manual completo

Ver `.agent/manuales/ia_service_manual.md` — límites por modelo, endpoints, costos, troubleshooting.

## Panel de administración (pendiente — próxima prioridad)

App separada en `ia.oscomunidad.com` (Vue + Quasar, mismo design system).
Vistas planeadas: Dashboard consumo, Agentes, Tipos de consulta, Logs, Playground.
Razón app separada: ia_service_os sirve a múltiples proyectos OS — no es parte de ningún proyecto específico.
