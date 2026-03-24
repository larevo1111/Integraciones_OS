# Plan de Mejora — IA Analítica (Bot + ia_service)

**Estado**: Aprobado por Santi — 2026-03-14
**Objetivo**: Construir el sistema bien desde el inicio — escalable, preciso, rápido y conversacional.

---

## Resumen de mejoras

| # | Mejora | Impacto | Velocidad | Complejidad | Estado |
|---|---|---|---|---|---|
| 1 | XML en system prompt | Alto — mejor parsing del modelo | Neutral | Baja | ✅ Completado 2026-03-14 |
| 2 | Embeddings en ia_ejemplos_sql | Alto — búsqueda semántica real | -100ms | Media | ✅ Completado 2026-03-14 |
| 3 | Validación resultado vacío + retry | Alto — elimina "no hay datos" falsos | +1-2s peor caso | Media | ✅ Completado 2026-03-14 |
| 4 | Arquitectura dos capas (mecánica gratis / analítica = elección usuario) | Alto — 55% más rápido, más barato, DeepSeek como default | -2.5s | Media | ✅ Completado 2026-03-14 |
| 5 | Restructurar prompt: QUÉ HACER vs QUÉ NO HACER | Medio — el modelo entiende mejor el "por qué" | Neutral | Baja | ✅ Completado 2026-03-14 |

---

## Detalle de cada mejora

---

### 1. XML en system prompt

**Qué es**: Envolver las secciones del prompt en tags XML nombrados en lugar de texto plano.

**Por qué**: Anthropic documenta que el modelo parsea las secciones con más precisión cuando están delimitadas. Mejora hasta 30% en tareas analíticas complejas (fuente: Anthropic Prompting Best Practices).

**Cómo**: Restructurar `analisis_datos.system_prompt` en la BD:

```xml
<rol>
Eres Lara, analista de negocio de Origen Silvestre...
</rol>

<precision>
Tu respuesta se construye exclusivamente con los datos que el sistema
te entrega en cada consulta. Cualquier cifra que no provenga de esos
datos será detectada como error. Si los datos están vacíos, dilo
claramente: "No encontré datos para ese período."
</precision>

<diccionario_campos>
...todo el diccionario actual...
</diccionario_campos>

<reglas_sql>
...todas las reglas SQL...
</reglas_sql>

<ejemplos>
<example>
<pregunta>ventas de hoy</pregunta>
<sql>SELECT...</sql>
</example>
...
</ejemplos>
```

**Archivos**: solo `ia_tipos_consulta.system_prompt` en la BD (script Python de update).

---

### 2. Embeddings en ia_ejemplos_sql

**Qué es**: Reemplazar búsqueda por LIKE (palabras clave) con búsqueda por similitud semántica usando vectores.

**Por qué**: LIKE falla cuando el usuario usa sinónimos o frases distintas. "¿qué producto arrasa?" no encuentra "top productos del mes" aunque sean la misma pregunta. Con embeddings, la distancia matemática entre ambas preguntas es pequeña y sí se encuentran.

**Cómo**:
- Usar `text-embedding-004` de Google (ya tenemos API key, es gratis)
- Columna nueva `embedding` TEXT en `ia_ejemplos_sql` — guarda el vector como JSON
- Al guardar un ejemplo: llamar a la API de embeddings, guardar el vector
- Al buscar: generar embedding de la pregunta nueva, calcular cosine similarity contra todos los ejemplos, devolver los 3 más cercanos
- Para nuestro volumen (máx miles de ejemplos), Python puro sin pgvector es suficiente

**Archivos**:
- `scripts/ia_service/servicio.py` — funciones `_guardar_ejemplo_sql` y `_obtener_ejemplos_dinamicos`
- BD: `ALTER TABLE ia_ejemplos_sql ADD COLUMN embedding LONGTEXT NULL`

**Escala**: funciona igual de bien con 10 ejemplos que con 100,000. Construido bien desde el inicio.

---

### 3. Validación resultado vacío + retry inteligente

**Qué es**: Cuando el SQL ejecuta sin error pero devuelve 0 filas (o un único valor NULL), reenviar al modelo con contexto del problema para que corrija el SQL.

**Por qué**: Hoy el retry solo se activa con errores de MariaDB. Si la consulta ejecuta pero devuelve vacío, el bot dice "no hay datos" — pero muchas veces es un filtro de fecha demasiado estricto o un campo mal filtrado, no que los datos no existan.

**Flujo propuesto**:
```
SQL ejecuta → 0 filas
  → Obtener la fecha máxima real de la tabla consultada
  → Reenviar al LLM: "El SQL devolvió 0 filas.
     El dato más reciente en la tabla es [fecha].
     Verifica si el filtro de fecha o estado es correcto."
  → Máximo 2 reintentos (total 3 intentos: 1 original + 2 correcciones)
  → Si sigue vacío al 3er intento: responder "No encontré datos para ese criterio"
```

**Casos que resuelve**:
- "Ventas del lunes" cuando el lunes no tuvo facturas → reformula hacia el día más reciente
- Filtros de estado mal escritos ("Pendiente" vs "Pendiente de facturar")
- Fechas futuras por error de razonamiento del modelo

**Impacto en velocidad**: +1 llamada al LLM solo cuando hay 0 filas (no siempre). En consultas normales: sin cambio.

---

### 4. Arquitectura de dos capas — Agentes mecánicos vs Agente analítico

**Qué es**: Clasificar los agentes en dos roles fijos e independientes.

**CAPA MECÁNICA** — siempre automática, el usuario nunca la configura:
- Enrutamiento (¿datos o conversación?) → Groq Llama (gratis, ~100ms)
- Generación SQL → Gemini Flash (gratis, ~300ms) — patrón sobre esquema conocido
- Retry/corrección SQL → Gemini Flash (gratis)

**CAPA ANALÍTICA** — el agente que el usuario elige en el bot:
- Interpretación de datos + respuesta conversacional
- Opciones disponibles:

| Agente | Costo (por 1M tokens) | Perfil |
|---|---|---|
| Gemini Flash | Gratis | Opción económica/rápida |
| **DeepSeek Chat V3** | **$0.14 entrada / $0.28 salida** | Mejor balance costo/calidad para uso diario |
| Gemini Pro | $1.25 / $10 | Contexto masivo, razonamiento profundo |
| Claude Sonnet | $3 / $15 | Mejor tono conversacional, mayor calidad |
| GPT-4o | $2.5 / $10 | Versatilidad general |

**Por qué DeepSeek es relevante**: muy bueno para análisis de datos y SQL complejo, precio 10x menor que Gemini Pro. Debe ser el default para usuarios no premium del bot.

**Comparación de velocidad**:
```
HOY (todo con Gemini Pro):
  enrutamiento → Gemini Flash  ~0.5s
  generar_sql  → Gemini Pro    ~1.5s
  redactar     → Gemini Pro    ~2.5s
  Total: ~4.5s

CON ARQUITECTURA DOS CAPAS:
  enrutamiento → Groq Llama    ~0.1s  (gratis)
  generar_sql  → Gemini Flash  ~0.3s  (gratis)
  redactar     → DeepSeek/Pro  ~1.5s  (según usuario)
  Total: ~2s  (55% más rápido, significativamente más barato)
```

**Cómo implementar**:
- Campo `agente_sql` en `ia_tipos_consulta` — el agente fijo de la capa mecánica
- El agente de la capa analítica sigue siendo el que selecciona el usuario (`agente_preferido`)
- Si el usuario no ha seleccionado uno → default = DeepSeek Chat (mejor ROI)

**Archivos**:
- BD: `ALTER TABLE ia_tipos_consulta ADD COLUMN agente_sql VARCHAR(50) NULL`
- `scripts/ia_service/servicio.py` — paso `generar_sql` usa `agente_sql`, paso `redactar` usa el del usuario
- Bot: actualizar menú /agente para mostrar DeepSeek como opción destacada

---

### 5. Reescribir reglas: QUÉ HACER en lugar de QUÉ NO HACER

**Qué es**: Cambiar instrucciones negativas por instrucciones afirmativas en el system prompt.

**Por qué**: Anthropic documenta que los modelos responden mejor a instrucciones de qué hacer que a prohibiciones. El modelo bajo presión tiende a ignorar el "NUNCA" pero sí sigue instrucciones positivas.

**Ejemplos**:
```
❌ Inefectivo: "NUNCA inventes datos"
✅ Efectivo: "Toda cifra que menciones debe aparecer literalmente en los
             datos que el sistema te entregó. Si no está ahí, di:
             'No tengo ese dato disponible.'"

❌ Inefectivo: "No uses tablas ASCII"
✅ Efectivo: "Presenta los resultados como texto con negritas para
             valores clave. Usa listas con — cuando haya más de 3 ítems."
```

**Archivos**: solo `ia_tipos_consulta.system_prompt` — puede hacerse junto con la mejora #1 (XML).

---

## Orden de implementación recomendado

```
SESIÓN 1 (hoy):
  [1] XML + [5] QUÉ HACER  →  mismo script de update en BD
                             →  probar en bot, comparar respuestas

SESIÓN 2:
  [2] Embeddings           →  API Google, columna en BD, funciones Python
                             →  migrar ejemplos ya guardados

SESIÓN 3:
  [3] Retry resultado vacío →  lógica en servicio.py, probar casos edge
  [4] Agente por paso      →  columna agente_sql, configurar Flash para SQL
```

---

## Tareas para Antigravity
- [ ] QA visual: comparar respuestas del bot antes/después de XML
- [ ] Verificar que embeddings se generan correctamente al guardar ejemplos
- [ ] Test de carga: simular 10 consultas seguidas y medir tiempos

---

## Referencias
- Anthropic Prompting Best Practices: XML tags + QUÉ HACER
- DAIL-SQL Paper: embeddings para selección de ejemplos (+20% accuracy)
- Amazon Nova Architecture: modelos distintos por tarea
- Defog SQL-Eval: retry con error inyectado (80% resolución en 1er reintento)
- Ver detalles: `.agent/docs/INVESTIGACION_IA_ANALITICA_2026-03-14.md`
