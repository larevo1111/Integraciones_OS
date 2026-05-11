// Búsqueda contextual en el header global del MainLayout.
// Cada página que necesite quicksearch la activa al montarse y la apaga al salir;
// el HeaderSearch del header consume este estado y emite cambios con debounce.

import { ref } from 'vue'

const enabled = ref(false)
const value = ref('')
const placeholder = ref('Buscar...')
let onChangeCb = null

export function usePageSearch() {
  return { enabled, value, placeholder }
}

export function activarBusqueda({ placeholder: p, onChange } = {}) {
  enabled.value = true
  value.value = ''
  placeholder.value = p || 'Buscar...'
  onChangeCb = typeof onChange === 'function' ? onChange : null
}

export function desactivarBusqueda() {
  enabled.value = false
  value.value = ''
  placeholder.value = 'Buscar...'
  onChangeCb = null
}

export function emitirBusqueda(v) {
  value.value = v ?? ''
  if (onChangeCb) onChangeCb(value.value)
}
