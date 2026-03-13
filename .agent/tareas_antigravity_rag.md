# Tareas para Antigravity — Módulo Contextos RAG en ia-admin
**Fecha:** 2026-03-13
**Prioridad:** Alta — completar antes del bot Telegram

---

## Contexto del proyecto

Estás trabajando en `ia-admin` — panel de administración del Servicio Central de IA de Origen Silvestre.
- **URL producción:** `ia.oscomunidad.com`
- **Directorio:** `/home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/`
- **Stack:** Vue 3 + Quasar + Express (Node.js)
  - Frontend: `ia-admin/app/src/`
  - API backend: `ia-admin/api/server.js` (puerto 9200)
  - BD: `ia_service_os` en MariaDB local
  - Proceso: `pm2` — reiniciar con `pm2 restart ia-admin`

---

## Schema de BD — tablas RAG (USAR EXACTAMENTE ESTE SCHEMA)

Las tablas ya existen en `ia_service_os`. El schema fue migrado el 2026-03-13.

```sql
-- TABLA PRINCIPAL DE TEMAS (reemplazó a ia_rag_colecciones que ya NO existe)
CREATE TABLE ia_temas (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  empresa         VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2',
  slug            VARCHAR(50) NOT NULL,
  nombre          VARCHAR(200) NOT NULL,
  descripcion     TEXT,
  schema_tablas   JSON,        -- tablas BD relevantes para este tema (para DDL selectivo)
  system_prompt   TEXT,        -- instrucciones base para el LLM en este tema
  agente_preferido VARCHAR(50), -- slug del agente preferido (FK ia_agentes.slug, nullable)
  activo          TINYINT(1) NOT NULL DEFAULT 1,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_empresa_slug (empresa, slug)
);

-- DOCUMENTOS (usa tema_id + empresa, NO coleccion_id)
CREATE TABLE ia_rag_documentos (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  empresa             VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2',
  tema_id             INT NOT NULL,
  nombre              VARCHAR(300) NOT NULL,
  tipo                ENUM('texto','pdf','url','manual') NOT NULL DEFAULT 'texto',
  contenido_original  LONGTEXT,
  tokens_estimados    INT DEFAULT 0,
  fragmentos_total    INT DEFAULT 0,
  activo              TINYINT(1) NOT NULL DEFAULT 1,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (tema_id) REFERENCES ia_temas(id)
);

-- FRAGMENTOS (usa tema_id + empresa)
CREATE TABLE ia_rag_fragmentos (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  empresa      VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2',
  tema_id      INT NOT NULL,
  documento_id INT NOT NULL,
  contenido    TEXT NOT NULL,
  orden        INT NOT NULL DEFAULT 0,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tema_id)      REFERENCES ia_temas(id),
  FOREIGN KEY (documento_id) REFERENCES ia_rag_documentos(id) ON DELETE CASCADE,
  FULLTEXT KEY ft_contenido (contenido)
);
```

### Temas ya seeded para ori_sil_2:
| id | slug | nombre |
|---|---|---|
| 1 | comercial | Comercial y Ventas |
| 2 | finanzas | Finanzas y Contabilidad |
| 3 | produccion | Producción y Operaciones |
| 4 | administracion | Administración y RRHH |
| 5 | marketing | Marketing y Comunicación |
| 6 | estrategia | Estrategia y Dirección |
| 7 | general | Conocimiento General |

---

## TAREA 1 — Endpoints API en server.js

Archivo: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/api/server.js`

Agrega los endpoints **ANTES** de la línea `app.get('*', ...)` (catch-all que sirve el frontend).

### Autenticación
- `GET` de lectura: solo `requireAuth` (ya existe en server.js).
- `POST`, `PUT`, `DELETE` que modifican datos: `requireAdmin` (ya existe).

### 1.1 Temas

```javascript
// GET /api/ia/rag/temas?empresa=ori_sil_2 — listar temas con estadísticas
app.get('/api/ia/rag/temas', requireAuth, async (req, res) => {
  const empresa = req.query.empresa || 'ori_sil_2'
  const [rows] = await db.execute(`
    SELECT t.*,
           COUNT(DISTINCT d.id)                      AS total_documentos,
           COALESCE(SUM(d.fragmentos_total), 0)      AS total_fragmentos,
           COALESCE(SUM(d.tokens_estimados), 0)      AS total_tokens
    FROM ia_temas t
    LEFT JOIN ia_rag_documentos d ON d.tema_id = t.id AND d.activo = 1 AND d.empresa = t.empresa
    WHERE t.empresa = ?
    GROUP BY t.id
    ORDER BY t.nombre
  `, [empresa])
  res.json({ ok: true, temas: rows })
})

// POST /api/ia/rag/temas — crear tema
// Body: { empresa, slug, nombre, descripcion, system_prompt, agente_preferido }
// Validar: slug solo minúsculas, guiones y números. Nombre obligatorio.
app.post('/api/ia/rag/temas', requireAdmin, async (req, res) => {
  const { empresa = 'ori_sil_2', slug, nombre, descripcion = '', system_prompt = '', agente_preferido = null } = req.body
  if (!slug || !/^[a-z0-9-]+$/.test(slug)) return res.status(400).json({ error: 'slug inválido (solo minúsculas, guiones y números)' })
  if (!nombre?.trim()) return res.status(400).json({ error: 'nombre es requerido' })
  try {
    const [result] = await db.execute(
      'INSERT INTO ia_temas (empresa, slug, nombre, descripcion, system_prompt, agente_preferido) VALUES (?, ?, ?, ?, ?, ?)',
      [empresa, slug, nombre.trim(), descripcion, system_prompt, agente_preferido || null]
    )
    res.json({ ok: true, id: result.insertId })
  } catch (e) {
    if (e.code === 'ER_DUP_ENTRY') return res.status(400).json({ error: 'Ya existe un tema con ese slug en esta empresa' })
    throw e
  }
})

// PUT /api/ia/rag/temas/:id — editar tema
// Body: { nombre, descripcion, system_prompt, agente_preferido, activo }
app.put('/api/ia/rag/temas/:id', requireAdmin, async (req, res) => {
  const { nombre, descripcion, system_prompt, agente_preferido, activo } = req.body
  const fields = []
  const params = []
  if (nombre !== undefined)          { fields.push('nombre = ?');           params.push(nombre) }
  if (descripcion !== undefined)     { fields.push('descripcion = ?');      params.push(descripcion) }
  if (system_prompt !== undefined)   { fields.push('system_prompt = ?');    params.push(system_prompt) }
  if (agente_preferido !== undefined){ fields.push('agente_preferido = ?'); params.push(agente_preferido || null) }
  if (activo !== undefined)          { fields.push('activo = ?');           params.push(activo ? 1 : 0) }
  if (!fields.length) return res.status(400).json({ error: 'Nada que actualizar' })
  params.push(req.params.id)
  await db.execute(`UPDATE ia_temas SET ${fields.join(', ')} WHERE id = ?`, params)
  res.json({ ok: true })
})

// DELETE /api/ia/rag/temas/:id — eliminar (solo si no tiene documentos)
app.delete('/api/ia/rag/temas/:id', requireAdmin, async (req, res) => {
  const [[{ total }]] = await db.execute('SELECT COUNT(*) AS total FROM ia_rag_documentos WHERE tema_id = ?', [req.params.id])
  if (total > 0) return res.status(400).json({ error: `No se puede eliminar: el tema tiene ${total} documento(s). Elimínalos primero.` })
  await db.execute('DELETE FROM ia_temas WHERE id = ?', [req.params.id])
  res.json({ ok: true })
})
```

### 1.2 Documentos

```javascript
// GET /api/ia/rag/temas/:id/documentos — listar documentos de un tema
// NO incluir contenido_original (demasiado pesado para listados)
app.get('/api/ia/rag/temas/:id/documentos', requireAuth, async (req, res) => {
  const [rows] = await db.execute(
    'SELECT id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at FROM ia_rag_documentos WHERE tema_id = ? ORDER BY nombre',
    [req.params.id]
  )
  res.json({ ok: true, documentos: rows })
})

// POST /api/ia/rag/temas/:id/documentos — crear documento + indexar
// Body: { nombre, tipo ('texto'|'pdf'|'url'|'manual'), contenido }
// Proceso:
//   1. Obtener empresa del tema
//   2. INSERT en ia_rag_documentos con contenido_original
//   3. Llamar Python para indexar: rag.indexar_documento(doc_id, contenido, tema_id, empresa)
//   4. Retornar { id, fragmentos_creados }
app.post('/api/ia/rag/temas/:id/documentos', requireAdmin, async (req, res) => {
  const { nombre, tipo = 'texto', contenido } = req.body
  if (!nombre?.trim()) return res.status(400).json({ error: 'nombre es requerido' })
  if (!contenido?.trim()) return res.status(400).json({ error: 'contenido es requerido' })
  const temaId = parseInt(req.params.id)

  // Obtener empresa del tema
  const [[tema]] = await db.execute('SELECT empresa FROM ia_temas WHERE id = ?', [temaId])
  if (!tema) return res.status(404).json({ error: 'Tema no encontrado' })

  // Crear documento
  const [result] = await db.execute(
    'INSERT INTO ia_rag_documentos (empresa, tema_id, nombre, tipo, contenido_original) VALUES (?, ?, ?, ?, ?)',
    [tema.empresa, temaId, nombre.trim(), tipo, contenido]
  )
  const docId = result.insertId

  // Indexar via Python (async, no bloquea)
  try {
    const fragmentos = await indexarEnPython(docId, contenido, temaId, tema.empresa)
    res.json({ ok: true, id: docId, fragmentos_creados: fragmentos })
  } catch (e) {
    res.json({ ok: true, id: docId, fragmentos_creados: 0, advertencia: 'Documento creado pero indexación falló: ' + e.message })
  }
})

// GET /api/ia/rag/documentos/:id — obtener documento con contenido_original
app.get('/api/ia/rag/documentos/:id', requireAuth, async (req, res) => {
  const [[doc]] = await db.execute('SELECT * FROM ia_rag_documentos WHERE id = ?', [req.params.id])
  if (!doc) return res.status(404).json({ error: 'Documento no encontrado' })
  res.json({ ok: true, documento: doc })
})

// PUT /api/ia/rag/documentos/:id — actualizar documento
// Si cambia contenido: re-indexar
app.put('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => {
  const { nombre, tipo, contenido, activo } = req.body
  const [[doc]] = await db.execute('SELECT * FROM ia_rag_documentos WHERE id = ?', [req.params.id])
  if (!doc) return res.status(404).json({ error: 'Documento no encontrado' })

  const fields = [], params = []
  if (nombre !== undefined) { fields.push('nombre = ?'); params.push(nombre) }
  if (tipo !== undefined)   { fields.push('tipo = ?');   params.push(tipo) }
  if (activo !== undefined) { fields.push('activo = ?'); params.push(activo ? 1 : 0) }
  if (contenido !== undefined) { fields.push('contenido_original = ?'); params.push(contenido) }

  if (fields.length) {
    params.push(req.params.id)
    await db.execute(`UPDATE ia_rag_documentos SET ${fields.join(', ')} WHERE id = ?`, params)
  }

  let fragmentos_creados = null
  if (contenido !== undefined) {
    // Re-indexar
    fragmentos_creados = await indexarEnPython(doc.id, contenido, doc.tema_id, doc.empresa)
  }

  res.json({ ok: true, fragmentos_creados })
})

// DELETE /api/ia/rag/documentos/:id — eliminar documento y sus fragmentos (CASCADE en BD)
app.delete('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => {
  await db.execute('DELETE FROM ia_rag_documentos WHERE id = ?', [req.params.id])
  res.json({ ok: true })
})
```

### 1.3 Búsqueda de prueba

```javascript
// POST /api/ia/rag/buscar — probar búsqueda (para el admin)
// Body: { pregunta, tema_id (opcional), empresa (opcional) }
app.post('/api/ia/rag/buscar', requireAuth, async (req, res) => {
  const { pregunta, tema_id, empresa = 'ori_sil_2' } = req.body
  if (!pregunta?.trim()) return res.status(400).json({ error: 'pregunta es requerida' })

  try {
    const script = `
import sys, json
sys.path.insert(0, 'scripts')
from ia_service import rag
result = rag.buscar(${JSON.stringify(pregunta)}, empresa=${JSON.stringify(empresa)}${tema_id ? `, tema_id=${parseInt(tema_id)}` : ''})
# Convertir Decimal a float para serialización JSON
def fix(o):
    import decimal
    if isinstance(o, decimal.Decimal): return float(o)
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list): return [fix(i) for i in o]
    return o
print(json.dumps({'fragmentos': fix(result)}))
`
    const { stdout } = await execAsync(`python3 -c "${script.replace(/"/g, '\\"')}"`, {
      cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
    })
    const data = JSON.parse(stdout.trim())
    res.json({ ok: true, ...data })
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  }
})
```

### Helper Python para indexar (agregar al top de server.js, cerca de los require):

```javascript
const { exec } = require('child_process')
const util = require('util')
const execAsync = util.promisify(exec)

async function indexarEnPython(docId, contenido, temaId, empresa = 'ori_sil_2') {
  const script = `
import sys, json
sys.path.insert(0, 'scripts')
from ia_service import rag
n = rag.indexar_documento(${docId}, ${JSON.stringify(contenido)}, ${temaId}, ${JSON.stringify(empresa)})
print(json.dumps({'fragmentos': n}))
`
  const { stdout } = await execAsync(`python3 -c "${script.replace(/"/g, '\\"')}"`, {
    cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
  })
  const data = JSON.parse(stdout.trim())
  return data.fragmentos
}
```

---

## TAREA 2 — Página ContextosPage.vue

Archivo a crear: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/app/src/pages/ContextosPage.vue`

### Diseño y estilo
- **OBLIGATORIO:** Seguir el mismo diseño de las otras páginas del ia-admin (AgentesPage.vue, TiposPage.vue)
- Colores: fondo `#0d1117`, texto `#e6edf3`, acentos `#58a6ff`, verde `#3fb950`, rojo `#f85149`
- Tipografía: `'Inter', sans-serif`
- Sin usar componentes de Quasar visuales — solo layout y lógica
- Misma estructura: título + subtítulo + tabla + panel lateral de edición

### Estructura de la página

**Vista principal (izquierda):**
```
[Título: "Contextos RAG"]
[Subtítulo: "Base de conocimiento para los agentes de IA"]

[Selector de tema — dropdown horizontal] (filtra por empresa = 'ori_sil_2')
  ○ comercial — Comercial y Ventas (3 docs, 12 fragmentos)
  ○ finanzas — Finanzas y Contabilidad (0 docs)
  ... etc
  ○ + Nuevo tema

[Tabla de documentos del tema seleccionado]
  Columnas: NOMBRE | TIPO | FRAGMENTOS | TOKENS EST. | ESTADO | ACCIONES
  - Estado: badge verde "activo" / gris "inactivo"
  - Acciones: botón "Ver/Editar" + botón "Eliminar"
  - Fila vacía: "No hay documentos en este tema — Agrega el primero"

[Botón "+ Agregar Documento" — en la parte superior derecha de la tabla]
```

**Panel lateral derecho (slide-in, igual que AgentesPage):**
Al hacer click en "+ Agregar Documento" o "Ver/Editar":
```
[Título: nombre del documento o "Nuevo Documento"]

Campos del formulario:
- Nombre * (text input)
- Tipo * (select: Texto | PDF | URL | Manual)
- Contenido * (textarea grande — mínimo 200px alto)
  Placeholder: "Pega aquí el texto completo del documento..."

Indicador de tokens en tiempo real:
  "~1,234 tokens estimados · ~3 fragmentos"
  (Fórmula: palabras * 1.33 para tokens; ceil(palabras / 500) para fragmentos)

Toggle: Activo ●

[Si el documento ya tiene fragmentos]:
  "Fragmentos indexados: 12 | Última indexación: 2026-03-13"
  [Botón "Re-indexar"] — fuerza nueva fragmentación (llama PUT con el mismo contenido)

[Botones]: Cancelar | Eliminar (solo en edición, rojo) | Guardar
```

**Modal "Nuevo Tema" (aparece al seleccionar "+ Nuevo tema"):**
```
Campos:
- Slug * (solo minúsculas, guiones, números — ej: "recursos-humanos")
- Nombre *
- Descripción (textarea)
- System Prompt (textarea — instrucciones base para el LLM en este tema)
- Agente preferido (select vacío — lista desde /api/ia/agentes)

[Botones]: Cancelar | Crear Tema
```

**Sección de prueba de búsqueda** (al fondo de la página):
```
[Título: "Probar búsqueda RAG"]
[Input: "Escribe una pregunta para ver qué fragmentos encontraría el sistema..."]
[Select: "Buscar en: Todos los temas | comercial | finanzas | ..."]
[Botón "Buscar"]

[Resultados: lista de fragmentos con nombre del documento y contenido]
  Cada resultado muestra: nombre_documento, tema_nombre, score (como barra de confianza), contenido
```

### Lógica Vue
```javascript
// Estado
const temas = ref([])
const temaActivo = ref(null)
const documentos = ref([]
const panelAbierto = ref(false)
const modalTema = ref(false)
const docSeleccionado = ref(null)  // null = nuevo
const formDoc = ref({ nombre: '', tipo: 'texto', contenido: '', activo: true })
const formTema = ref({ slug: '', nombre: '', descripcion: '', system_prompt: '', agente_preferido: '' })
const buscando = ref(false)
const resultadosBusqueda = ref([])
const preguntaPrueba = ref('')
const temaFiltroSearch = ref(null)

// Computed: tokens y fragmentos estimados en tiempo real
const tokensEstimados = computed(() => {
  const palabras = formDoc.value.contenido.split(/\s+/).filter(w => w).length
  return Math.round(palabras * 1.33)
})
const fragmentosEstimados = computed(() => Math.ceil(
  formDoc.value.contenido.split(/\s+/).filter(w => w).length / 500
))
```

### Llamadas a la API
Usa `import { apiFetch } from 'src/services/api'` (ya existe en el proyecto).

```javascript
// Cargar temas
const cargarTemas = async () => {
  const data = await apiFetch('/api/ia/rag/temas?empresa=ori_sil_2')
  temas.value = data.temas
  if (!temaActivo.value && data.temas.length)
    temaActivo.value = data.temas[0]
  if (temaActivo.value) cargarDocumentos()
}

// Cargar documentos del tema activo
const cargarDocumentos = async () => {
  if (!temaActivo.value) return
  const data = await apiFetch(`/api/ia/rag/temas/${temaActivo.value.id}/documentos`)
  documentos.value = data.documentos
}

// Guardar documento (crear o actualizar)
const guardarDoc = async () => {
  if (docSeleccionado.value) {
    await apiFetch(`/api/ia/rag/documentos/${docSeleccionado.value.id}`, { method: 'PUT', body: formDoc.value })
  } else {
    await apiFetch(`/api/ia/rag/temas/${temaActivo.value.id}/documentos`, { method: 'POST', body: formDoc.value })
  }
  panelAbierto.value = false
  cargarDocumentos()
}

// Eliminar documento
const eliminarDoc = async (id) => {
  await apiFetch(`/api/ia/rag/documentos/${id}`, { method: 'DELETE' })
  cargarDocumentos()
}

// Probar búsqueda
const probarBusqueda = async () => {
  buscando.value = true
  const data = await apiFetch('/api/ia/rag/buscar', {
    method: 'POST',
    body: { pregunta: preguntaPrueba.value, tema_id: temaFiltroSearch.value?.id, empresa: 'ori_sil_2' }
  })
  resultadosBusqueda.value = data.fragmentos || []
  buscando.value = false
}
```

---

## TAREA 3 — Agregar ruta y menú

### 3.1 Ruta en router/routes.js

Agregar dentro del bloque de MainLayout (que ya tiene `meta: { requiresAuth: true }`):
```javascript
{ path: '/contextos', component: () => import('pages/ContextosPage.vue') }
```

### 3.2 Ítem en AppSidebar.vue

Agregar en la sección "CONFIGURACIÓN" del menú lateral (entre Tipos y Usuarios):
```javascript
{
  label: 'Contextos',
  icon: DatabaseIcon,  // usar DatabaseIcon de lucide-vue-next
  path: '/contextos'
}
```

El AppSidebar ya tiene este patrón, solo agregar el ítem al array de nav.

---

## TAREA 4 — QA completo

Una vez implementado todo, verificar:

1. **Listar temas:** GET /api/ia/rag/temas → 7 temas con sus estadísticas
2. **Agregar documento:** POST texto de ~200 palabras en tema 'comercial' → verificar fragmentos_total > 0 en BD
3. **Búsqueda RAG:** POST /api/ia/rag/buscar con pregunta relacionada → debe retornar fragmentos con score
4. **Flujo completo:** Ir al Playground → hacer pregunta del mismo tema → verificar que la respuesta usa el conocimiento del documento
5. **Editar documento:** cambiar contenido → re-indexar → fragmentos se actualizan
6. **Toggle activo/inactivo:** desactivar documento → búsqueda ya no lo retorna
7. **Eliminar:** documento eliminado desaparece de BD con todos sus fragmentos (CASCADE)
8. **Nuevo tema:** crear uno nuevo → aparece en selector → puede agregar documentos

**Screenshots requeridos:**
- `TEST_ia_admin_rag_<fecha>.md` con resumen de todos los pasos
- Screenshots en `/home/osserver/playwright/exports/rag_*.png`

---

## Cómo reiniciar el servidor tras cambios

```bash
pm2 restart ia-admin
# Verificar:
curl -s http://localhost:9200/api/health | python3 -m json.tool
```

Para cambios en el frontend Vue:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/app
npm run build
pm2 restart ia-admin
```

## Verificar tablas BD

```bash
mysql -u osadmin -pEpist2487. ia_service_os -e "
  SELECT t.slug, t.nombre, t.empresa,
         COUNT(DISTINCT d.id) AS docs,
         COALESCE(SUM(d.fragmentos_total), 0) AS frags
  FROM ia_temas t
  LEFT JOIN ia_rag_documentos d ON d.tema_id = t.id
  GROUP BY t.id
  ORDER BY t.id;" 2>/dev/null
```

## Archivos clave para referencia

| Archivo | Para qué |
|---|---|
| `ia-admin/api/server.js` | Ver patrón de endpoints existentes (agentes, tipos) |
| `ia-admin/app/src/pages/AgentesPage.vue` | Copiar patrón de UI (tabla + panel lateral) |
| `ia-admin/app/src/services/api.js` | `apiFetch()` ya disponible |
| `ia-admin/app/src/router/routes.js` | Dónde agregar la ruta |
| `ia-admin/app/src/components/AppSidebar.vue` | Dónde agregar el ítem de menú |
| `scripts/ia_service/rag.py` | Funciones Python disponibles (indexar_documento, buscar) |

## Notas importantes

- **`ia_rag_colecciones` ya NO existe** — fue reemplazada por `ia_temas` el 2026-03-13
- Todas las consultas usan `tema_id` (no `coleccion_id`)
- Los fragmentos tienen campo `empresa` + `tema_id` (ambos)
- El enrutador de IA detecta automáticamente el `tema` según la pregunta
- `rag.indexar_documento(doc_id, contenido, tema_id, empresa)` — el argumento `empresa` es el 4to parámetro
