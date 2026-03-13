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

## Qué ya existe (NO tocar)

El backend (`scripts/ia_service/`) ya tiene implementado:
- `rag.py` — motor de fragmentación + búsqueda FULLTEXT
- `contexto.py` — mensajes recientes verbatim
- `servicio.py` — integración de 6 capas de contexto

Las tablas ya existen en `ia_service_os`:
```
ia_rag_colecciones  (id, slug, nombre, descripcion, activo, created_at, updated_at)
ia_rag_documentos   (id, coleccion_id, nombre, tipo, contenido_original, tokens_estimados, fragmentos_total, activo, created_at, updated_at)
ia_rag_fragmentos   (id, documento_id, coleccion_id, contenido, orden, created_at)
```

Ya hay una colección de ejemplo:
```sql
SELECT * FROM ia_rag_colecciones;
-- id=1, slug='negocio-os', nombre='Origen Silvestre — Conocimiento General'
```

---

## TAREA 1 — Endpoints API en server.js

Archivo: `/home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/api/server.js`

Agrega los siguientes endpoints **ANTES** de la línea `app.get('*', ...)` (catch-all que sirve el frontend).

### Autenticación
- `GET` y `POST` requieren `requireAuth` middleware (ya existe en server.js).
- `POST`, `PUT`, `DELETE` que modifican datos requieren `requireAdmin` (ya existe).
- `GET` de lectura: solo `requireAuth`.

### 1.1 Colecciones

```javascript
// GET /api/ia/rag/colecciones — listar todas con estadísticas
app.get('/api/ia/rag/colecciones', requireAuth, async (req, res) => {
  const [rows] = await db.execute(`
    SELECT c.*,
           COUNT(DISTINCT d.id)       AS total_documentos,
           COALESCE(SUM(d.fragmentos_total), 0) AS total_fragmentos,
           COALESCE(SUM(d.tokens_estimados), 0) AS total_tokens
    FROM ia_rag_colecciones c
    LEFT JOIN ia_rag_documentos d ON d.coleccion_id = c.id AND d.activo = 1
    GROUP BY c.id
    ORDER BY c.nombre
  `)
  res.json({ ok: true, colecciones: rows })
})

// POST /api/ia/rag/colecciones — crear colección
// Body: { slug, nombre, descripcion }
// Validar: slug solo minúsculas, guiones y números. Nombre obligatorio.
app.post('/api/ia/rag/colecciones', requireAdmin, async (req, res) => { ... })

// PUT /api/ia/rag/colecciones/:id — editar colección
// Body: { nombre, descripcion, activo }
app.put('/api/ia/rag/colecciones/:id', requireAdmin, async (req, res) => { ... })

// DELETE /api/ia/rag/colecciones/:id — eliminar (solo si no tiene documentos)
// Si tiene documentos: responder 400 con mensaje claro
app.delete('/api/ia/rag/colecciones/:id', requireAdmin, async (req, res) => { ... })
```

### 1.2 Documentos

```javascript
// GET /api/ia/rag/colecciones/:id/documentos — listar documentos de una colección
// Incluir: id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at
// NO incluir contenido_original (demasiado pesado para listados)
app.get('/api/ia/rag/colecciones/:id/documentos', requireAuth, async (req, res) => { ... })

// POST /api/ia/rag/colecciones/:id/documentos — crear documento + indexar
// Body: { nombre, tipo ('texto'|'pdf'|'url'|'manual'), contenido }
// Proceso:
//   1. INSERT en ia_rag_documentos con contenido_original
//   2. Llamar Python para indexar: ejecutar via child_process
//      python3 -c "import sys; sys.path.insert(0,'scripts'); from ia_service import rag; print(rag.indexar_documento(DOC_ID, CONTENIDO, COL_ID))"
//      Directorio de trabajo: /home/osserver/Proyectos_Antigravity/Integraciones_OS
//   3. Retornar { id, fragmentos_creados }
app.post('/api/ia/rag/colecciones/:id/documentos', requireAdmin, async (req, res) => { ... })

// GET /api/ia/rag/documentos/:id — obtener documento con contenido_original
app.get('/api/ia/rag/documentos/:id', requireAuth, async (req, res) => { ... })

// PUT /api/ia/rag/documentos/:id — actualizar documento (nombre, activo, o re-indexar si cambia contenido)
// Si cambia contenido: re-indexar llamando Python igual que en POST
app.put('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => { ... })

// DELETE /api/ia/rag/documentos/:id — eliminar documento y sus fragmentos (CASCADE en BD)
app.delete('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => { ... })
```

### 1.3 Búsqueda de prueba

```javascript
// POST /api/ia/rag/buscar — probar búsqueda (para el admin)
// Body: { pregunta, coleccion_id (opcional) }
// Llama Python: rag.buscar(pregunta, coleccion_id)
// Retorna los fragmentos encontrados con scores
app.post('/api/ia/rag/buscar', requireAuth, async (req, res) => { ... })
```

**Cómo llamar Python desde Node.js:**
```javascript
const { execSync } = require('child_process')
const script = `
import sys, json
sys.path.insert(0, 'scripts')
from ia_service import rag
result = rag.indexar_documento(${docId}, ${JSON.stringify(contenido)}, ${colId})
print(json.dumps({'fragmentos': result}))
`
const output = execSync(`python3 -c "${script.replace(/"/g, '\\"')}"`, {
  cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
}).toString()
const data = JSON.parse(output)
```

**IMPORTANTE:** Usa `exec` con promesa (no sync) para no bloquear el servidor:
```javascript
const { exec } = require('child_process')
const util = require('util')
const execAsync = util.promisify(exec)
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

[Selector de colección — dropdown horizontal]
  ○ negocio-os — Origen Silvestre (3 docs, 12 fragmentos)
  ○ + Nueva colección

[Tabla de documentos de la colección seleccionada]
  Columnas: NOMBRE | TIPO | FRAGMENTOS | TOKENS EST. | ESTADO | ACCIONES
  - Estado: badge verde "activo" / gris "inactivo"
  - Acciones: botón "Ver/Editar" + botón "Eliminar"
  - Fila vacía: mensaje "No hay documentos en esta colección — Agrega el primero"

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

Indicador de tokens (calculado en tiempo real mientras se escribe):
  "~1,234 tokens estimados · ~3 fragmentos"
  (Fórmula: palabras * 1.33 para tokens, dividido 500 para fragmentos)

Toggle: Activo ●

[Si el documento ya tiene fragmentos]:
  "Fragmentos indexados: 12 | Última indexación: 2026-03-13"
  [Botón "Re-indexar"] — fuerza nueva fragmentación

[Botones]: Cancelar | Eliminar (solo en edición, rojo) | Guardar
```

**Sección de prueba de búsqueda** (al fondo de la página):
```
[Título: "Probar búsqueda RAG"]
[Input: "Escribe una pregunta para ver qué fragmentos encontraría el sistema..."]
[Select: "Buscar en: Todas las colecciones | negocio-os | ..."]
[Botón "Buscar"]

[Resultados: lista de fragmentos con nombre del documento y contenido]
```

### Lógica Vue
```javascript
// Estado
const colecciones = ref([])
const coleccionActiva = ref(null)
const documentos = ref([])
const panelAbierto = ref(false)
const docSeleccionado = ref(null)  // null = nuevo
const formDoc = ref({ nombre: '', tipo: 'texto', contenido: '', activo: true })
const buscando = ref(false)
const resultadosBusqueda = ref([])
const preguntaPrueba = ref('')

// Computed: tokens y fragmentos estimados en tiempo real
const tokensEstimados = computed(() => {
  const palabras = formDoc.value.contenido.split(/\s+/).filter(w => w).length
  return Math.round(palabras * 1.33)
})
const fragmentosEstimados = computed(() => Math.ceil(tokensEstimados.value / 665))
// (665 = 500 palabras * 1.33 tokens)
```

### Llamadas a la API
Usa siempre `import { apiFetch } from 'src/services/api'` (ya existe en el proyecto).

```javascript
// Cargar colecciones
const cargarColecciones = async () => {
  const data = await api('/api/ia/rag/colecciones')
  colecciones.value = data.colecciones
  if (!coleccionActiva.value && data.colecciones.length)
    coleccionActiva.value = data.colecciones[0]
}

// Cargar documentos de la colección activa
const cargarDocumentos = async () => {
  if (!coleccionActiva.value) return
  const data = await api(`/api/ia/rag/colecciones/${coleccionActiva.value.id}/documentos`)
  documentos.value = data.documentos
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

1. **Crear colección:** POST desde UI → aparece en la lista → confirmar en BD
2. **Agregar documento:** pegar texto de ~200 palabras → guardar → verificar fragmentos_total > 0 en BD
3. **Búsqueda RAG:** usar el buscador de prueba → debe retornar fragmentos si hay match
4. **Flujo completo:** ir al Playground → hacer una pregunta relacionada con el documento subido → verificar que la respuesta usa el conocimiento del documento
5. **Editar documento:** cambiar contenido → re-indexar → fragmentos se actualizan
6. **Toggle activo/inactivo:** desactivar documento → búsqueda ya no lo retorna
7. **Eliminar:** documento eliminado desaparece de BD con todos sus fragmentos

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

## Verificar tablas BD

```bash
mysql -u osadmin -pEpist2487. ia_service_os -e "
  SELECT c.slug, c.nombre, COUNT(d.id) AS docs, SUM(d.fragmentos_total) AS frags
  FROM ia_rag_colecciones c
  LEFT JOIN ia_rag_documentos d ON d.coleccion_id = c.id
  GROUP BY c.id;" 2>/dev/null
```

## Archivos clave para referencia

| Archivo | Para qué |
|---|---|
| `ia-admin/api/server.js` | Ver patrón de endpoints existentes (agentes, tipos) |
| `ia-admin/app/src/pages/AgentesPage.vue` | Copiar patrón de UI (tabla + panel lateral) |
| `ia-admin/app/src/services/api.js` | `apiFetch()` y `api()` ya disponibles |
| `ia-admin/app/src/router/routes.js` | Dónde agregar la ruta |
| `ia-admin/app/src/components/AppSidebar.vue` | Dónde agregar el ítem de menú |
| `scripts/ia_service/rag.py` | Funciones Python disponibles |

## Preguntas frecuentes

**¿Debo compilar el frontend?**
No. El servidor en producción sirve el directorio `dist/spa/`. Para que los cambios se vean en `ia.oscomunidad.com` debes correr:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/app
npm run build
```
Y luego `pm2 restart ia-admin`.

**¿Cómo sé que el fragmentador funciona?**
```bash
python3 -c "
import sys; sys.path.insert(0, '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts')
from ia_service import rag
frags = rag.fragmentar_texto('palabra ' * 600)
print(f'Fragmentos: {len(frags)}, primero: {len(frags[0].split())} palabras')
"
```
Debe dar ~2 fragmentos de ~500 palabras.
