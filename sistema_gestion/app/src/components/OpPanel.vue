<template>
  <Teleport to="body">
    <div class="op-overlay" @click.self="$emit('cerrar')">
      <aside class="op-panel">

        <!-- ═══ SUB-PANEL: Detalle tarea ═══ -->
        <template v-if="tareaAbierta">
          <div class="op-header">
            <button class="btn-icon" @click="tareaAbierta = null" title="Volver">
              <span class="material-icons" style="font-size:18px">arrow_back</span>
            </button>
            <span class="op-header-tipo">Tarea</span>
            <q-space />
            <button class="btn-icon" title="Cerrar" @click="$emit('cerrar')">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>
          <div class="op-subtarea-wrap">
            <TareaPanel
              :tarea="tareaAbierta"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="[]"
              :etiquetas="[]"
              @cerrar="tareaAbierta = null"
              @actualizada="onTareaActualizada"
              @crear-item="() => {}"
              @abrir-padre="() => {}"
            />
          </div>
        </template>

        <!-- ═══ CONTENIDO PRINCIPAL ═══ -->
        <template v-else>
          <!-- Header -->
          <div class="op-header">
            <span class="op-header-tipo">OP-{{ idOp }}</span>
            <q-chip v-if="ficha?.cabecera"
              :class="estadoClase"
              dense size="sm"
              :label="ficha.cabecera.estado || '—'"
              style="margin-left: 6px"
            />
            <q-chip v-if="estaAnulada"
              class="op-est-anul"
              dense size="sm"
              icon="block"
              label="Anulada"
              style="margin-left: 4px"
            />
            <q-space />
            <button class="btn-icon" title="Cerrar" @click="$emit('cerrar')">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>

          <div v-if="cargando && !ficha" class="op-loading">
            <q-spinner color="primary" size="32px" />
            <div class="text-caption q-mt-sm">Cargando OP...</div>
          </div>

          <div v-if="ficha" class="op-body">
            <!-- ── BLOQUE 1: CABECERA ─────────────────────────── -->
            <div class="op-section">
              <div class="op-cab-row"><span class="op-lbl">Producto</span><span class="op-val">{{ articuloPrincipal || '—' }}</span></div>
              <div class="op-cab-row">
                <span class="op-lbl">Encargado previsto</span>
                <span class="op-val">{{ ficha.cabecera.nombre_encargado || '—' }}</span>
              </div>
              <div class="op-cab-row">
                <span class="op-lbl">Encargado real</span>
                <span class="op-val">
                  <q-select
                    v-if="puedeEditarEncargado"
                    v-model="encargadoRealCC"
                    :options="encargadosOptions"
                    emit-value map-options
                    dense borderless
                    class="op-encargado-sel"
                    :loading="!encargadosLista.length"
                  />
                  <template v-else>{{ encargadoRealNombre || '—' }}</template>
                </span>
              </div>
              <div class="op-cab-row"><span class="op-lbl">Vigencia</span><span class="op-val">{{ ficha.cabecera.vigencia || '—' }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Creada</span><span class="op-val">{{ fmtFecha(ficha.cabecera.fecha_de_creacion) }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Sucursal/Bodega</span><span class="op-val">{{ ficha.cabecera.sucursal || '—' }} / {{ ficha.cabecera.bodega || '—' }}</span></div>
              <div class="op-cab-row">
                <span class="op-lbl">Lote/OP ant</span>
                <span class="op-val">#{{ ficha.detalle?.op_anterior || idOp }}</span>
              </div>
              <div v-if="ficha.detalle?.procesado_por" class="op-cab-row">
                <span class="op-lbl">Procesada por</span>
                <span class="op-val">{{ ficha.detalle.procesado_por }} · {{ fmtFecha(ficha.detalle.procesado_en) }}</span>
              </div>
              <div v-if="ficha.detalle?.validado_por" class="op-cab-row">
                <span class="op-lbl">Validada por</span>
                <span class="op-val">{{ ficha.detalle.validado_por }} · {{ fmtFecha(ficha.detalle.validado_en) }}</span>
              </div>
            </div>

            <!-- ── BLOQUE 2: MATERIALES ───────────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Materiales</div>
              <div v-if="!ficha.materiales.length" class="op-empty">Sin materiales</div>
              <table v-else class="op-table">
                <thead><tr>
                  <th>Material</th>
                  <th class="t-right">Estimado</th>
                  <th class="t-right">Real</th>
                  <th class="t-right">Costo U</th>
                  <th v-if="puedeAgregar"></th>
                </tr></thead>
                <tbody>
                  <tr v-for="l in ficha.materiales" :key="l.id">
                    <td>
                      <span class="text-grey">{{ l.cod_articulo }}</span>
                      <span v-if="l.es_no_previsto" class="badge-no-prev">+</span>
                      <div>{{ l.descripcion }}</div>
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.cantidad_teorica) }} {{ l.unidad }}</td>
                    <td class="t-right">
                      <input
                        type="text" inputmode="decimal"
                        class="op-input-cell"
                        :class="{ 'op-input-cell--locked': lineasBloqueadas }"
                        v-model="valores[l.id]"
                        :placeholder="fmtNum(l.cantidad_teorica)"
                        :readonly="lineasBloqueadas"
                        @beforeinput="filtrarDecimal"
                        @blur="guardarLinea(l)"
                      />
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.costo_unit) }}</td>
                    <td v-if="puedeAgregar" class="t-right">
                      <button class="btn-icon-mini" @click="eliminarLinea(l)" :title="l.es_no_previsto ? 'Eliminar línea no prevista' : 'Eliminar línea (no se enviará a Effi)'">
                        <span class="material-icons" style="font-size:14px">delete_outline</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="puedeAgregar" class="op-add-line">
                <button class="op-btn-add" @click="abrirNuevaLinea('material')">+ agregar material no previsto</button>
              </div>
            </div>

            <!-- ── BLOQUE 3: PRODUCTOS ────────────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Artículos producidos</div>
              <div v-if="!ficha.productos.length" class="op-empty">Sin productos</div>
              <table v-else class="op-table">
                <thead><tr>
                  <th>Artículo</th>
                  <th class="t-right">Estimado</th>
                  <th class="t-right">Real</th>
                  <th class="t-right">Precio U</th>
                  <th v-if="puedeAgregar"></th>
                </tr></thead>
                <tbody>
                  <tr v-for="l in ficha.productos" :key="l.id">
                    <td>
                      <span class="text-grey">{{ l.cod_articulo }}</span>
                      <span v-if="l.es_no_previsto" class="badge-no-prev">+</span>
                      <div>{{ l.descripcion }}</div>
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.cantidad_teorica) }} {{ l.unidad }}</td>
                    <td class="t-right">
                      <input
                        type="text" inputmode="decimal"
                        class="op-input-cell"
                        :class="{ 'op-input-cell--locked': lineasBloqueadas }"
                        v-model="valores[l.id]"
                        :placeholder="fmtNum(l.cantidad_teorica)"
                        :readonly="lineasBloqueadas"
                        @beforeinput="filtrarDecimal"
                        @blur="guardarLinea(l)"
                      />
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.precio_unit) }}</td>
                    <td v-if="puedeAgregar" class="t-right">
                      <button class="btn-icon-mini" @click="eliminarLinea(l)" :title="l.es_no_previsto ? 'Eliminar línea no prevista' : 'Eliminar línea (no se enviará a Effi)'">
                        <span class="material-icons" style="font-size:14px">delete_outline</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="puedeAgregar" class="op-add-line">
                <button class="op-btn-add" @click="abrirNuevaLinea('producto')">+ agregar producto no previsto</button>
              </div>
            </div>

            <!-- ── BLOQUE 4: TIEMPOS CONSOLIDADOS ─────────────── -->
            <div class="op-section">
              <div class="op-section-title">
                Tiempos consolidados
                <span v-if="ficha.fuente_tiempos === 'snapshot'" class="op-tag">snapshot</span>
                <span v-else class="op-tag op-tag-vivo">en vivo</span>
                <q-space />
                <q-btn
                  v-if="puedeEditarTiempos && !editandoTiempos"
                  flat dense no-caps size="xs" icon="edit"
                  label="Editar"
                  @click="iniciarEdicionTiempos"
                />
              </div>

              <!-- Modo VISTA -->
              <template v-if="!editandoTiempos">
                <div v-if="!ficha.tiempos.length" class="op-empty">Aún no hay tiempos registrados</div>
                <table v-else class="op-table">
                  <tbody>
                    <tr v-for="t in ficha.tiempos" :key="t.categoria">
                      <td>{{ t.categoria }}</td>
                      <td class="t-right text-mono">{{ segHHMMSS(t.segundos) }}</td>
                    </tr>
                    <tr class="op-row-total">
                      <td><b>Total</b></td>
                      <td class="t-right text-mono"><b>{{ segHHMMSS(totalSeg) }}</b></td>
                    </tr>
                  </tbody>
                </table>
              </template>

              <!-- Modo EDICIÓN -->
              <template v-else>
                <table class="op-table">
                  <tbody>
                    <tr v-for="(t, idx) in tiemposEdit" :key="'edit-'+idx">
                      <td>
                        <q-select
                          v-model="t.categoria_produccion_id"
                          :options="categoriasProduccion.map(c => ({ value: c.id, label: c.nombre }))"
                          emit-value map-options
                          dense borderless
                          class="op-cat-sel"
                        />
                      </td>
                      <td class="t-right">
                        <span class="tiempo-edit-row">
                          <input
                            type="number" inputmode="numeric" min="0"
                            class="op-input-num text-mono"
                            style="width:46px"
                            :value="Math.floor((t.segundos || 0) / 3600)"
                            @input="onTiempoH(idx, $event.target.value)"
                            placeholder="0"
                          />
                          <span class="t-sep">h</span>
                          <input
                            type="number" inputmode="numeric" min="0" max="59"
                            class="op-input-num text-mono"
                            style="width:46px"
                            :value="Math.floor(((t.segundos || 0) % 3600) / 60)"
                            @input="onTiempoM(idx, $event.target.value)"
                            placeholder="0"
                          />
                          <span class="t-sep">m</span>
                        </span>
                      </td>
                      <td class="t-right">
                        <button class="btn-icon-mini" @click="eliminarTiempoFila(idx)" title="Eliminar">
                          <span class="material-icons" style="font-size:14px">delete_outline</span>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div class="op-add-line">
                  <button class="op-btn-add" @click="agregarTiempoFila">+ agregar tiempo</button>
                </div>
                <div class="row q-gutter-xs q-mt-sm">
                  <q-btn flat dense no-caps size="sm" label="Cancelar" @click="cancelarEdicionTiempos" />
                  <q-space />
                  <q-btn unelevated dense no-caps size="sm" color="primary" label="Guardar" :loading="guardandoTiempos" @click="guardarTiempos" />
                </div>
              </template>
            </div>

            <!-- ── BLOQUE 5: PUNTOS CRÍTICOS DEL PROCESO ──────── -->
            <PuntosCriticosPanel
              :id-op="String(idOp)"
              :read-only="estado === 'Validado' || estaAnulada"
            />

            <!-- ── BLOQUE 6: CALIDAD ──────────────────────────── -->
            <CalidadPanel
              ref="calidadPanelRef"
              :id-op="String(idOp)"
              :estado-op="estado"
              :es-anulada="estaAnulada"
            />

            <!-- ── BLOQUE 7: TAREAS VINCULADAS ────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Tareas vinculadas ({{ ficha.tareas_vinculadas.length }})</div>

              <!-- Quickadd tarea (igual que ProyectoPanel) -->
              <form class="quickadd-row" :class="{ activo: mostrarFormTarea }" @submit.prevent="crearTareaEnOp">
                <span class="material-icons quickadd-plus">add</span>
                <input
                  v-model="nuevaTareaTitulo"
                  class="quickadd-input"
                  placeholder="Agregar una tarea..."
                  @focus="mostrarFormTarea = true"
                  @keydown.escape="mostrarFormTarea = false; nuevaTareaTitulo = ''"
                />
                <template v-if="mostrarFormTarea">
                  <button type="submit" class="btn-icon" :disabled="!nuevaTareaTitulo.trim()" title="Agregar">
                    <span class="material-icons" style="font-size:18px;color:var(--accent)">check</span>
                  </button>
                  <button type="button" class="btn-icon" @click="mostrarFormTarea = false; nuevaTareaTitulo = ''" title="Cancelar">
                    <span class="material-icons" style="font-size:18px">close</span>
                  </button>
                </template>
              </form>
              <template v-if="mostrarFormTarea">
                <div class="quickadd-extra">
                  <CatProduccionSelector
                    v-model="nuevaTareaCatProdId"
                    :categorias="categoriasProduccion"
                  />
                  <ResponsablesSelector
                    :single="false"
                    :model-value="nuevaTareaResponsables"
                    :usuarios="usuarios"
                    @update:model-value="v => nuevaTareaResponsables = v"
                  />
                  <EtiquetasSelector
                    v-model="nuevaTareaEtiquetas"
                    :etiquetas="etiquetasGlobal"
                  />
                  <q-input
                    v-model="nuevaTareaFecha"
                    type="date"
                    dense outlined
                    class="quickadd-date"
                  >
                    <template #prepend>
                      <q-icon name="event" size="16px" />
                    </template>
                  </q-input>
                </div>
              </template>

              <div v-if="!ficha.tareas_vinculadas.length && !mostrarFormTarea" class="op-empty">Sin tareas asignadas a esta OP</div>
              <ul v-if="ficha.tareas_vinculadas.length" class="op-tareas">
                <li v-for="t in ficha.tareas_vinculadas" :key="t.id" class="op-tarea" @click="abrirTarea(t)">
                  <div class="op-tarea-row1">
                    <span class="op-tarea-titulo">{{ t.titulo }}</span>
                    <span class="op-tarea-estado" :class="'estado-'+ slug(t.estado)">{{ t.estado }}</span>
                  </div>
                  <div class="op-tarea-row2">
                    <span>{{ t.responsable_nombre || t.responsable || '—' }}</span>
                    <span v-if="t.categoria_produccion_nombre" class="op-tarea-cat">{{ t.categoria_produccion_nombre }}</span>
                    <span class="op-tarea-cron">{{ segHHMMSS(t.duracion_cronometro_seg) }}</span>
                  </div>
                </li>
              </ul>
            </div>

            <!-- ── BLOQUE 6: OBSERVACIONES DEL LOTE ───────────── -->
            <div class="op-section">
              <div class="op-section-title">Observaciones del lote</div>
              <textarea
                class="op-textarea"
                rows="3"
                v-model="obsLote"
                placeholder="Notas, hallazgos, eventos del lote..."
                @blur="guardarObs"
              ></textarea>
            </div>

            <!-- ── BLOQUE 7: ACCIONES ─────────────────────────── -->
            <div class="op-section op-acciones">
              <div v-if="estaAnulada" class="op-aviso-anulada">
                <span class="material-icons" style="font-size:16px;color:#888">block</span>
                Esta OP está anulada en Effi. No se puede procesar ni validar.
              </div>
              <template v-else>
                <button
                  v-if="puedeProcesar"
                  class="btn-procesar"
                  :disabled="procesando || estado === 'Procesada' || estado === 'Validado'"
                  @click="confirmarProcesar"
                >
                  <span class="material-icons" style="font-size:16px">check_circle_outline</span>
                  {{ procesando ? 'Procesando...' : 'Procesar' }}
                </button>
                <button
                  v-if="puedeValidar"
                  class="btn-validar"
                  :disabled="validando || estado === 'Validado'"
                  @click="confirmarValidar"
                >
                  <span class="material-icons" style="font-size:16px">verified</span>
                  {{ validando ? 'Validando...' : 'Validar' }}
                </button>
              </template>
            </div>
          </div>
        </template>
      </aside>
    </div>

    <!-- Diálogo: confirmar procesar / validar (encargado se elige en el panel) -->
    <q-dialog v-model="dialogConfirm" persistent>
      <q-card style="min-width:380px;max-width:90vw">
        <q-card-section>
          <div class="text-h6">{{ confirmTipo === 'validar' ? 'Validar' : 'Procesar' }} OP {{ idOp }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey">
            {{ confirmTipo === 'validar'
              ? 'Anula la OP, crea una nueva con los reales reportados y la marca como Validado. Corre en segundo plano (~2-3 min).'
              : 'Cambia el estado de la OP a Procesada en Effi. Corre en segundo plano (~30-60s).' }}
          </div>

          <div class="q-mt-md" style="font-size:13px">
            Encargado: <b>{{ encargadoRealNombre || ficha?.cabecera?.nombre_encargado || '—' }}</b>
          </div>

          <div v-if="confirmAviso" class="q-mt-md" style="color:#ffa726;font-size:13px">
            {{ confirmAviso }}
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="dialogConfirm = false" />
          <q-btn
            unelevated
            :label="confirmTipo === 'validar' ? 'Validar' : 'Procesar'"
            :color="confirmTipo === 'validar' ? 'positive' : 'warning'"
            @click="ejecutarConfirmar"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Diálogo: agregar línea no prevista -->
    <q-dialog v-model="dialogNuevaLinea" persistent>
      <q-card style="min-width:380px;max-width:90vw">
        <q-card-section><div class="text-h6">Agregar {{ nuevaLinea.tipo }} no previsto</div></q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey q-mb-xs">Artículo</div>
          <ArticuloSelector
            v-model="articuloSeleccionado"
            :tipo="nuevaLinea.tipo"
            :placeholder="nuevaLinea.tipo === 'producto' ? 'Buscar producto…' : 'Buscar material…'"
          />
          <div v-if="articuloSeleccionado" class="row items-end q-gutter-sm q-mt-md">
            <q-input
              v-model="nuevaLinea.cantidad_real"
              label="Cantidad"
              dense filled inputmode="decimal" autofocus
              class="col"
              :suffix="articuloSeleccionado.unidad || ''"
            />
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="cerrarDialogNuevaLinea" />
          <q-btn
            unelevated label="Agregar" color="primary"
            :disable="!articuloSeleccionado || !nuevaLinea.cantidad_real"
            @click="agregarLineaNoPrevista"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { fmtNum, parseDecimal } from 'src/services/numero'
import { useAuthStore } from 'src/stores/authStore'
import { crearTarea } from 'src/composables/useTareas'
import TareaPanel from './TareaPanel.vue'
import ResponsablesSelector from './ResponsablesSelector.vue'
import EtiquetasSelector from './EtiquetasSelector.vue'
import CatProduccionSelector from './CatProduccionSelector.vue'
import ArticuloSelector from './ArticuloSelector.vue'
import CalidadPanel from './CalidadPanel.vue'
import PuntosCriticosPanel from './PuntosCriticosPanel.vue'

const $q  = useQuasar()
const auth = useAuthStore()

const props = defineProps({
  idOp:       { type: [String, Number], required: true },
  usuarios:   { type: Array, default: () => [] },
  categorias: { type: Array, default: () => [] },
})
const emit = defineEmits(['cerrar', 'actualizada'])

const ficha       = ref(null)
const cargando    = ref(false)
const calidadPanelRef = ref(null)
const obsLote     = ref('')
const valores     = reactive({})  // id_linea -> string editable del input "Real"
const tareaAbierta = ref(null)
const procesando  = ref(false)
const validando   = ref(false)
const dialogNuevaLinea = ref(false)
const nuevaLinea = reactive({ tipo: 'material', cantidad_real: '' })

// Diálogo confirmar procesar/validar con selector de encargado real
const dialogConfirm = ref(false)
const confirmTipo = ref('')              // 'procesar' | 'validar'
const confirmAviso = ref('')             // HTML extra (warnings de calidad en validar)
const encargadosLista = ref([])          // { email, nombre, cc, nivel } desde /api/gestion/encargados
const encargadoRealCC = ref('')          // CC seleccionado en el dialog
const articuloSeleccionado = ref(null)  // {cod, nombre, unidad, costo_unit, precio_unit, grupo}

// Quickadd tarea vinculada a esta OP
const categoriasProduccion = ref([])
const etiquetasGlobal      = ref([])
const mostrarFormTarea     = ref(false)
const nuevaTareaTitulo     = ref('')
const nuevaTareaCatProdId  = ref(null)
const nuevaTareaResponsables = ref(auth.usuario?.email ? [auth.usuario.email] : [])
const nuevaTareaEtiquetas  = ref([])
const nuevaTareaFecha      = ref('')

const miNivel = computed(() => auth.usuario?.nivel || 1)
const estado = computed(() => ficha.value?.cabecera?.estado || '')
const vigencia = computed(() => ficha.value?.cabecera?.vigencia || '')
const estaAnulada = computed(() => vigencia.value === 'Anulado')
const puedeProcesar = computed(() => miNivel.value >= 3 && !estaAnulada.value)
const puedeValidar  = computed(() => miNivel.value >= 5 && !estaAnulada.value)
const puedeAgregar = computed(() => estado.value === 'Generada' && miNivel.value >= 3 && !estaAnulada.value)
const puedeEditarTiempos = computed(() => miNivel.value >= 5)
const lineasBloqueadas = computed(() => estado.value === 'Validado' || estaAnulada.value)
// Encargado real editable en Generada o Procesada (mismos criterios que materiales reales)
const puedeEditarEncargado = computed(() => !lineasBloqueadas.value)
const encargadosOptions = computed(() =>
  encargadosLista.value.map(e => ({ value: e.cc, label: e.nombre }))
)
const encargadoRealNombre = computed(() => {
  const e = encargadosLista.value.find(x => x.cc === encargadoRealCC.value)
  return e?.nombre || ficha.value?.cabecera?.nombre_encargado || ''
})

// Edición tiempos consolidados (nivel >= 5)
const editandoTiempos = ref(false)
const tiemposEdit = ref([])
const guardandoTiempos = ref(false)

function iniciarEdicionTiempos() {
  // Copia editable: usa categoria_id del backend si está, o resuelve por nombre
  tiemposEdit.value = (ficha.value?.tiempos || []).map(t => ({
    categoria_produccion_id: t.categoria_id || categoriasProduccion.value.find(c => c.nombre === t.categoria)?.id || null,
    segundos: t.segundos
  })).filter(t => t.categoria_produccion_id)
  editandoTiempos.value = true
}
function cancelarEdicionTiempos() {
  editandoTiempos.value = false
  tiemposEdit.value = []
}
function agregarTiempoFila() {
  // Elegir primera categoría no usada (o cualquiera si todas se usaron)
  const usadas = new Set(tiemposEdit.value.map(t => t.categoria_produccion_id))
  const libre = categoriasProduccion.value.find(c => !usadas.has(c.id)) || categoriasProduccion.value[0]
  if (!libre) return
  tiemposEdit.value.push({ categoria_produccion_id: libre.id, segundos: 0 })
}
function eliminarTiempoFila(idx) {
  tiemposEdit.value.splice(idx, 1)
}
function onTiempoH(idx, valor) {
  const h = Math.max(0, parseInt(valor) || 0)
  const m = Math.floor(((tiemposEdit.value[idx].segundos || 0) % 3600) / 60)
  tiemposEdit.value[idx].segundos = h * 3600 + m * 60
}
function onTiempoM(idx, valor) {
  const m = Math.max(0, Math.min(59, parseInt(valor) || 0))
  const h = Math.floor((tiemposEdit.value[idx].segundos || 0) / 3600)
  tiemposEdit.value[idx].segundos = h * 3600 + m * 60
}
async function guardarTiempos() {
  guardandoTiempos.value = true
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/tiempos`, {
      method: 'PUT',
      body: JSON.stringify({ tiempos: tiemposEdit.value })
    })
    editandoTiempos.value = false
    tiemposEdit.value = []
    await cargar()
    $q.notify({ type: 'positive', message: 'Tiempos actualizados', position: 'top', timeout: 2000 })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error al guardar', position: 'top' })
  } finally { guardandoTiempos.value = false }
}

const totalSeg = computed(() => (ficha.value?.tiempos || []).reduce((s, t) => s + (Number(t.segundos)||0), 0))

const articuloPrincipal = computed(() => {
  const p = ficha.value?.productos?.[0]
  return p ? p.descripcion : (ficha.value?.materiales?.[0]?.descripcion || '')
})

const estadoClase = computed(() => {
  const e = (estado.value || '').toLowerCase()
  if (e === 'validado')  return 'op-est-val'
  if (e === 'procesada') return 'op-est-proc'
  if (e === 'anulada')   return 'op-est-anul'
  return 'op-est-gen'
})

async function cargar() {
  cargando.value = true
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/ficha`)
    ficha.value = r
    obsLote.value = r.detalle?.observaciones_lote || ''
    // Inicializar inputs editables de cantidad_real
    Object.keys(valores).forEach(k => delete valores[k])
    for (const l of [...(r.materiales || []), ...(r.productos || [])]) {
      valores[l.id] = l.cantidad_real == null ? '' : fmtNum(l.cantidad_real)
    }
    // Prellenar encargado real: si la OP ya tiene encargado_real_cc guardado, usar ese;
    // sino, default = CC del predefinido (Effi). Cargar lista en paralelo.
    encargadoRealCC.value = r.detalle?.encargado_real_cc || _ccPredefinida()
    _cargarEncargados()
    if (!jobActivo.value) checarJobActivo()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error cargando OP: ' + (e.message || e), position: 'top' })
  } finally { cargando.value = false }
}

async function cargarCatalogosQuickadd() {
  if (categoriasProduccion.value.length && etiquetasGlobal.value.length) return
  try {
    const [cp, et] = await Promise.all([
      api('/api/gestion/categorias-produccion').catch(() => ({})),
      api('/api/gestion/etiquetas').catch(() => ({})),
    ])
    categoriasProduccion.value = cp.categorias || []
    etiquetasGlobal.value      = et.etiquetas  || []
  } catch (e) { console.warn('[OpPanel] catálogos quickadd:', e?.message) }
}

async function crearTareaEnOp() {
  const titulo = nuevaTareaTitulo.value.trim()
  if (!titulo) return
  const catProduccion = props.categorias.find(c => c.es_produccion) || props.categorias.find(c => /produccion/i.test(c.nombre || ''))
  if (!catProduccion) {
    $q.notify({ type: 'negative', message: 'No se encontró la categoría Producción', position: 'top' })
    return
  }
  try {
    await crearTarea({
      titulo,
      categoria_id: catProduccion.id,
      categoria_produccion_id: nuevaTareaCatProdId.value,
      id_op: String(props.idOp),
      responsables: nuevaTareaResponsables.value,
      etiquetas: nuevaTareaEtiquetas.value,
      fecha_limite: nuevaTareaFecha.value || null
    })
    nuevaTareaTitulo.value = ''
    nuevaTareaCatProdId.value = null
    nuevaTareaResponsables.value = auth.usuario?.email ? [auth.usuario.email] : []
    nuevaTareaEtiquetas.value = []
    nuevaTareaFecha.value = ''
    mostrarFormTarea.value = false
    await cargar()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error creando tarea: ' + (e.message || e), position: 'top' })
  }
}

watch(() => props.idOp, () => { _limpiarJob(); cargar() })
onMounted(() => { cargar(); cargarCatalogosQuickadd() })

function fmtFecha(s) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d)) return String(s)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toTimeString().slice(0, 5)
}
function segHHMMSS(seg) {
  seg = Number(seg) || 0
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  const s = seg % 60
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':')
}
function slug(s) { return String(s || '').toLowerCase().replace(/\s+/g, '-') }
// Filtro mientras se escribe: solo dígitos y un único separador decimal (, o .)
function filtrarDecimal(e) {
  if (e.data == null) return  // borrado / navegación: siempre permitir
  if (!/^[0-9.,]$/.test(e.data)) { e.preventDefault(); return }
  // No permitir un segundo separador si ya hay uno
  if (/[.,]/.test(e.data) && /[.,]/.test(e.target.value)) e.preventDefault()
}

async function guardarLinea(l) {
  if (lineasBloqueadas.value) return
  const raw = valores[l.id]
  const val = parseDecimal(raw)
  if (val === l.cantidad_real) return
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas/${l.id}`, {
      method: 'PUT', body: JSON.stringify({ cantidad_real: val })
    })
    l.cantidad_real = r.cantidad_real
    valores[l.id] = r.cantidad_real == null ? '' : fmtNum(r.cantidad_real)
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error guardando: ' + (e.message || e), position: 'top' })
  }
}

async function guardarObs() {
  const v = (obsLote.value || '').trim() || null
  const previa = (ficha.value?.detalle?.observaciones_lote || '').trim() || null
  if (v === previa) return
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/detalle`, {
      method: 'PUT', body: JSON.stringify({ observaciones_lote: v })
    })
    if (ficha.value) {
      if (!ficha.value.detalle) ficha.value.detalle = {}
      ficha.value.detalle.observaciones_lote = v
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error guardando obs: ' + (e.message || e), position: 'top' })
  }
}

function abrirNuevaLinea(tipo) {
  nuevaLinea.tipo = tipo
  nuevaLinea.cantidad_real = ''
  articuloSeleccionado.value = null
  dialogNuevaLinea.value = true
}
function cerrarDialogNuevaLinea() {
  dialogNuevaLinea.value = false
  articuloSeleccionado.value = null
  nuevaLinea.cantidad_real = ''
}

async function agregarLineaNoPrevista() {
  if (!articuloSeleccionado.value) return
  const a = articuloSeleccionado.value
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas`, {
      method: 'POST',
      body: JSON.stringify({
        tipo: nuevaLinea.tipo,
        cod_articulo: a.cod,
        descripcion: a.nombre,
        unidad: a.unidad || '',
        cantidad_real: parseDecimal(nuevaLinea.cantidad_real),
        costo_unit: a.costo_unit ?? null,
        precio_unit: a.precio_unit ?? null,
      })
    })
    cerrarDialogNuevaLinea()
    await cargar()
    $q.notify({ type: 'positive', message: 'Línea agregada', position: 'top' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error', position: 'top' })
  }
}

async function eliminarLinea(l) {
  $q.dialog({
    title: `Eliminar ${l.tipo}`,
    message: `${l.cod_articulo} · ${l.descripcion}<br><span style="color:var(--text-tertiary);font-size:12px">No se enviará a Effi al validar.</span>`,
    html: true,
    cancel: { label: 'Cancelar', flat: true, color: 'grey-5' },
    ok:     { label: 'Eliminar', unelevated: true, color: 'negative' },
    persistent: false, dark: true
  }).onOk(async () => {
    try {
      await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas/${l.id}`, { method: 'DELETE' })
      await cargar()
      $q.notify({ type: 'positive', message: 'Línea eliminada', position: 'top', timeout: 2000 })
    } catch (e) {
      $q.notify({ type: 'negative', message: e.message || 'Error', position: 'top' })
    }
  })
}

function abrirTarea(t) { tareaAbierta.value = { ...t } }
function onTareaActualizada(t) {
  if (t && ficha.value) {
    const i = ficha.value.tareas_vinculadas.findIndex(x => x.id === t.id)
    if (i !== -1) ficha.value.tareas_vinculadas[i] = { ...ficha.value.tareas_vinculadas[i], ...t }
  }
  tareaAbierta.value = null
  cargar()
}

// ─── Background jobs (procesar / validar) ────────────────────────
// Pollea el estado del job hasta que termine. Notify persistente mientras corre.
const jobActivo = ref(null)
let _pollTimer = null
let _dismissJob = null

function _limpiarJob() {
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null }
  if (_dismissJob) { _dismissJob(); _dismissJob = null }
  jobActivo.value = null
  procesando.value = false
  validando.value = false
}

async function _pollearJob(jobId) {
  try {
    const r = await api(`/api/gestion/op/jobs/${jobId}`)
    jobActivo.value = { jobId: r.jobId, tipo: r.tipo, estado: r.estado }
    if (r.estado === 'exitoso') {
      _limpiarJob()
      if (r.tipo === 'validar' && r.resultado?.id_op_nueva) {
        $q.notify({ type: 'positive', message: `OP ${r.resultado.id_op_anterior} → Anulada · OP ${r.resultado.id_op_nueva} → Validado`, position: 'top', timeout: 6000 })
        emit('actualizada', r.resultado.id_op_nueva)
      } else {
        $q.notify({ type: 'positive', message: `OP ${props.idOp} → ${r.tipo === 'procesar' ? 'Procesada' : 'Validada'}`, position: 'top', timeout: 5000 })
        await cargar(); emit('actualizada')
      }
      return
    }
    if (r.estado === 'fallido') {
      _limpiarJob()
      $q.notify({ type: 'negative', message: r.error || 'Error en la operación', position: 'top', timeout: 9000, multiLine: true })
      await cargar()
      return
    }
    _pollTimer = setTimeout(() => _pollearJob(jobId), 3000)
  } catch (e) {
    _pollTimer = setTimeout(() => _pollearJob(jobId), 5000)
  }
}

function _iniciarPolling(jobId, tipo) {
  if (_pollTimer || _dismissJob) _limpiarJob()
  jobActivo.value = { jobId, tipo, estado: 'pendiente' }
  if (tipo === 'procesar') procesando.value = true
  else if (tipo === 'validar') validando.value = true
  const label = tipo === 'procesar' ? 'Procesando' : 'Validando'
  _dismissJob = $q.notify({
    type: 'ongoing', position: 'top', timeout: 0,
    message: `${label} OP ${props.idOp}…`,
    caption: 'Corre en segundo plano. Si cerrás el panel, podés reabrirlo para ver el resultado.'
  })
  _pollearJob(jobId)
}

async function checarJobActivo() {
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/job-activo`)
    if (r.activo) _iniciarPolling(r.activo.jobId, r.activo.tipo)
  } catch (_) {}
}

async function _cargarEncargados() {
  if (encargadosLista.value.length) return
  try {
    const r = await api('/api/gestion/encargados')
    encargadosLista.value = r.encargados || []
  } catch (e) {
    console.warn('[OpPanel] No se pudo cargar lista de encargados:', e.message)
  }
}

// Resuelve la CC predefinida desde id_encargado (formato Effi 'CC: 74084937')
function _ccPredefinida() {
  const raw = ficha.value?.cabecera?.id_encargado || ''
  return String(raw).replace(/^CC:\s*/, '').trim()
}

async function abrirConfirmar(tipo) {
  await _cargarEncargados()
  confirmTipo.value = tipo
  encargadoRealCC.value = _ccPredefinida()
  confirmAviso.value = ''
  if (tipo === 'validar') {
    // Soft-block: avisa si calidad no firmada / rechazada / inexistente
    const insp = calidadPanelRef.value?.insp?.value || calidadPanelRef.value?.insp || null
    if (!insp) {
      confirmAviso.value = '⚠️ Esta OP no tiene inspección de calidad registrada.'
    } else if (insp.firmada !== 1) {
      confirmAviso.value = '⚠️ La inspección de calidad está como borrador (sin firmar).'
    } else if (insp.resultado === 'rechazado') {
      confirmAviso.value = '⚠️ Calidad = Rechazado.'
    }
  }
  dialogConfirm.value = true
}

async function ejecutarConfirmar() {
  const tipo = confirmTipo.value
  const ccElegida = String(encargadoRealCC.value || '').trim()
  const ccDefault = _ccPredefinida()
  // Solo enviar encargado_real si difiere del predefinido
  let body = null
  if (ccElegida && ccElegida !== ccDefault) {
    const enc = encargadosLista.value.find(e => e.cc === ccElegida)
    body = { encargado_real_cc: ccElegida, encargado_real_nombre: enc?.nombre || '' }
  }
  dialogConfirm.value = false
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/${tipo}`, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined
    })
    _iniciarPolling(r.jobId, r.tipo || tipo)
  } catch (e) {
    if (e?.retry) setTimeout(() => abrirConfirmar(tipo), tipo === 'validar' ? 5000 : 3000)
    else $q.notify({ type: 'negative', message: e.message || 'Error al iniciar', position: 'top', timeout: 6000 })
  }
}

const confirmarProcesar = () => abrirConfirmar('procesar')
const confirmarValidar  = () => abrirConfirmar('validar')

onUnmounted(() => _limpiarJob())
</script>

<style scoped>
.op-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.45); display: flex; justify-content: flex-end;
}
.op-panel {
  width: 648px; max-width: 100vw; height: 100%;
  background: var(--bg-card); color: var(--text-primary);
  display: flex; flex-direction: column;
  overflow: hidden; box-shadow: -2px 0 16px rgba(0,0,0,0.3);
}
.op-header {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px; border-bottom: 1px solid var(--border-default);
}
.op-header-tipo { font-size: 13px; font-weight: 600; }
.op-loading { padding: 60px 0; text-align: center; }
.op-body {
  flex: 1; overflow-y: auto; padding: 6px 12px 24px;
}
.op-section { padding: 10px 0; border-bottom: 1px solid var(--border-subtle); }
.op-section-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
  display: flex; align-items: center; gap: 6px;
}
.op-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-row-hover); color: var(--text-tertiary); font-weight: 500;
}
.op-tag-vivo { background: #2db14a33; color: #2db14a; }
.op-empty { font-size: 11px; color: var(--text-tertiary); font-style: italic; padding: 4px 0; }
.op-cab-row {
  display: flex; align-items: center;
  font-size: 12px; padding: 3px 0;
}
.op-lbl { width: 130px; color: var(--text-tertiary); font-size: 11px; }
.op-val { flex: 1; }
/* Select inline del encargado real: estilo discreto, sin marco grueso */
.op-encargado-sel { min-width: 220px; max-width: 320px; }
.op-encargado-sel :deep(.q-field__control) { min-height: 28px; padding: 0; }
.op-encargado-sel :deep(.q-field__native) { padding: 0; min-height: 22px; font-size: 12px; }

.op-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.op-table thead th {
  text-align: left; font-size: 10px; font-weight: 500;
  color: var(--text-tertiary); padding: 4px 4px;
  border-bottom: 1px solid var(--border-default);
}
.op-table thead th.t-right { text-align: right; }
.op-table tbody td { padding: 6px 4px; border-bottom: 1px solid var(--border-subtle); vertical-align: top; }
.op-table tbody tr:last-child td { border-bottom: none; }
.t-right { text-align: right; }
.text-mono { font-family: var(--font-mono, monospace); }
.text-grey { color: var(--text-tertiary); font-size: 11px; }
.op-row-total { background: var(--bg-row-hover); }
.op-input-num {
  width: 80px; padding: 4px 6px;
  background: var(--bg-row-hover); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  font-size: 12px; text-align: right;
}
.op-input-num:focus { outline: 2px solid var(--accent); }

/* Input dentro de tabla — alineado al borde derecho del header (sin border/padding horizontal) */
.op-input-cell {
  width: 80px; padding: 4px 0; margin: 0;
  background: var(--bg-row-hover); color: var(--text-primary);
  border: none; border-radius: 3px;
  font-size: 12px; text-align: right; font-family: inherit;
}
.op-input-cell:hover { background: var(--bg-card); }
.op-input-cell:focus { outline: 1.5px solid var(--accent); outline-offset: -1.5px; background: var(--bg-card); }
.op-input-cell--locked,
.op-input-cell--locked:hover,
.op-input-cell--locked:focus {
  background: transparent; cursor: not-allowed; outline: none;
  color: var(--text-secondary);
}

.tiempo-edit-row {
  display: inline-flex; align-items: center; gap: 4px;
  justify-content: flex-end;
}
.tiempo-edit-row .t-sep {
  font-size: 11px; color: var(--text-tertiary); margin: 0 2px;
}

.badge-no-prev {
  display: inline-block; margin-left: 4px;
  font-size: 10px; padding: 0 4px; border-radius: 6px;
  background: var(--accent); color: #fff; font-weight: 600;
}

.op-add-line { margin-top: 6px; }
.op-btn-add {
  background: transparent; color: var(--accent);
  border: 1px dashed var(--border-default);
  padding: 4px 10px; border-radius: 4px;
  font-size: 11px; cursor: pointer;
}
.op-btn-add:hover { background: var(--bg-row-hover); }

.op-tareas { list-style: none; margin: 0; padding: 0; }
.op-tarea {
  padding: 6px 8px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--border-subtle); margin-bottom: 4px;
}
.op-tarea:hover { background: var(--bg-row-hover); border-color: var(--border-default); }
.op-tarea-row1 {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-weight: 500;
}
.op-tarea-titulo { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.op-tarea-estado {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-row-hover); color: var(--text-tertiary); margin-left: 8px;
}
.op-tarea-estado.estado-en-progreso { background: #2196f333; color: #2196f3; }
.op-tarea-estado.estado-completada { background: #2db14a33; color: #2db14a; }
.op-tarea-estado.estado-pendiente { background: #ffa72633; color: #ffa726; }
.op-tarea-row2 {
  display: flex; gap: 10px; font-size: 10px;
  color: var(--text-tertiary); margin-top: 2px;
}
.op-tarea-cat { color: var(--accent); }
.op-tarea-cron { margin-left: auto; font-family: var(--font-mono, monospace); }

.op-textarea {
  width: 100%; min-height: 60px; resize: vertical;
  background: var(--bg-row-hover); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 12px; font-family: inherit;
}
.op-textarea:focus { outline: 2px solid var(--accent); }

.op-acciones { display: flex; gap: 8px; padding-top: 12px; border-bottom: none; }
.op-aviso-anulada {
  flex: 1; display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 6px;
  background: var(--bg-row-hover); border: 1px solid var(--border-default);
  color: var(--text-secondary); font-size: 12px;
}
.btn-procesar, .btn-validar {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer;
  font-size: 12px; font-weight: 600;
}
.btn-procesar { background: #ffa726; color: #000; }
.btn-procesar:hover:not(:disabled) { background: #ff9800; }
.btn-validar { background: #2db14a; color: #fff; }
.btn-validar:hover:not(:disabled) { background: #1f8c38; }
.btn-procesar:disabled, .btn-validar:disabled { opacity: 0.4; cursor: not-allowed; }

.op-est-val   { background: #2db14a; color: #fff; }
.op-est-proc  { background: #ffa726; color: #000; }
.op-est-anul  { background: #888;    color: #fff; }
.op-est-gen   { background: #ccc;    color: #000; }

.btn-icon {
  background: transparent; border: none; color: var(--text-secondary);
  padding: 4px; border-radius: 4px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.btn-icon:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.btn-icon-mini {
  background: transparent; border: none; color: var(--text-tertiary);
  padding: 2px; border-radius: 4px; cursor: pointer;
}
.btn-icon-mini:hover { color: var(--negative); }

.op-subtarea-wrap {
  flex: 1; overflow-y: auto;
}

@media (max-width: 768px) {
  .op-panel { width: 100vw; }
  /* Espacio inferior para que el bottombar móvil no tape Procesar/Validar */
  .op-body { padding-bottom: calc(80px + env(safe-area-inset-bottom, 0)); }
}
</style>
