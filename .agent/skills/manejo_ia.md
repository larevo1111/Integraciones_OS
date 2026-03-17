---
description: Arquitectura del Servicio Central de IA — ia_service_os (multi-proyecto)
---

# Skill: Servicio Central de IA — ia_service_os

> **ACTUALIZADO 2026-03-16 (v3)**: Visión multimodal, capacidades por agente, bot de notificaciones separado.

## ¿Qué es ia_service_os?

Es el **servicio de IA centralizado de Origen Silvestre** — corre en el servidor OS y sirve a TODOS los proyectos de la empresa (bot de Telegram, ERP, integraciones, futuros proyectos). No es exclusivo de Integraciones_OS.

- **Puerto**: 5100 (systemd `ia-service.service`)
- **BD**: `ia_service_os` en MariaDB local
- **Código**: `scripts/ia_service/` en este repo
- **Admin panel**: `ia.oscomunidad.com` (activo, puerto 9200)

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
    imagen_b64   = None,           # base64 de imagen opcional (activa flujo de visión)
    imagen_mime  = "image/jpeg",   # mime de la imagen
)
# resultado = {ok, conversacion_id, respuesta, formato, tabla, sql, imagen_b64, agente, tokens, costo_usd}
```

O vía HTTP:
```bash
# Solo texto
POST http://localhost:5100/ia/consultar
{"pregunta": "¿Cuánto vendimos?", "usuario_id": "santi", "canal": "telegram"}

# Con imagen (base64)
POST http://localhost:5100/ia/consultar
{"pregunta": "confirmame esta remisión", "usuario_id": "santi", "canal": "telegram",
 "imagen_base64": "..base64..", "imagen_mime": "image/jpeg"}

# Solo imagen sin texto — el agente describe y pregunta qué hacer
POST http://localhost:5100/ia/consultar
{"pregunta": "", "usuario_id": "santi", "canal": "telegram", "imagen_base64": "..base64.."}
```

## Flujo con imagen (visión multimodal)

```
Foto + texto opcional
      ↓
[Visión — agente con capacidad 'vision'] → extrae texto estructurado
      ↓                                    (usa google.agente_con_capacidad('vision'))
¿Imagen en blanco?
  SÍ → responde directo sin SQL
  NO → inyecta texto extraído como contexto en la pregunta
      ↓
[Enrutador — Groq] → ¿requiere SQL?
      ↓
[Flujo normal] → SQL → ejecutar → redactar
```

**Telegram**: el bot acepta fotos directamente (caption opcional). `handle_foto()` en `bot.py` descarga la foto, convierte a base64, llama a `consultar()` con `imagen_b64`.

## Capacidades por agente (ia_agentes.capacidades JSON)

| slug | vision | sql | razonamiento | imagen_gen | enrutamiento |
|---|---|---|---|---|---|
| gemini-flash | ✅ | ✅ | — | — | — |
| gemini-pro | ✅ | ✅ | ✅ | — | — |
| claude-sonnet | ✅ | ✅ | ✅ | — | — |
| gemini-flash-lite | ✅ | — | — | — | ✅ |
| deepseek-chat | — | ✅ | ✅ | — | — |
| groq-llama | — | — | — | — | ✅ |
| gemini-image | — | — | — | ✅ | — |

El servicio usa `google.agente_con_capacidad('vision')` para elegir dinámicamente — sin hardcoding. Agregar capacidad a un agente = solo update en BD.

## Bots de Telegram — dos bots separados

| Bot | Token .env | Uso |
|---|---|---|
| `@os_integraciones_bot` | `TELEGRAM_BOT_TOKEN` | Asistente IA conversacional |
| `@os_notificaciones_sys_bot` | `TELEGRAM_NOTIF_BOT_TOKEN` | Alertas del pipeline (solo notificaciones) |

El orquestador usa `TELEGRAM_NOTIF_BOT_TOKEN` (fallback a `TELEGRAM_BOT_TOKEN` si no existe).

## Regla de los 3 Pasos (Anti-Alucinaciones) — sigue vigente

El servicio implementa esto internamente para `analisis_datos`:

1. **Generar SQL**: LLM recibe pregunta + DDL de tablas → devuelve SQL puro
2. **Ejecutar SQL**: Sistema ejecuta en Hostinger (solo SELECT, MAX 500 filas)
3. **Redactar respuesta**: LLM recibe datos reales → redacta respuesta humana

**NUNCA la IA responde con cifras de negocio inventadas.** Solo con datos reales de la BD.

## Arquitectura de BD (ia_service_os) — tablas principales

| Tabla | Propósito |
|---|---|
| `ia_agentes` | Catálogo de modelos con API key, endpoint, límites RPD/RPM, costos |
| `ia_tipos_consulta` | Flujos por tipo: pasos, system_prompt, agente_preferido, agente_sql |
| `ia_temas` | Áreas de negocio (7 temas): agente_preferido + schema_tablas por tema |
| `ia_conversaciones` | Contexto vivo: resumen ≤600 palabras + mensajes_recientes por usuario/canal |
| `ia_logs` | Auditoría completa por llamada: SQL, tokens, costo, latencia, error |
| `ia_consumo_diario` | Agregado diario: llamadas, tokens, costo, % del límite RPD |
| `ia_ejemplos_sql` | Pares pregunta→SQL (few-shot learning + embeddings semánticos) |
| `ia_rag_fragmentos` | Chunks de documentos de negocio con FULLTEXT index |
| `ia_usuarios` | Usuarios con nivel de acceso (1–7) |

## Resumen Vivo — CÓMO funciona (cambio 2026-03-15)

El contexto de conversación tiene:
- `resumen` ≤600 palabras — historia comprimida de la conversación
- `mensajes_recientes` — últimos 10 mensajes literales

**⚠️ Cambio importante**: el resumen ya NO lo genera el agente principal (gemini-pro, etc.). Lo genera **Groq Llama** en llamada separada DESPUÉS de responder al usuario:
```
respuesta entregada → _generar_resumen_groq() → Groq genera resumen 600 palabras → guarda en BD
```
Esto elimina la penalización de latencia que tenía DeepSeek (era de 80+ segundos por generar 1,000 palabras de resumen).

## Enrutador — cambios críticos (2026-03-15)

### Qué devuelve
```json
{"tipo": "analisis_datos", "tema": "comercial", "requiere_sql": true}
```

### Usa contexto COMPLETO de la conversación
El enrutador recibe `resumen_anterior + historial_reciente` — NO solo la pregunta actual. Esto permite que "¿Y el mes pasado?" sea correctamente interpretado como consulta de ventas (porque el historial dice que hablaban de ventas).

### System prompt reescrito (2026-03-15)
Cubre todos los módulos del negocio:
- **analisis_datos**: ventas, compras, producción, inventario, remisiones, cotizaciones, consignación, cartera, devoluciones, rankings, comparaciones
- **conversacion**: estrategia, planes, preguntas sin datos de BD
- **Regla**: en caso de duda → `analisis_datos` (mejor SQL innecesario que ignorar dato real)

### schema_tablas por tema — crítico
El campo `ia_temas.schema_tablas` controla el DDL que recibe el agente SQL. **Si la tabla no está aquí, el modelo no puede consultarla.**

| Tema | Tablas incluidas |
|---|---|
| `comercial` | Todos los ventas, remisiones, cotizaciones, ordenes_venta, notas_credito, clientes, inventario |
| `finanzas` | Compras (facturas, ordenes, remisiones), proveedores, cuentas por cobrar/pagar, cartera |
| `produccion` | zeffi_produccion_encabezados, zeffi_articulos_producidos, zeffi_materiales, zeffi_costos_produccion |
| `estrategia` | resumen_ventas_facturas_mes, resumen_ventas_remisiones_mes |
| `general` | Principales: facturas_venta_enc, resumen_ventas_mes, clientes, inventario, crm_contactos |

**Error corregido**: `produccion` tenía `zeffi_articulos` (inexistente). Ahora tiene las tablas de producción reales.

## Agentes activos (2026-03-16)

| slug | modelo | RPD | Rol | Costo input/M |
|---|---|---|---|---|
| `gemini-flash` | gemini-2.5-flash | 10,000 | **Principal** — todos los flujos (analisis, conversacion, redaccion) | $0.075 |
| `deepseek-chat` | deepseek-chat | — | **Respaldo** de gemini-flash en todos los flujos | $0.14 |
| `groq-llama` | llama-3.3-70b-versatile | 14,400 | Enrutador principal + generador de resúmenes | gratis |
| `gemini-flash-lite` | gemini-2.5-flash-lite | 150,000 | Enrutador fallback (si groq falla) | $0.0375 |
| `gemini-pro` | gemini-2.5-pro | 1,000 | SQL complejo (reservado — $1.25/M, 20s latencia) | $1.25 |
| `gemini-image` | gemini-2.5-flash-image | 70 | Generación de imágenes | $52.00 |
| `claude-sonnet` | claude-sonnet-4-6 | — | Documentos premium | $3.00 |
| `deepseek-reasoner` | deepseek-reasoner | — | Razonamiento complejo (nivel_minimo=7) | $0.55 |
| `gemma-router` | gemma-3-27b-it | — | ❌ **Desactivado** — eliminado de todos los chains | gratis |

**Regla de enrutamiento**: `groq-llama` → `gemini-flash-lite` → `gemini-flash` (primero disponible).
**Groq y flash-lite NUNCA son agentes finales** — solo enrutan y generan resúmenes.

## Catálogo de tablas — dónde vive y cómo actualizar

El LLM solo conoce lo que está en el `system_prompt` de `analisis_datos` (ia_tipos_consulta):
- `<tablas_disponibles>` — catálogo con descripciones de negocio
- `<diccionario_campos>` — campos clave con semántica
- `<reglas_sql>` — gotchas técnicos de la BD
- `<ejemplos>` — few-shot SQL

Para actualizar cuando se agrega una tabla nueva:
1. Actualizar `.agent/CATALOGO_TABLAS.md`
2. Editar `ia_tipos_consulta.system_prompt` donde slug='analisis_datos'
3. Reiniciar servicio: `sudo systemctl restart ia-service.service`

## Sistema de Fallback (implementado 2026-03-16)

Campo `agente_fallback` en `ia_tipos_consulta` e `ia_temas`. Si el agente principal falla (cualquier error):
1. Se intenta con `agente_fallback` (deepseek-chat por defecto)
2. Se envía notificación Telegram via `@os_notificaciones_sys_bot`

**Notificaciones automáticas** (función `_notificar()` + `_verificar_gasto_y_notificar()` en servicio.py):
- Cuando fallback se activa: tipo de error, agente que falló, agente de respaldo
- Gasto diario > $2 USD (anti-spam 1h por empresa)
- Gasto por hora > $0.5 USD (anti-spam 1h por empresa)

## Enrutamiento automático

Flujo del enrutador: `groq-llama` → `gemini-flash-lite` → `gemini-flash` (primero disponible con key).
**Groq y flash-lite NUNCA son agentes finales** — solo enrutan y generan resúmenes.

## Monitoreo de consumo

```bash
# Ver consumo de hoy con % del límite usado
curl http://localhost:5100/ia/consumo

# Histórico 30 días
curl http://localhost:5100/ia/consumo/historico

# SQL directo
python3 -c "
import pymysql
conn = pymysql.connect(host='localhost', user='osadmin', password='Epist2487.', db='ia_service_os')
cur = conn.cursor()
cur.execute('SELECT agente_slug, llamadas, tokens_total, costo_usd FROM ia_consumo_diario WHERE fecha=CURDATE()')
for row in cur.fetchall(): print(row)
"
```

## Dónde van las API keys

**SOLO** en la BD (`ia_agentes.api_key`) y en `scripts/.env`.
NUNCA en código, manuales, comentarios o commits.

## Manual completo

Ver `.agent/manuales/ia_service_manual.md` — límites por modelo, endpoints, costos, troubleshooting.
