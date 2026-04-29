<template>
  <div class="ops-page">
    <OsDataTable
      title="Órdenes de producción"
      :columns="columnas"
      :rows="filas"
      :loading="cargando"
      @row-click="abrirOp"
    >
      <template #toolbar>
        <q-input
          v-model="qInput" dense outlined dark
          placeholder="Buscar (id u artículo)"
          clearable @clear="qInput=''; cargar()" @keyup.enter="cargar()"
          style="min-width:200px"
          input-class="text-caption"
        >
          <template #prepend><q-icon name="search" size="14px" /></template>
        </q-input>
        <q-btn
          flat dense no-caps size="sm"
          :disable="sincronizando"
          @click="sincronizarEffi"
          class="q-ml-sm"
        >
          <span class="material-icons q-mr-xs" :class="{ 'spin-ico': sincronizando }" style="font-size:14px">sync</span>
          {{ sincronizando ? 'Sincronizando…' : 'Sincronizar Effi' }}
        </q-btn>
      </template>
      <template #cell-estado="{ value }">
        <span :style="`display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:500;background:${ESTADO_COLOR[value]||'#78909C'}20;color:${ESTADO_COLOR[value]||'#78909C'}`">
          {{ value }}
        </span>
      </template>
      <template #cell-vigencia="{ value }">
        <span :style="`display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:${value==='Anulado' ? '#90909020' : '#2db14a20'};color:${value==='Anulado' ? '#909090' : '#2db14a'}`">
          {{ value }}
        </span>
      </template>
      <template #cell-fecha_de_creacion="{ value }">
        {{ fmtFechaCorta(value) }}
      </template>
      <template #cell-articulos="{ value }">
        <span class="cel-articulos" :title="value">{{ value || '—' }}</span>
      </template>
    </OsDataTable>

    <OpPanel
      v-if="panelIdOp"
      :id-op="panelIdOp"
      :usuarios="usuarios"
      :categorias="categorias"
      @cerrar="panelIdOp = null"
      @actualizada="onActualizada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import OsDataTable from 'src/components/OsDataTable.vue'
import OpPanel from 'src/components/OpPanel.vue'

const $q = useQuasar()
const auth = useAuthStore()
const route = useRoute()
const ops = ref([])
const cargando = ref(false)
const qInput = ref('')
const panelIdOp = ref(null)
const usuarios = ref([])
const categorias = ref([])
const sincronizando = ref(false)

const ESTADO_COLOR = {
  Generada:  '#7c8ea8',
  Procesada: '#ffa726',
  Validado:  '#2db14a',
  Anulada:   '#888888',
}

const columnas = computed(() => [
  { key: 'estado',            label: 'Estado',     sortable: true, visible: true, width: '110px',
    options: ['Generada','Procesada','Validado','Anulada'].map(e => ({ value: e, label: e, color: ESTADO_COLOR[e] })) },
  { key: 'id_orden',          label: 'OP',         sortable: true, visible: true, width: '90px' },
  { key: 'nombre_encargado',  label: 'Responsable',sortable: true, visible: true, width: '180px' },
  { key: 'articulos',         label: 'Artículos',  sortable: false, visible: true },
  { key: 'fecha_de_creacion', label: 'Creada',     sortable: true, visible: true, width: '130px' },
  { key: 'vigencia',          label: 'Vigencia',   sortable: true, visible: true, width: '90px',
    options: ['Vigente','Anulado'].map(v => ({ value: v, label: v })) },
])

const filas = computed(() => ops.value)

async function cargar() {
  cargando.value = true
  try {
    const params = new URLSearchParams()
    if (qInput.value) params.set('q', qInput.value)
    const url = `/api/gestion/op${params.toString() ? '?' + params.toString() : ''}`
    const data = await api(url)
    ops.value = data.ops || []
  } catch (e) { console.error('[OpTablePage]', e) }
  finally { cargando.value = false }
}

function abrirOp(row) { panelIdOp.value = row.id_orden }
function onActualizada(idOpNueva) {
  cargar()
  if (idOpNueva) panelIdOp.value = idOpNueva   // si validó, abrir la nueva
  else panelIdOp.value = null
}

function fmtFechaCorta(s) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d)) return String(s).slice(0, 16)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) +
    ' ' + d.toTimeString().slice(0, 5)
}

async function sincronizarEffi() {
  $q.dialog({
    title: 'Sincronizar OPs e inventario',
    message: 'Ejecuta export desde Effi (Playwright) + import + sync. Tarda ~2-3 min. ¿Continuar?',
    cancel: 'Cancelar',
    ok: { label: 'Sincronizar', color: 'primary' },
    persistent: false,
    dark: true
  }).onOk(_ejecutarSincronizacion)
}

async function _ejecutarSincronizacion() {
  sincronizando.value = true
  // Guardar siempre la función dismiss del notify ongoing actual para poder cerrarlo después.
  let dismissNotif = $q.notify({
    type: 'ongoing', message: 'Sincronizando OPs e inventario…',
    caption: 'Iniciando…', position: 'top', timeout: 0, group: 'sync-ops'
  })
  let okFinal = false, errMsg = null
  try {
    const resp = await fetch('/api/gestion/op/sync', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + auth.token }
    })
    if (resp.status === 409) {
      const d = await resp.json().catch(() => ({}))
      throw new Error(d.error || 'Sync ya en curso')
    }
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const blocks = buf.split('\n\n')
      buf = blocks.pop()
      for (const block of blocks) {
        if (!block.trim()) continue
        const eventLine = block.split('\n').find(l => l.startsWith('event: ')) || ''
        const dataLine = block.split('\n').find(l => l.startsWith('data: ')) || ''
        if (!dataLine) continue
        let data = null
        try { data = JSON.parse(dataLine.slice(6)) } catch {}
        if (eventLine.includes('end')) {
          okFinal = !!data?.ok
        } else if (data?.msg) {
          dismissNotif = $q.notify({
            type: 'ongoing', message: 'Sincronizando OPs e inventario…',
            caption: data.msg.slice(0, 120), position: 'top', timeout: 0, group: 'sync-ops'
          })
        }
      }
    }
  } catch (e) {
    errMsg = e.message || String(e)
  } finally {
    // Cerrar el notify "ongoing" explícitamente con la función dismiss que devuelve Quasar.
    try { dismissNotif?.() } catch {}
    sincronizando.value = false
  }
  if (okFinal) {
    $q.notify({ type: 'positive', message: '✅ OPs e inventario actualizados desde Effi', position: 'top', timeout: 4000 })
    await cargar()
  } else {
    $q.notify({ type: 'negative', message: errMsg || 'Error en la sincronización', position: 'top', timeout: 6000 })
  }
}

// Si entra con ?op_id=X en query → abrir directamente esa OP
watch(() => route.query.op_id, (id) => {
  if (id) panelIdOp.value = String(id)
}, { immediate: true })

onMounted(async () => {
  await cargar()
  // Cargar lookups en paralelo (tareas vinculadas las muestra OpPanel)
  try {
    const [u, c] = await Promise.all([
      api('/api/gestion/usuarios'),
      api('/api/gestion/categorias'),
    ])
    usuarios.value = u.usuarios || []
    categorias.value = c.categorias || []
  } catch {}
})
</script>

<style scoped>
.ops-page { padding: 0; }
.ops-page :deep(.os-table th:nth-child(4)) { min-width: 280px; }
.cel-articulos {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12px;
}
.spin-ico { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
