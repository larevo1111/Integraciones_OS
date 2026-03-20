<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Roles de Agentes</h1>
      <p class="page-subtitle">Qué agente desempeña cada función del sistema — enrutador, analítico, resumen, visión</p>
    </div>

    <div class="page-content">

      <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>

      <div v-else>

        <!-- SECCIÓN: ENRUTAMIENTO -->
        <div class="rol-seccion">
          <div class="rol-seccion-titulo">
            <GitBranchIcon :size="15" class="rol-seccion-icono" />
            Enrutamiento
          </div>
          <p class="rol-seccion-desc">Antes de responder cada pregunta, el sistema la "clasifica" — decide si es análisis de datos, conversación, búsqueda web, etc. Esto lo hace el enrutador. Debe ser <strong>muy rápido y barato</strong> porque se ejecuta en cada consulta.</p>

          <div class="roles-grid">
            <RolCard
              v-for="rol in rolesRouter"
              :key="rol.clave"
              :rol="rol"
              :agentes="agentes"
              @guardar="guardarRol"
            />
          </div>
        </div>

        <!-- SECCIÓN: ANALÍTICO POR TIPO -->
        <div class="rol-seccion">
          <div class="rol-seccion-titulo">
            <BrainIcon :size="15" class="rol-seccion-icono" />
            Agente analítico — por tipo de consulta
          </div>
          <p class="rol-seccion-desc">El agente que <strong>redacta la respuesta final</strong> al usuario. Uno por cada tipo de consulta. También define el agente SQL (el que genera la consulta a la BD) y el suplente en caso de fallo.</p>

          <table class="os-table" style="margin-top:8px">
            <thead>
              <tr>
                <th>Tipo de consulta</th>
                <th>Principal</th>
                <th>Suplente</th>
                <th>Agente SQL</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tipos" :key="t.slug">
                <td>
                  <div style="font-weight:500">{{ t.nombre }}</div>
                  <div style="font-size:11px;color:var(--text-tertiary)">{{ t.slug }}</div>
                </td>
                <td>
                  <AgenteBadge :slug="t.agente_preferido" :agentes="agentes" />
                </td>
                <td>
                  <AgenteBadge :slug="t.agente_fallback" :agentes="agentes" />
                </td>
                <td>
                  <AgenteBadge :slug="t.agente_sql" :agentes="agentes" vacio="— (mismo)" />
                </td>
              </tr>
            </tbody>
          </table>
          <div style="font-size:12px;color:var(--text-tertiary);margin-top:8px">
            Para cambiar estos valores, ir a
            <router-link to="/tipos" style="color:var(--accent)">Tipos de consulta</router-link>
          </div>
        </div>

        <!-- SECCIÓN: AUXILIARES -->
        <div class="rol-seccion">
          <div class="rol-seccion-titulo">
            <ZapIcon :size="15" class="rol-seccion-icono" />
            Agentes auxiliares
          </div>
          <p class="rol-seccion-desc">Se ejecutan en background o en pasos internos. Deben ser <strong>rápidos y baratos</strong> — no los ve el usuario directamente.</p>

          <div class="roles-grid">
            <RolCard
              v-for="rol in rolesAuxiliares"
              :key="rol.clave"
              :rol="rol"
              :agentes="agentes"
              @guardar="guardarRol"
            />
          </div>
        </div>

        <!-- SECCIÓN: VISIÓN -->
        <div class="rol-seccion">
          <div class="rol-seccion-titulo">
            <EyeIcon :size="15" class="rol-seccion-icono" />
            Visión e Imágenes
          </div>
          <p class="rol-seccion-desc">El agente de visión se selecciona automáticamente — cualquier agente que tenga <code>capacidades.vision = true</code>. El agente de generación de imágenes se configura en "Tipos de consulta" → generacion_imagen.</p>

          <div class="roles-grid">
            <div
              v-for="ag in agentesConVision"
              :key="ag.slug"
              class="rol-card rol-card-info"
            >
              <div class="rol-card-nombre">{{ ag.nombre }}</div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">
                <span v-for="cap in capacidadesActivas(ag)" :key="cap" class="badge badge-neutral" style="font-size:10px">{{ cap }}</span>
              </div>
              <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px">Selección automática por capacidad</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineProps, defineEmits } from 'vue'
import { apiFetch } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import { GitBranchIcon, BrainIcon, ZapIcon, EyeIcon } from 'lucide-vue-next'

// ── Datos ──────────────────────────────────────────────────────────
const agentes  = ref([])
const config   = ref({})
const tipos    = ref([])
const cargando = ref(true)

const COSTO = {
  'gemini-pro':        { nivel: 'alto',   label: 'Costoso (~$3.50/1M tok)', color: 'error' },
  'claude-sonnet':     { nivel: 'alto',   label: 'Costoso (~$3/1M tok)',    color: 'error' },
  'deepseek-reasoner': { nivel: 'alto',   label: 'Costoso + muy lento',     color: 'error' },
  'deepseek-chat':     { nivel: 'medio',  label: 'Costo moderado',          color: 'warning' },
  'gpt-oss-120b':      { nivel: 'medio',  label: 'Costo moderado',          color: 'warning' },
  'gemini-flash':      { nivel: 'bajo',   label: 'Barato',                  color: 'success' },
  'gemini-flash-lite': { nivel: 'gratis', label: 'Gratis (150k RPD)',       color: 'success' },
  'groq-llama':        { nivel: 'gratis', label: 'Gratis (Groq)',           color: 'success' },
  'cerebras-llama':    { nivel: 'gratis', label: 'Gratis (Cerebras)',       color: 'success' },
  'gemma-router':      { nivel: 'gratis', label: 'Gratis',                  color: 'success' },
  'gemini-image':      { nivel: 'medio',  label: 'Costo por imagen',        color: 'warning' },
}

const VELOCIDAD = {
  'gemini-pro':        { label: 'Lento (~20s)',  color: 'error' },
  'claude-sonnet':     { label: 'Medio (~5s)',   color: 'warning' },
  'deepseek-reasoner': { label: 'Muy lento',     color: 'error' },
  'deepseek-chat':     { label: 'Lento (~18s)',  color: 'warning' },
  'gpt-oss-120b':      { label: 'Rápido',        color: 'success' },
  'gemini-flash':      { label: 'Rápido (~3s)',  color: 'success' },
  'gemini-flash-lite': { label: 'Muy rápido',    color: 'success' },
  'groq-llama':        { label: 'Muy rápido',    color: 'success' },
  'cerebras-llama':    { label: 'Ultrarrápido',  color: 'success' },
  'gemma-router':      { label: 'Rápido',        color: 'success' },
  'gemini-image':      { label: 'Medio',         color: 'warning' },
}

const rolesRouter = computed(() => [
  {
    clave: 'rol_router_principal',
    nombre: 'Router principal',
    descripcion: 'Clasifica cada pregunta antes de responder. Se ejecuta en TODAS las consultas.',
    recomendado: 'Rápido y gratis: groq-llama, cerebras-llama, gemini-flash-lite',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner', 'deepseek-chat'],
    advertencia: 'Este rol se ejecuta en cada consulta — usar un agente costoso o lento lo haría prohibitivo.',
    valor: config.value['rol_router_principal'] || '',
  },
  {
    clave: 'rol_router_suplente_1',
    nombre: 'Router suplente 1',
    descripcion: 'Se activa si el router principal falla o supera su límite de llamadas.',
    recomendado: 'cerebras-llama, gemini-flash-lite, gemma-router',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner'],
    advertencia: 'Los suplentes del router también se ejecutan frecuentemente cuando el principal está saturado.',
    valor: config.value['rol_router_suplente_1'] || '',
  },
  {
    clave: 'rol_router_suplente_2',
    nombre: 'Router suplente 2',
    descripcion: 'Tercer intento si los dos anteriores fallan.',
    recomendado: 'gemini-flash-lite, gemini-flash',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner'],
    advertencia: 'Suplente de último recurso — preferir modelos rápidos.',
    valor: config.value['rol_router_suplente_2'] || '',
  },
  {
    clave: 'rol_router_suplente_3',
    nombre: 'Router suplente 3',
    descripcion: 'Último intento antes de usar clasificación por defecto.',
    recomendado: 'gemini-flash',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner'],
    advertencia: 'Si este también falla, el sistema asume tipo "conversacion" como fallback.',
    valor: config.value['rol_router_suplente_3'] || '',
  },
])

const rolesAuxiliares = computed(() => [
  {
    clave: 'rol_resumen_agente',
    nombre: 'Resumen de conversación',
    descripcion: 'Tras cada respuesta, comprime el historial de conversación en un resumen de máx. 600 palabras. Se ejecuta en background.',
    recomendado: 'groq-llama, cerebras-llama (gratis y rápidos)',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner'],
    advertencia: 'El resumen se genera tras cada mensaje — con un agente caro el costo se multiplica por número de turnos.',
    valor: config.value['rol_resumen_agente'] || '',
  },
  {
    clave: 'rol_depurador_agente',
    nombre: 'Depurador de lógica de negocio',
    descripcion: 'Cuando el bot aprende algo nuevo, consolida y comprime toda la lógica de negocio para eliminar redundancias. Corre en background.',
    recomendado: 'groq-llama, cerebras-llama, gemini-flash-lite',
    advertencia_slugs: ['gemini-pro', 'claude-sonnet', 'deepseek-reasoner'],
    advertencia: 'Solo se ejecuta al aprender algo nuevo, no en cada consulta. Un modelo más capaz da mejor compresión.',
    valor: config.value['rol_depurador_agente'] || '',
  },
])

const agentesConVision = computed(() =>
  agentes.value.filter(a => {
    try { return JSON.parse(a.capacidades || '{}').vision } catch { return false }
  })
)

function capacidadesActivas(ag) {
  try {
    const caps = JSON.parse(ag.capacidades || '{}')
    return Object.entries(caps).filter(([, v]) => v === true).map(([k]) => k)
  } catch { return [] }
}

async function cargar() {
  cargando.value = true
  try {
    const [resAg, resCfg, resTipos] = await Promise.all([
      apiFetch('/api/ia/agentes-admin').then(r => r.json()),
      apiFetch('/api/ia/config').then(r => r.json()),
      apiFetch('/api/ia/tipos-admin').then(r => r.json()),
    ])
    agentes.value = resAg
    config.value = Object.fromEntries((resCfg.config || []).map(c => [c.clave, c.valor]))
    tipos.value = resTipos.filter(t => t.slug !== 'enrutamiento')
  } catch { }
  cargando.value = false
}

async function guardarRol(clave, valor) {
  await apiFetch(`/api/ia/config/${clave}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ valor })
  })
  config.value[clave] = valor
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => cargar())
onMounted(cargar)
</script>

<script>
// Componente interno RolCard
import { defineComponent, ref, computed, watch } from 'vue'
import { CheckIcon, AlertTriangleIcon } from 'lucide-vue-next'

export const RolCard = defineComponent({
  name: 'RolCard',
  components: { CheckIcon, AlertTriangleIcon },
  props: {
    rol: Object,
    agentes: Array,
  },
  emits: ['guardar'],
  setup(props, { emit }) {
    const seleccion = ref(props.rol.valor || '')
    const guardando = ref(false)
    const guardado  = ref(false)

    watch(() => props.rol.valor, v => { seleccion.value = v || '' })

    const COSTO = {
      'gemini-pro': 'alto', 'claude-sonnet': 'alto', 'deepseek-reasoner': 'alto',
      'deepseek-chat': 'medio', 'gpt-oss-120b': 'medio',
    }
    const VELOCIDAD_LENTA = new Set(['gemini-pro', 'claude-sonnet', 'deepseek-reasoner', 'deepseek-chat'])

    const advertencia = computed(() => {
      if (!seleccion.value) return null
      if (props.rol.advertencia_slugs?.includes(seleccion.value)) return props.rol.advertencia
      return null
    })

    const costoInfo = computed(() => {
      const ag = props.agentes?.find(a => a.slug === seleccion.value)
      if (!ag) return null
      const c = {
        'gemini-pro':        '$3.50/1M tok — costoso',
        'claude-sonnet':     '$3/1M tok — costoso',
        'deepseek-reasoner': 'Caro + muy lento',
        'deepseek-chat':     'Costo moderado, lento ~18s',
        'gpt-oss-120b':      'Costo moderado',
        'gemini-flash':      'Barato ~$0.15/1M',
        'gemini-flash-lite': 'Gratis (150k RPD)',
        'groq-llama':        'Gratis (Groq 14.4k RPD)',
        'cerebras-llama':    'Gratis (Cerebras)',
        'gemma-router':      'Gratis',
        'gemini-image':      'Costo por imagen',
      }
      return c[seleccion.value] || null
    })

    const esCaro = computed(() => props.rol.advertencia_slugs?.includes(seleccion.value))

    async function guardar() {
      guardando.value = true
      await emit('guardar', props.rol.clave, seleccion.value)
      guardando.value = false
      guardado.value = true
      setTimeout(() => { guardado.value = false }, 2000)
    }

    return { seleccion, guardando, guardado, advertencia, costoInfo, esCaro, guardar }
  },
  template: `
    <div class="rol-card" :class="{ 'rol-card-warn': esCaro }">
      <div class="rol-card-nombre">{{ rol.nombre }}</div>
      <div class="rol-card-desc">{{ rol.descripcion }}</div>
      <div class="rol-card-recomendado">
        <CheckIcon :size="11" /> Recomendado: {{ rol.recomendado }}
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin-top:10px">
        <select class="input-field" v-model="seleccion" style="flex:1;height:32px;font-size:13px">
          <option value="">— Sin asignar —</option>
          <option v-for="ag in agentes" :key="ag.slug" :value="ag.slug">
            {{ ag.nombre }}{{ !ag.activo ? ' (inactivo)' : '' }}
          </option>
        </select>
        <button class="btn btn-primary" style="height:32px;font-size:12px;white-space:nowrap" @click="guardar" :disabled="guardando">
          <span v-if="guardado">✓ Guardado</span>
          <span v-else-if="guardando">...</span>
          <span v-else>Guardar</span>
        </button>
      </div>

      <div v-if="costoInfo" style="font-size:11px;color:var(--text-tertiary);margin-top:4px">
        Agente seleccionado: {{ costoInfo }}
      </div>

      <div v-if="advertencia" class="rol-advertencia">
        <AlertTriangleIcon :size="12" style="flex-shrink:0;margin-top:1px" />
        {{ advertencia }}
      </div>
    </div>
  `
})

export const AgenteBadge = defineComponent({
  name: 'AgenteBadge',
  props: { slug: String, agentes: Array, vacio: { type: String, default: '—' } },
  template: `
    <span v-if="slug" class="badge badge-neutral" style="font-size:11px">{{ slug }}</span>
    <span v-else style="color:var(--text-tertiary);font-size:12px">{{ vacio }}</span>
  `
})
</script>

<style scoped>
.rol-seccion {
  margin-bottom: 32px;
}
.rol-seccion-titulo {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}
.rol-seccion-icono { opacity: 0.6; }
.rol-seccion-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 14px;
  max-width: 700px;
}
.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.rol-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px;
  transition: border-color 150ms;
}
.rol-card-warn {
  border-color: var(--color-warning, #f59e0b);
  background: var(--color-warning-bg, rgba(245,158,11,0.05));
}
.rol-card-info {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px;
}
.rol-card-nombre {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 5px;
}
.rol-card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 6px;
}
.rol-card-recomendado {
  font-size: 11px;
  color: var(--color-success, #16a34a);
  display: flex;
  align-items: center;
  gap: 4px;
}
.rol-advertencia {
  margin-top: 8px;
  padding: 7px 9px;
  background: var(--color-warning-bg, rgba(245,158,11,0.08));
  border: 1px solid rgba(245,158,11,0.25);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--color-warning-text, #92400e);
  display: flex;
  gap: 6px;
  align-items: flex-start;
  line-height: 1.4;
}
code {
  background: var(--bg-card-hover);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}
</style>
