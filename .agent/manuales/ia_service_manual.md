# Manual del Servicio Central de IA — ia_service_os

**Versión**: 2.0 — 2026-03-14
**Scope**: Servicio de IA centralizado de Origen Silvestre. Corre en el servidor OS (puerto 5100) y sirve a TODOS los proyectos: bot de Telegram, apps, integraciones, ERP.
**Admin panel**: app separada `ia.oscomunidad.com` — ✅ Activa (puerto 9200, `os-ia-admin.service`). Vue+Quasar con 7 páginas: Dashboard, Agentes, Tipos, Logs, Playground, Usuarios, Contextos. Auth Google OAuth + JWT 2 pasos.

> **REGLA DE SEGURIDAD ABSOLUTA**: Las API keys van SOLO en la BD (`ia_agentes.api_key`) y en `scripts/.env`. NUNCA en archivos .md, código commiteado, comentarios ni mensajes de commit.

---

## Índice

1. [Filosofía del sistema — por qué importa](#filosofia)
2. [Arquitectura completa](#arquitectura)
3. [Base de datos — 8 tablas](#bd)
4. [System prompt — 6 capas](#system-prompt)
5. [Tipos de consulta](#tipos)
6. [Agentes disponibles](#agentes)
7. [Arquitectura de dos capas — mecánica vs analítica](#dos-capas)
8. [Sistema RAG — documentos de negocio](#rag)
9. [Embeddings — búsqueda semántica de ejemplos SQL](#embeddings)
10. [Retry inteligente — resultado vacío](#retry)
11. [Enrutador y requiere_sql](#enrutador)
12. [Catálogo de tablas](#catalogo)
13. [Conversaciones — contexto vivo](#conversaciones)
14. [Bot de Telegram](#telegram)
15. [Sistema de usuarios y niveles de acceso](#usuarios)
16. [Cómo agregar / configurar un agente](#agregar-agente)
17. [Monitoreo del consumo](#monitoreo)
18. [Operación diaria — comandos útiles](#operacion)
19. [Troubleshooting](#troubleshooting)
20. [Referencia: modelos y costos](#referencia)

---

## 1. Filosofía del sistema — por qué importa {#filosofia}

### El principio fundamental: enseñar a razonar, no a memorizar

**El objetivo de este sistema es construir una IA que encuentre las respuestas de forma autónoma.**

Esto significa que NO hay que llenar el sistema de reglas específicas para cada pregunta posible. Si la IA falla en una pregunta concreta y la respuesta correcta se le inyecta directamente en el prompt, la próxima vez la responderá bien — pero eso no es aprendizaje: es memorización. Y el próximo usuario que haga la misma pregunta de otra forma, volverá a fallar.

**La diferencia clave:**

| Enfoque incorrecto | Enfoque correcto |
|---|---|
| "Cuando pregunten por ventas del lunes, usar esta fórmula exacta" | Dar al modelo el contexto y las herramientas para razonar la fórmula él solo |
| Agregar una regla por cada caso edge que falla | Mejorar el contexto general para que el modelo razone mejor en todos los casos |
| Inyectar el resultado correcto de una consulta fallida | Revisar si el sistema prompt tiene la información necesaria para que el modelo llegue solo a ese resultado |
| System prompt de 10,000 palabras con casos específicos | System prompt claro, bien estructurado, con principios generales y ejemplos representativos |

### ¿Cuándo sí agregar reglas específicas?

Solo cuando representan un patrón que el modelo NO puede inferir por sí solo con el contexto disponible:
- Gotchas técnicos de la BD (ej: "id_cliente en facturas tiene prefijo 'CC '")
- Semántica de campos que no es obvia (ej: "precio_neto_total INCLUYE IVA — para sin IVA usa precio_bruto_total - descuento_total")
- Comportamientos contraintuitivos del negocio (ej: vigencia='Vigente' para consignación activa)

Esas cosas el modelo no puede deducirlas. Pero "cómo calcular ventas del lunes" sí puede razonarlo desde los patrones de fecha que ya tiene en el prompt.

### Implicación para el refinamiento del sistema

Cuando la IA falla en una consulta:
1. **Primero diagnosticar**: ¿Le falta contexto general? ¿O es un caso edge muy específico?
2. **Si le falta contexto general** → mejorar el system prompt con el principio, no el caso
3. **Si es un gotcha técnico** → sí agregar la regla, es legítimo
4. **Si es un error de razonamiento puro** → agregar un ejemplo representativo a `ia_ejemplos_sql` (no hardcodear la respuesta, sino demostrar el patrón)

---

## 2. Arquitectura completa {#arquitectura}

```
POST /ia/consultar (Flask :5100)
        ↓
  consultar() — servicio.py
        ↓
  CAPA 0: fecha + contexto dinámico
        ↓
  _enrutar() → Groq Llama (~100ms, gratis)
    devuelve: tipo, tema, requiere_sql
        ↓
  ┌─────────────────────────────────────────────────┐
  │ tipo = analisis_datos && requiere_sql = True     │
  │                                                  │
  │  agente_sql (Gemini Flash, gratis, ~300ms)       │
  │    → genera SQL con schema DDL + ejemplos        │
  │    → (retry si SQL tiene error)                  │
  │    → (retry si resultado vacío → fecha máxima)   │
  │                                                  │
  │  ejecutor_sql.py → SELECT en Hostinger           │
  │                                                  │
  │  agente analítico (elección usuario)             │
  │    → redacta respuesta con los datos             │
  └─────────────────────────────────────────────────┘
        ↓
  tipo = conversacion (requiere_sql = False)
    → RAG search en ia_rag_fragmentos
    → agente analítico redacta con contexto RAG
        ↓
  contexto.py → guarda resumen vivo (ia_conversaciones)
        ↓
  ia_logs → auditoría completa
  ia_consumo_diario → agregado diario
        ↓
  retorna: {ok, respuesta, tabla, sql, agente, tokens, costo, conversacion_id}
```

**BD local**: `ia_service_os` — 8 tablas (ver sección 3)
**Puerto**: 5100 (systemd `ia-service.service`)
**Código**: `scripts/ia_service/`

---

## 3. Base de datos — 8 tablas {#bd}

BD: `ia_service_os` en MariaDB local (servidor OS, acceso solo local).

```bash
# Conectar
mysql -u osadmin -pEpist2487. ia_service_os 2>/dev/null
```

### ia_agentes

Modelos de IA configurados. Cada fila es un agente con su provider, modelo y key.

```sql
SELECT slug, nombre, modelo_id, proveedor, activo,
       LENGTH(api_key) > 0 AS tiene_key, rate_limit_rpd, orden, nivel_minimo
FROM ia_agentes ORDER BY orden;
```

| Columna | Descripción |
|---|---|
| `slug` | Identificador único: `gemini-pro`, `groq-llama`, `deepseek-chat`, etc. |
| `nombre` | Nombre display al usuario |
| `modelo_id` | ID exacto del modelo en la API del proveedor |
| `proveedor` | `"google"`, `"openai"` (Groq/DeepSeek), `"anthropic"` |
| `api_key` | KEY del proveedor — SOLO aquí (no en código) |
| `activo` | 1 = disponible, 0 = desactivado |
| `rate_limit_rpd` | Límite diario de requests del proveedor |
| `orden` | Para fallback — si el preferido falla, se usa el siguiente en orden |
| `nivel_minimo` | Nivel de acceso mínimo de usuario (1–7) para usar este agente |

### ia_tipos_consulta

Define los flujos y system prompts por tipo de consulta.

```sql
SELECT slug, descripcion, pasos, agente_preferido, agente_sql, tema
FROM ia_tipos_consulta;
```

| Columna | Descripción |
|---|---|
| `slug` | `analisis_datos`, `redaccion`, `enrutamiento`, `conversacion`, `clasificacion`, `generacion_imagen` |
| `pasos` | JSON array — pasos del flujo: `["enrutar","generar_sql","ejecutar","redactar"]` |
| `agente_preferido` | Slug del agente para redactar respuesta |
| `agente_sql` | Slug del agente para generar SQL (capa mecánica, distinto al analítico) |
| `system_prompt` | TEXT — prompt completo con XML estructurado |
| `tema` | Campo libre para clasificar temas RAG |

### ia_conversaciones

Contexto vivo de cada conversación. Una fila por usuario+canal.

```sql
SELECT usuario_id, canal, empresa, LENGTH(resumen) AS chars_resumen,
       mensajes_count, updated_at
FROM ia_conversaciones ORDER BY updated_at DESC LIMIT 20;
```

| Columna | Descripción |
|---|---|
| `usuario_id` | ID del usuario (Telegram ID, nombre, etc.) |
| `canal` | `telegram`, `api`, `web`, etc. |
| `empresa` | Código empresa: `ori_sil_2` |
| `resumen` | TEXT — resumen comprimido del historial (máx 1,000 palabras) |
| `mensajes_recientes` | JSON — últimos 10 mensajes `[{role, content}]` |
| `mensajes_count` | Total de mensajes en la conversación |

### ia_logs

Auditoría completa — una fila por llamada a la IA.

```sql
SELECT created_at, agente_slug, tipo_consulta, ok, tokens_in, tokens_out,
       costo_usd, latencia_ms, error_msg
FROM ia_logs ORDER BY created_at DESC LIMIT 20;
```

### ia_consumo_diario

Agregado diario por agente. Se actualiza automáticamente con cada llamada.

```sql
SELECT fecha, agente_slug, llamadas, tokens_total, costo_usd, errores
FROM ia_consumo_diario ORDER BY fecha DESC, llamadas DESC LIMIT 30;
```

### ia_rag_documentos

Documentos de negocio cargados para RAG (búsqueda por contexto).

```sql
SELECT id, nombre, tema, empresa, activo, LENGTH(contenido_completo) AS chars,
       created_at
FROM ia_rag_documentos ORDER BY tema, nombre;
```

| Columna | Descripción |
|---|---|
| `nombre` | Nombre descriptivo del documento |
| `tema` | `estrategia`, `comercial`, `marketing`, `administracion` |
| `empresa` | Código empresa (`ori_sil_2`) |
| `contenido_completo` | Texto completo extraído del documento original |
| `activo` | 1 = incluido en búsquedas RAG |

### ia_rag_fragmentos

Fragmentos individuales de cada documento (para búsqueda FULLTEXT).

```sql
SELECT d.nombre AS documento, f.tema, f.posicion,
       LEFT(f.contenido, 100) AS preview, LENGTH(f.contenido) AS chars
FROM ia_rag_fragmentos f
JOIN ia_rag_documentos d ON d.id = f.documento_id
ORDER BY f.tema, f.posicion;
```

| Columna | Descripción |
|---|---|
| `documento_id` | FK a ia_rag_documentos |
| `tema` | Hereda del documento |
| `posicion` | Orden del fragmento dentro del documento |
| `contenido` | ~500 palabras de texto |
| (índice FULLTEXT sobre `contenido`) | Para búsqueda |

### ia_ejemplos_sql

Ejemplos pregunta→SQL guardados por el sistema (few-shot learning).

```sql
SELECT empresa, pregunta, LEFT(sql_generado, 80) AS sql_preview,
       embedding IS NOT NULL AS tiene_embedding, calidad, creado_en
FROM ia_ejemplos_sql ORDER BY creado_en DESC LIMIT 20;
```

| Columna | Descripción |
|---|---|
| `empresa` | Código empresa |
| `pregunta` | Pregunta en lenguaje natural |
| `sql_generado` | SQL que resolvió la pregunta |
| `resultado_muestra` | JSON muestra del resultado |
| `embedding` | LONGTEXT — vector 768 dims (JSON) para búsqueda semántica |
| `calidad` | `buena`, `mala` — para filtrar ejemplos de baja calidad |

---

## 4. System prompt — 6 capas {#system-prompt}

El system prompt que recibe el LLM se construye en 6 capas dinámicas:

```
CAPA 0 — Fecha y hora actual (siempre)
  "Fecha y hora actuales: 2026-03-14 15:30 (Sábado, 14 de marzo de 2026)"

CAPA 1 — System prompt base (desde ia_tipos_consulta)
  Para analisis_datos: XML completo con rol, precisión, catálogo tablas,
  diccionario campos, reglas SQL, ejemplos Q→SQL

CAPA 2 — RAG (solo si hay fragmentos relevantes)
  Fragmentos de documentos de negocio que coinciden con el tema de la pregunta
  "<documentos_negocio>...</documentos_negocio>"

CAPA 3 — DDL del esquema (solo para analisis_datos)
  CREATE TABLE de las tablas de Hostinger — para que el modelo vea estructura real
  "<esquema_base_datos>...</esquema_base_datos>"

CAPA 4 — Resumen de conversación (si hay contexto previo)
  El resumen comprimido del historial (máx 1,000 palabras)
  "<contexto_conversacion>...</contexto_conversacion>"

CAPA 5 — Mensajes recientes (últimos 10 mensajes)
  Los mensajes literales más recientes con sus preguntas y respuestas
```

**¿Por qué XML en CAPA 1?** Anthropic documenta que el modelo parsea las secciones con más precisión cuando están delimitadas con tags XML nombrados (+30% en tareas analíticas complejas).

**Tags XML del system prompt de analisis_datos:**
- `<rol>` — quién es Lara, cómo piensa, cómo habla
- `<precision>` — cómo construir la respuesta con los datos entregados
- `<tablas_disponibles>` — catálogo de tablas con descripciones de negocio
- `<diccionario_campos>` — campos de las tablas principales con semántica
- `<reglas_sql>` — patrones de fecha, tipos de datos, gotchas técnicos
- `<ejemplos>` — 10 pares pregunta/SQL como few-shot examples

---

## 5. Tipos de consulta {#tipos}

Cada consulta se clasifica en un tipo por el enrutador. El tipo define:
- Qué pasos se ejecutan
- Qué agente genera el SQL (capa mecánica)
- Qué agente redacta la respuesta (capa analítica)

| slug | Descripción | Pasos | agente_sql | agente_preferido |
|---|---|---|---|---|
| `analisis_datos` | Preguntas sobre datos históricos de ventas, compras, inventario, etc. | enrutar → generar_sql → ejecutar → redactar | gemini-flash | Elección del usuario |
| `conversacion` | Preguntas de estrategia, planes, metas — respuesta con RAG | enrutar → redactar (RAG) | — | gemini-flash |
| `enrutamiento` | Solo para el enrutador (no tiene steps de respuesta) | — | — | groq-llama |
| `redaccion` | Redactar texto, email, documento | redactar | — | gemini-flash-lite |
| `clasificacion` | Clasificar o etiquetar información | clasificar | — | groq-llama |
| `generacion_imagen` | Crear imagen con IA | generar_imagen | — | gemini-image |

### Cómo actualizar el system prompt de un tipo

```bash
# Editar el script y ejecutarlo
python3 scripts/ia_service/actualizar_system_prompt.py
# Esto actualiza ia_tipos_consulta.system_prompt para slug='analisis_datos'
```

Para otros tipos, actualizar directamente en BD:
```sql
UPDATE ia_tipos_consulta
SET system_prompt = '...'
WHERE slug = 'conversacion';
```

---

## 6. Agentes disponibles {#agentes}

### Estado actual (2026-03-14)

```bash
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, nombre, modelo_id, activo, LENGTH(api_key)>0 AS tiene_key,
          rate_limit_rpd, nivel_minimo, orden
   FROM ia_agentes ORDER BY orden;" 2>/dev/null
```

| slug | modelo_id | tiene_key | RPD | nivel_min | Rol principal |
|---|---|---|---|---|---|
| `gemini-pro` | gemini-2.5-pro | ✅ | 1,000 | 1 | SQL complejo + análisis |
| `gemini-flash` | gemini-2.5-flash | ✅ | 10,000 | 1 | Redacción, resumen |
| `gemini-flash-lite` | gemini-3.1-flash-lite | ✅ | 150,000 | 1 | Alto volumen |
| `gemma-router` | gemma-3-27b-it | ✅ | 14,400 | 1 | Enrutador fallback |
| `gemini-image` | gemini-2.5-flash-image | ✅ | 70 | 1 | Imágenes |
| `groq-llama` | llama-3.3-70b-versatile | ✅ | 14,400 | 1 | Enrutador principal |
| `deepseek-chat` | deepseek-chat | ✅ | — | 1 | Análisis — recomendado uso diario |
| `deepseek-reasoner` | deepseek-reasoner | ✅ | — | 7 | Razonamiento complejo (solo admin) |
| `claude-sonnet` | claude-sonnet-4-6 | ✅ | — | 1 | Documentos premium |

### Cómo obtener cada API key

**Google Gemini** (ya activo):
1. `aistudio.google.com/apikey` → Create API Key
2. Vincular billing en `console.cloud.google.com/billing`
3. Key empieza con `AIzaSy...`

**Groq** (gratis, sin tarjeta):
1. `console.groq.com` → API Keys → Create API Key
2. Key empieza con `gsk_...`

**DeepSeek** (requiere $5 de recarga):
1. `platform.deepseek.com` → API Keys → Create Key
2. Key empieza con `sk-...`

**Anthropic Claude** (requiere $5 de recarga):
1. `console.anthropic.com` → API Keys → Create Key
2. Key empieza con `sk-ant-...`

### Formato de payload por proveedor

**Google (Gemini)**:
```json
{
  "contents": [{"role": "user", "parts": [{"text": "Hola"}]}],
  "systemInstruction": {"parts": [{"text": "Eres Lara..."}]},
  "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
}
```
Diferencia OpenAI: role `"assistant"` → `"model"`, system va en `systemInstruction`.

**OpenAI-compat (Groq / DeepSeek)**:
```json
{
  "model": "llama-3.1-8b-instant",
  "messages": [
    {"role": "system", "content": "Eres un enrutador..."},
    {"role": "user", "content": "¿Cuánto vendimos?"}
  ],
  "temperature": 0.1
}
```

**Anthropic**:
```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "system": "Eres Lara...",
  "messages": [{"role": "user", "content": "¿Cuánto vendimos?"}]
}
```
Header requerido: `anthropic-version: 2023-06-01`

---

## 7. Arquitectura de dos capas — mecánica vs analítica {#dos-capas}

### Concepto

Los agentes se dividen en dos roles con propósitos distintos:

**CAPA MECÁNICA** (siempre automática, usuario no la ve ni configura):
- Enrutador: clasifica la pregunta → Groq Llama (gratis, ~100ms)
- Generación SQL: produce el SELECT → Gemini Flash (gratis, ~300ms)
- Retry SQL: si SQL falla, corrige → Gemini Flash (gratis)
- Retry vacío: si resultado = 0 filas, pide fecha máxima y reformula → Gemini Flash

**CAPA ANALÍTICA** (el agente que el usuario elige):
- Interpreta los datos y redacta la respuesta
- Por defecto: DeepSeek Chat (mejor costo/calidad para uso diario)
- El usuario puede cambiar a: Gemini Pro, Gemini Flash, Claude Sonnet

### Configuración en BD

```sql
-- Ver configuración actual
SELECT slug, agente_preferido, agente_sql
FROM ia_tipos_consulta WHERE slug = 'analisis_datos';

-- agente_sql = capa mecánica (genera SQL)
-- agente_preferido = capa analítica (redacta respuesta)
-- El campo 'agente_preferido' se sobreescribe con la elección del usuario
```

### Comparativa de velocidad

```
HOY (capa mecánica con Gemini Flash + analítica con DeepSeek):
  enrutamiento → Groq Llama    ~0.1s  (gratis)
  generar_sql  → Gemini Flash  ~0.3s  (gratis)
  redactar     → DeepSeek      ~1.5s  ($0.07/M tokens)
  Total: ~2s  (vs ~4.5s con todo en Gemini Pro)
```

### Cambiar el agente SQL (capa mecánica)

```sql
UPDATE ia_tipos_consulta
SET agente_sql = 'gemini-flash'
WHERE slug = 'analisis_datos';
-- Reiniciar servicio después
```

---

## 8. Sistema RAG — documentos de negocio {#rag}

### Qué es el RAG aquí

RAG (Retrieval-Augmented Generation) permite que la IA responda preguntas de estrategia, comercial y administración usando documentos internos de la empresa, no solo datos de la BD.

Cuando el enrutador clasifica la pregunta como `conversacion` (no SQL), el sistema busca fragmentos relevantes en `ia_rag_fragmentos` y los inyecta en la CAPA 2 del system prompt.

### Documentos cargados (estado 2026-03-14)

| Tema | Documento | Fragmentos |
|---|---|---|
| `estrategia` | Plan Estratégico Comercial 12 Meses | 5 |
| `comercial` | Presentación y Plan de Acople de Ventas | 23 |
| `marketing` | Guión de Ventas Presentación OS | 7 |
| `administracion` | Informe Sesión Estratégica Stack Tecnológico | 3 |

### Cómo cargar un documento nuevo

1. Extraer el texto del PDF/DOCX (pdfminer, python-docx, etc.)
2. Dividir en fragmentos de ~500 palabras con solapamiento
3. Insertar en `ia_rag_documentos` + `ia_rag_fragmentos`

```python
# Estructura mínima
doc = {
    'nombre': 'Plan de Marketing Q2 2026',
    'tema': 'marketing',          # estrategia | comercial | marketing | administracion
    'empresa': 'ori_sil_2',
    'contenido_completo': texto_completo,
    'activo': 1
}
# INSERT en ia_rag_documentos, luego fragmentar y INSERT en ia_rag_fragmentos
```

### Cómo funciona la búsqueda RAG

```python
# En servicio.py — función _buscar_rag()
# Busca por FULLTEXT MATCH en ia_rag_fragmentos
# Filtra por empresa y, si el enrutador detectó tema, también por tema
# Devuelve top 3 fragmentos más relevantes
SELECT f.contenido, d.nombre, f.tema
FROM ia_rag_fragmentos f
JOIN ia_rag_documentos d ON d.id = f.documento_id
WHERE d.empresa = %s AND d.activo = 1
  AND MATCH(f.contenido) AGAINST (%s IN BOOLEAN MODE)
ORDER BY relevance DESC LIMIT 3
```

### El enrutador detecta el tema

El enrutador (Groq Llama) devuelve también un campo `tema` en el JSON:
```json
{"tipo": "conversacion", "tema": "estrategia", "requiere_sql": false}
```
Este tema se usa para filtrar el RAG por categoría de documento.

---

## 9. Embeddings — búsqueda semántica de ejemplos SQL {#embeddings}

### El problema que resuelve

La tabla `ia_ejemplos_sql` guarda pares pregunta→SQL aprendidos. Antes se buscaban por LIKE (palabras clave). Si el usuario decía "¿qué producto arrasa?" no encontraba el ejemplo de "top productos del mes" aunque son la misma consulta.

Con embeddings, se calcula la distancia semántica entre preguntas en un espacio vectorial de 768 dimensiones — preguntas similares quedan cerca aunque usen palabras distintas.

### Implementación

**Modelo**: Google `text-embedding-004` (768 dims, gratis, ilimitado).
**Código**: `scripts/ia_service/embeddings.py`

```python
# Funciones principales
generar_embedding(texto)           # Llama API Google, devuelve lista 768 floats
guardar_embedding(ejemplo_id, txt) # Genera y guarda en ia_ejemplos_sql.embedding
buscar_ejemplos_semanticos(empresa, pregunta, n=3)  # Cosine similarity
migrar_embeddings_faltantes(empresa)  # Retroalimentar ejemplos sin embedding
```

### Flujo de uso

**Al guardar un ejemplo nuevo** (cuando el modelo genera un buen SQL):
```python
# En _guardar_ejemplo_sql() — el embedding se genera en background thread
threading.Thread(target=guardar_embedding, args=(id_ejemplo, pregunta)).start()
```

**Al buscar ejemplos para el prompt**:
```python
# _obtener_ejemplos_dinamicos() — primero prueba semántico, fallback a LIKE
ejemplos = buscar_ejemplos_semanticos(empresa, pregunta, n=3)
if not ejemplos:
    ejemplos = buscar_por_keywords(empresa, pregunta)  # LIKE fallback
```

### Columna en BD

```sql
ALTER TABLE ia_ejemplos_sql ADD COLUMN embedding LONGTEXT NULL;
-- El embedding se guarda como JSON: "[0.123, -0.456, ...]"
-- Con 500 ejemplos máximo en memoria — suficiente para nuestro volumen
```

---

## 10. Retry inteligente — resultado vacío {#retry}

### El problema

Antes, si el SQL ejecutaba sin error pero devolvía 0 filas, la IA respondía "no hay datos". Muchas veces era un filtro de fecha demasiado estricto o un estado mal escrito, no que los datos no existan.

### Solución: retry con contexto de fecha máxima

```
SQL ejecuta → 0 filas
  → _obtener_fecha_maxima(sql) detecta las tablas usadas
  → Consulta MAX(fecha_de_creacion) de esas tablas en Hostinger
  → Reenvía al LLM: "El SQL devolvió 0 filas.
     El dato más reciente en la tabla es [fecha].
     Verifica si el filtro es correcto."
  → Máximo 2 reintentos (total: 1 original + 2 correcciones)
  → Si sigue vacío al 3er intento: "No encontré datos para ese criterio"
```

### Casos que resuelve

- "Ventas del lunes" cuando el lunes no tuvo facturas → reformula hacia el día más reciente
- Filtros de estado mal escritos ("Pendiente" vs "Pendiente de facturar")
- Fechas futuras por error de razonamiento del modelo

**Impacto en velocidad**: solo agrega +1 LLM call cuando hay 0 filas. En consultas normales: sin cambio.

---

## 11. Enrutador y requiere_sql {#enrutador}

### Qué hace el enrutador

El enrutador es la PRIMERA llamada en cada consulta. Usa Groq Llama (ultra rápido, gratis) para clasificar la pregunta en ~100ms, antes de hacer ninguna otra llamada.

El enrutador devuelve un JSON:
```json
{
  "tipo": "analisis_datos",
  "tema": null,
  "requiere_sql": true
}
```

### El campo requiere_sql

Este campo es la optimización más importante del enrutador:

- `requiere_sql: true` → la pregunta necesita consultar la BD → flujo completo (3 llamadas LLM)
- `requiere_sql: false` → la pregunta se puede responder desde el contexto de la conversación o desde RAG → solo 1 llamada LLM

**Ejemplos de requiere_sql: false:**
- "¿Cuál es la meta de ventas anual?" (estrategia — responde con RAG)
- "¿Y cuánto fue el mes pasado?" (si ya se habló de ventas — responde desde contexto)
- "Explícame qué es el margen de utilidad" (conceptual — no necesita BD)

**Ejemplos de requiere_sql: true:**
- "¿Cuánto vendimos ayer?" (necesita datos reales de la BD)
- "Top 5 productos del mes" (necesita consultar facturas)

### Configuración del enrutador en BD

```sql
-- Ver system prompt del enrutador
SELECT system_prompt FROM ia_tipos_consulta WHERE slug = 'enrutamiento';

-- Ver agente del enrutador
SELECT agente_preferido FROM ia_tipos_consulta WHERE slug = 'enrutamiento';
-- Debe apuntar a groq-llama (cuando tenga key) o gemma-router (fallback)
```

### Distinción crítica: analisis_datos vs conversacion

El sistema distingue DOS tipos principales:
- `analisis_datos`: el dato proviene de la BD histórica de Effi (ventas, compras, inventario...)
- `conversacion`: el dato proviene de documentos de estrategia/planes/marketing (RAG)

Si el enrutador confunde los dos → o se hace una consulta SQL innecesaria, o se responde con RAG cuando debería consultar la BD. Mantener el system prompt del enrutador claro en esta distinción.

---

## 12. Catálogo de tablas {#catalogo}

El catálogo completo de tablas está en `.agent/CATALOGO_TABLAS.md`.

Dentro del system prompt de `analisis_datos`, la sección `<tablas_disponibles>` tiene las mismas descripciones en formato compacto para que el modelo las use directamente.

### Tablas más usadas — resumen rápido

| Tabla | Cuándo usarla |
|---|---|
| `resumen_ventas_facturas_mes` | Resumen mensual global — SIEMPRE preferir para análisis por mes |
| `zeffi_facturas_venta_encabezados` | Ventas del día/semana, análisis con filtros específicos |
| `zeffi_facturas_venta_detalle` | Análisis por producto/referencia/categoría |
| `zeffi_remisiones_venta_encabezados` | Mercancía entregada sin facturar |
| `zeffi_ordenes_venta_encabezados` | Consignación activa (vigencia='Vigente') |
| `zeffi_clientes` | Datos de un cliente específico |
| `zeffi_inventario` | Stock disponible, precios, costos actuales |
| `catalogo_articulos` | Grupo de producto de un artículo |
| `zeffi_notas_credito_venta_encabezados` | Devoluciones |

### Gotchas técnicos críticos de las tablas

```
1. Todos los campos numéricos en zeffi_* son TEXT → usar CAST(campo AS DECIMAL(15,2))
2. fecha_de_creacion es TEXT "YYYY-MM-DD HH:MM:SS" → usar DATE() para filtrar
3. id_cliente en facturas tiene prefijo: "CC 74084937" → JOIN usa SUBSTRING_INDEX(id_cliente,' ',-1)
4. precio_neto_total en detalle INCLUYE IVA → para sin IVA: precio_bruto_total - descuento_total
5. zeffi_clientes tiene NITs duplicados → siempre deduplicar con GROUP BY en JOINs
6. Consignación activa: SOLO filtrar por vigencia='Vigente' (no por estado_facturacion)
7. Tablas resumen_ventas_* usan campo mes en formato "YYYY-MM", no fechas completas
```

---

## 13. Conversaciones — contexto vivo {#conversaciones}

### Cómo funciona el contexto

El sistema mantiene el hilo de la conversación en `ia_conversaciones` (una fila por usuario+canal).

```
Mensaje 1: "¿Cuánto vendimos ayer?"
  → respuesta con datos de ayer

Mensaje 2: "¿Y el día anterior?"
  → el sistema sabe que hablas de ventas gracias al contexto
  → genera SQL para anteayer sin necesidad de que el usuario especifique "ventas"
```

### Estructura del contexto

| Campo | Descripción |
|---|---|
| `resumen` | Resumen comprimido de toda la conversación (máx ~1,000 palabras) |
| `mensajes_recientes` | JSON — últimos 10 mensajes literales (pregunta + respuesta) |

El resumen se actualiza automáticamente cuando los mensajes recientes superan cierto tamaño.

### Limpiar contexto de un usuario

```bash
# Desde el bot: /limpiar
# O directamente en BD:
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_conversaciones SET resumen=NULL, mensajes_recientes='[]',
   mensajes_count=0 WHERE usuario_id='TELEGRAM_ID' AND canal='telegram';" 2>/dev/null
```

---

## 14. Bot de Telegram {#telegram}

### Archivos

```
scripts/telegram_bot/
  bot.py      — handlers principales, arranca con python3 bot.py
  api_ia.py   — cliente del ia_service (POST /ia/consultar)
  db.py       — sesiones en MariaDB local (tabla ia_bot_sesiones o similar)
  tabla.py    — procesar tablas de datos para el bot
  teclado.py  — construcción de teclados reply e inline
```

### Comandos del bot

| Comando | Acción |
|---|---|
| `/start` | Bienvenida, registra sesión |
| `/ayuda` | Muestra comandos disponibles |
| `/estado` | Muestra agente activo del usuario |
| `/agente` | Menú para cambiar el agente analítico |
| `/ventas` | Shortcut: "¿Cuánto hemos vendido hoy?" |
| `/mes` | Shortcut: "¿Cuánto llevamos vendido este mes vs el mes anterior?" |
| `/limpiar` | Limpia historial de conversación |

### Agentes disponibles en el menú /agente

| Display | slug interno |
|---|---|
| 💡 DeepSeek Chat ★ recomendado | `deepseek-chat` |
| 🧠 Gemini Pro (análisis profundo) | `gemini-pro` |
| ⚡ Gemini Flash (rápido) | `gemini-flash` |
| 🤖 Claude Sonnet (premium) | `claude-sonnet` |

### Variables de entorno necesarias

En `scripts/.env`:
```
TELEGRAM_BOT_TOKEN=...
```

### Cómo arranca el bot

```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/telegram_bot
python3 bot.py
```

### Tabla con datos grandes → mini app web

Si la respuesta tiene una tabla con muchas filas, el bot muestra un botón inline que lleva a:
```
https://menu.oscomunidad.com/bot/tabla?token=TOKEN_TEMPORAL
```
Este endpoint carga la tabla completa en la app web.

---

## 15. Sistema de usuarios y niveles de acceso {#usuarios}

### Niveles (1–7)

| Nivel | Descripción |
|---|---|
| 1–2 | Usuario básico (acceso solo a agentes económicos) |
| 3–4 | Usuario estándar |
| 5–6 | Usuario avanzado |
| 7 | Admin — acceso a todos los agentes |

### Tabla ia_usuarios (en BD local)

```sql
SELECT usuario_id, nombre, nivel, canal, empresa, activo
FROM ia_usuarios ORDER BY nivel DESC;
```

### Rate limiting

El sistema tiene sliding window in-memory por usuario. Si un usuario hace demasiadas consultas seguidas, recibe error con `retry_after` (segundos a esperar).

### Asignar nivel a un usuario

```sql
INSERT INTO ia_usuarios (usuario_id, nombre, nivel, canal, empresa, activo)
VALUES ('TELEGRAM_ID', 'Santi', 7, 'telegram', 'ori_sil_2', 1)
ON DUPLICATE KEY UPDATE nivel=7;
```

---

## 16. Cómo agregar / configurar un agente {#agregar-agente}

### Paso 1 — Insertar key en BD

```bash
# Ver estado actual
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT slug, activo, LENGTH(api_key)>0 AS tiene_key FROM ia_agentes;" 2>/dev/null

# Agregar key (ejemplo para Groq)
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "UPDATE ia_agentes SET api_key='gsk_TU_KEY', activo=1 WHERE slug='groq-llama';" 2>/dev/null
```

### Paso 2 — Backup en .env

```bash
# Agregar a scripts/.env (no commiteado)
echo "GROQ_API_KEY=gsk_..." >> scripts/.env
```

### Paso 3 — Reiniciar servicio

```bash
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2)
sudo systemctl start ia-service.service
```

### Paso 4 — Verificar

```bash
curl -s http://localhost:5100/ia/agentes | python3 -m json.tool
```

### Crear un agente nuevo (no existe en BD)

```sql
INSERT INTO ia_agentes
  (slug, nombre, modelo_id, proveedor, api_key, activo, rate_limit_rpd, orden, nivel_minimo)
VALUES
  ('groq-llama-fast', 'Groq Llama Fast', 'llama-3.1-8b-instant',
   'openai', 'gsk_...', 1, 14400, 10, 1);
```

`proveedor` debe ser: `"google"`, `"openai"` (para Groq/DeepSeek), o `"anthropic"`.
La URL base del endpoint se configura en `proveedores/openai_compat.py` según el slug.

---

## 17. Monitoreo del consumo {#monitoreo}

### Endpoints del servicio

```bash
# Consumo de hoy
curl -s "http://localhost:5100/ia/consumo" | python3 -m json.tool

# Consumo de la semana
curl -s "http://localhost:5100/ia/consumo?periodo=semana" | python3 -m json.tool

# Histórico últimos 30 días
curl -s "http://localhost:5100/ia/consumo/historico" | python3 -m json.tool

# Solo para gemini-pro
curl -s "http://localhost:5100/ia/consumo?agente=gemini-pro" | python3 -m json.tool
```

### SQL directo

```bash
# Consumo hoy por agente
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT agente_slug, llamadas, tokens_total, ROUND(costo_usd,4) AS costo,
          ROUND(llamadas*100.0/a.rate_limit_rpd,1) AS pct_rpd
   FROM ia_consumo_diario c JOIN ia_agentes a ON a.slug=c.agente_slug
   WHERE fecha=CURDATE() ORDER BY llamadas DESC;" 2>/dev/null

# Errores recientes
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT created_at, agente_slug, tipo_consulta, error_msg
   FROM ia_logs WHERE ok=0 ORDER BY created_at DESC LIMIT 10;" 2>/dev/null
```

### Señales de alarma

- `pct_rpd > 90%` para gemini-pro (1,000 RPD) → cambiar temporalmente a gemini-flash
- Error 429 repetido → RPM o RPD superado → esperar 60s (RPM) o hasta 3 AM Colombia (RPD)
- `ok=0` repetido → problema con la key o el modelo

---

## 18. Operación diaria — comandos útiles {#operacion}

```bash
# Estado del servicio
sudo systemctl status ia-service.service

# Logs en tiempo real
journalctl -u ia-service.service -f

# Reiniciar (kill + start porque restart a veces se cuelga)
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2)
sudo systemctl start ia-service.service

# Health check
curl -s http://localhost:5100/ia/health

# Probar consulta de datos
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"¿Cuánto vendimos este mes?","usuario_id":"santi","canal":"api"}' \
  | python3 -m json.tool

# Probar con agente específico
curl -s -X POST http://localhost:5100/ia/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"Top 5 productos del mes","agente":"gemini-pro","usuario_id":"santi"}' \
  | python3 -m json.tool

# Ver últimas 10 consultas
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT created_at, tipo_consulta, agente_slug, ok, latencia_ms,
          LEFT(pregunta,50) AS pregunta
   FROM ia_logs ORDER BY created_at DESC LIMIT 10;" 2>/dev/null

# Ver conversaciones activas
mysql -u osadmin -pEpist2487. ia_service_os -e \
  "SELECT usuario_id, canal, mensajes_count, updated_at
   FROM ia_conversaciones ORDER BY updated_at DESC LIMIT 10;" 2>/dev/null

# Migrar embeddings faltantes en ia_ejemplos_sql
python3 -c "
import sys; sys.path.insert(0,'scripts')
from ia_service.embeddings import migrar_embeddings_faltantes
migrar_embeddings_faltantes('ori_sil_2')
"
```

---

## 19. Troubleshooting {#troubleshooting}

### Resultado vacío / "no hay datos" incorrecto

1. Revisar si la consulta fue al día/período correcto: `mysql ... "SELECT MAX(fecha_de_creacion) FROM zeffi_facturas_venta_encabezados;" 2>/dev/null`
2. El retry de resultado vacío debería haberlo manejado — revisar `ia_logs` para ver si hubo retry
3. Si el modelo eligió la tabla incorrecta → el catálogo en `<tablas_disponibles>` debería guiarlo

### El enrutador classifica mal (analisis_datos vs conversacion)

Revisar el system prompt del enrutador:
```sql
SELECT system_prompt FROM ia_tipos_consulta WHERE slug='enrutamiento';
```
La distinción clave: `analisis_datos` = datos transaccionales de BD. `conversacion` = estrategia, planes, metas.

### SQL generado con error de sintaxis

El retry automático maneja la mayoría. Si es un patrón recurrente:
1. Agregar el caso como ejemplo en `<ejemplos>` del system prompt
2. Si es un gotcha técnico (campo TEXT, JOINs especiales) → agregar a `<reglas_sql>`
3. NO agregar reglas ultra-específicas que no escalen — ver Sección 1 (Filosofía)

### Servicio no responde / timeout al reiniciar

```bash
# systemctl restart a veces se cuelga — usar kill + start
sudo kill $(sudo systemctl show -p MainPID ia-service.service | cut -d= -f2) 2>/dev/null
sleep 1
sudo systemctl start ia-service.service
sleep 2
curl -s http://localhost:5100/ia/health
```

### Key inválida / Error 401

La key fue revocada o expiró. Actualizar en BD:
```sql
UPDATE ia_agentes SET api_key='NUEVA_KEY' WHERE slug='gemini-flash';
```
Luego reiniciar el servicio.

### Rate limit Gemini (RPD agotado a las 3 AM Colombia)

```sql
-- Temporalmente cambiar agente SQL a uno con más RPD
UPDATE ia_tipos_consulta SET agente_sql='gemini-flash-lite' WHERE slug='analisis_datos';
```

---

## 20. Referencia: modelos y costos {#referencia}

### Google Gemini (Nivel de pago 1 — estado OS 2026-03-14)

| Modelo | modelo_id | RPD | Uso en OS |
|---|---|---|---|
| Gemini 2.5 Pro | `gemini-2.5-pro` | 1,000 | SQL complejo |
| Gemini 2.5 Flash | `gemini-2.5-flash` | 10,000 | Redacción |
| Gemini 2.0 Flash | `gemini-2.0-flash` | Ilimitado | Disponible |
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | 150,000 | Alto volumen |
| Gemma 3 27B | `gemma-3-27b-it` | 14,400 | Enrutador fallback |
| Imagen 4 Fast | `imagen-4.0-fast-generate-preview` | 70 | Imágenes |
| text-embedding-004 | `text-embedding-004` | Ilimitado | Embeddings |

**Reset cuotas**: 3:00 AM Colombia (medianoche Pacific Time)

### Groq (gratis)

| Modelo | modelo_id | RPD |
|---|---|---|
| Llama 3.1 8B | `llama-3.1-8b-instant` | 14,400 |
| Llama 3.3 70B | `llama-3.3-70b-versatile` | 1,000 |

### DeepSeek

| Modelo | Input | Output |
|---|---|---|
| deepseek-chat | $0.07/M | $1.10/M |
| deepseek-reasoner | $0.55/M | $2.19/M |

### Anthropic Claude

| Modelo | Input | Output |
|---|---|---|
| claude-haiku-4-5 | $0.80/M | $4.00/M |
| claude-sonnet-4-6 | $3.00/M | $15.00/M |
| claude-opus-4-6 | $15.00/M | $75.00/M |

---

*Última actualización: 2026-03-14*
