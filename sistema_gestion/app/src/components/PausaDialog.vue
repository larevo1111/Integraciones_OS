<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="pd-overlay" @click="cerrar">
        <div class="pd-dialog" @click.stop>
          <div class="pd-title">{{ retroactiva ? 'Agregar Pausa Pasada' : 'Iniciar Pausa' }}</div>

          <div class="pd-label">Tipo de pausa</div>
          <div class="pd-chips">
            <button
              v-for="t in tipos"
              :key="t.id"
              class="pd-chip"
              :class="{ selected: seleccionados.includes(t.id) }"
              @click="toggleTipo(t.id)"
            >{{ t.nombre }}</button>
          </div>
          <div v-if="errorTipos" class="pd-error">Selecciona al menos un tipo</div>

          <!-- Hora de inicio de pausa (siempre visible) -->
          <template v-if="!retroactiva">
            <div class="pd-label" style="margin-top:12px">Hora</div>
            <div class="pd-hora-wrap">
              <span class="material-icons" style="font-size:16px;color:var(--text-tertiary)">schedule</span>
              <input v-model="horaInicio" type="time" step="60" class="pd-time-input" style="width:auto" />
            </div>
          </template>

          <!-- Campos de tiempo para pausa retroactiva -->
          <template v-if="retroactiva">
            <div class="pd-row-2col" style="margin-top:12px">
              <div>
                <div class="pd-label">Hora inicio</div>
                <input v-model="horaInicio" type="time" step="60" class="pd-time-input" />
              </div>
              <div>
                <div class="pd-label">Hora fin</div>
                <input v-model="horaFin" type="time" step="60" class="pd-time-input" />
              </div>
            </div>
            <div v-if="errorTiempo" class="pd-error">{{ errorTiempo }}</div>
          </template>

          <div class="pd-label" style="margin-top:12px">Observaciones <span class="pd-optional">(opcional)</span></div>
          <textarea
            v-model="observaciones"
            class="pd-textarea"
            rows="2"
            placeholder="Comentario sobre la pausa..."
          ></textarea>

          <div class="pd-actions">
            <button class="pd-btn pd-btn-cancel" @click="cerrar">Cancelar</button>
            <button class="pd-btn pd-btn-confirm" @click="confirmar">
              {{ retroactiva ? 'Guardar Pausa' : 'Iniciar Pausa' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { hoyLocal } from 'src/services/fecha'

const props = defineProps({
  modelValue: Boolean,
  tipos: { type: Array, default: () => [] },
  retroactiva: { type: Boolean, default: false },
  fecha: { type: String, default: '' }   // 'YYYY-MM-DD' para construir datetime
})

const emit = defineEmits(['update:modelValue', 'confirmar'])

const seleccionados = ref([])
const observaciones = ref('')
const horaInicio    = ref('')
const horaFin       = ref('')
const errorTipos    = ref(false)
const errorTiempo   = ref('')

watch(() => props.modelValue, (v) => {
  if (v) {
    seleccionados.value = []
    observaciones.value = ''
    errorTipos.value    = false
    errorTiempo.value   = ''
    const ahora = new Date()
    if (props.retroactiva) {
      // Valores por defecto para retroactiva: hace 30 y 15 min
      const hace30 = new Date(ahora - 30 * 60000)
      const hace15 = new Date(ahora - 15 * 60000)
      horaInicio.value = hace30.toTimeString().slice(0, 5)
      horaFin.value    = hace15.toTimeString().slice(0, 5)
    } else {
      // Pausa normal: hora actual para confirmar
      horaInicio.value = ahora.toTimeString().slice(0, 5)
    }
  }
})

function toggleTipo(id) {
  const idx = seleccionados.value.indexOf(id)
  if (idx >= 0) seleccionados.value.splice(idx, 1)
  else seleccionados.value.push(id)
  errorTipos.value = false
}

function cerrar() { emit('update:modelValue', false) }

function confirmar() {
  if (!seleccionados.value.length) { errorTipos.value = true; return }

  if (props.retroactiva) {
    if (!horaInicio.value || !horaFin.value) { errorTiempo.value = 'Completa los dos horarios'; return }
    const fecha = props.fecha || hoyLocal()
    const ini   = new Date(`${fecha}T${horaInicio.value}:00`)
    const fin   = new Date(`${fecha}T${horaFin.value}:00`)
    if (fin <= ini) { errorTiempo.value = 'La hora de fin debe ser después del inicio'; return }

    emit('confirmar', {
      tipos: seleccionados.value,
      observaciones: observaciones.value.trim(),
      hora_inicio: ini.toISOString(),
      hora_fin:    fin.toISOString()
    })
  } else {
    // Pausa normal: construir hora_inicio desde el input de hora
    const fecha = props.fecha || hoyLocal()
    const horaInicioISO = new Date(`${fecha}T${horaInicio.value}:00`).toISOString()
    emit('confirmar', { tipos: seleccionados.value, observaciones: observaciones.value.trim(), hora_inicio: horaInicioISO })
  }
  cerrar()
}
</script>

<style scoped>
.pd-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 9000;
}
.pd-dialog {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 20px;
  width: 340px;
  max-width: 92vw;
}
.pd-title {
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 14px;
}
.pd-label {
  font-size: 12px; font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.pd-optional { color: var(--text-tertiary); font-weight: 400; }

.pd-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.pd-chip {
  padding: 5px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px; font-weight: 500;
  cursor: pointer;
  transition: background 80ms, color 80ms, border-color 80ms;
}
.pd-chip:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.pd-chip.selected {
  background: var(--accent-muted);
  border-color: var(--accent-border);
  color: var(--accent);
}

.pd-hora-wrap {
  display: flex; align-items: center; gap: 8px;
}
.pd-row-2col {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.pd-time-input {
  width: 100%;
  background: var(--bg-input, var(--bg-card));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 7px 10px;
  font-size: 14px; font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.pd-time-input:focus { outline: none; border-color: var(--accent); }

.pd-error { font-size: 11px; color: var(--color-error, #ef5350); margin-top: 4px; }

.pd-textarea {
  width: 100%;
  background: var(--bg-input, var(--bg-card));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-primary);
  resize: vertical;
  font-family: inherit;
}
.pd-textarea:focus { outline: none; border-color: var(--accent); }
.pd-textarea::placeholder { color: var(--text-tertiary); }

.pd-actions {
  display: flex; gap: 8px; justify-content: flex-end;
  margin-top: 16px;
}
.pd-btn {
  padding: 6px 16px;
  border-radius: var(--radius-md);
  font-size: 12px; font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-default);
  transition: background 80ms;
}
.pd-btn-cancel { background: transparent; color: var(--text-secondary); }
.pd-btn-cancel:hover { background: var(--bg-row-hover); }
.pd-btn-confirm { background: var(--accent); border-color: var(--accent); color: #fff; }
.pd-btn-confirm:hover { background: var(--accent-hover); }

.fade-enter-active, .fade-leave-active { transition: opacity 150ms; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
