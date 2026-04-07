/**
 * useMultiSelect — composable para selección múltiple de filas y edición masiva.
 *
 * Uso:
 *   const ms = useMultiSelect({
 *     endpointBase: '/api/gestion/tareas',
 *     onAfter: async () => { await cargar(); },
 *   })
 *
 *   ms.toggle(item)            // agregar/quitar de la selección
 *   ms.clear()                 // limpiar
 *   ms.selectedIds.value       // array reactivo de IDs
 *   await ms.bulkPut({ estado: 'Completada' })   // PUT a /endpoint/:id por cada seleccionado
 *   await ms.bulkDelete()      // DELETE por cada seleccionado
 *
 * Soporte teclado y click-fuera:
 *   - Escape limpia la selección
 *   - Click fuera de elementos con clases ignoreSelectors limpia
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'

export function useMultiSelect({
  endpointBase,
  onAfter = async () => {},
  // Selectores que NO deben limpiar la selección al hacer click
  ignoreSelectors = ['.tarea-item', '.os-table .data-row', '.multi-bar', '.multi-bar-menu']
} = {}) {
  const selectedIds = ref([])

  function toggle(item) {
    const idx = selectedIds.value.indexOf(item.id)
    if (idx === -1) selectedIds.value.push(item.id)
    else selectedIds.value.splice(idx, 1)
  }

  function add(id) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  }

  function clear() {
    selectedIds.value = []
  }

  function isSelected(id) {
    return selectedIds.value.includes(id)
  }

  // PUT genérico a cada ID
  async function bulkPut(body) {
    const ids = [...selectedIds.value]
    await Promise.all(ids.map(id =>
      api(`${endpointBase}/${id}`, { method: 'PUT', body: JSON.stringify(body) }).catch(console.error)
    ))
    await _post(ids)
  }

  // PUT con callback que recibe cada ID y devuelve el body (útil cuando necesita data del item)
  async function bulkPutWith(buildBody) {
    const ids = [...selectedIds.value]
    await Promise.all(ids.map(async id => {
      const body = await buildBody(id)
      if (body === null) return
      return api(`${endpointBase}/${id}`, { method: 'PUT', body: JSON.stringify(body) }).catch(console.error)
    }))
    await _post(ids)
  }

  async function bulkDelete() {
    const ids = [...selectedIds.value]
    await Promise.all(ids.map(id =>
      api(`${endpointBase}/${id}`, { method: 'DELETE' }).catch(console.error)
    ))
    await _post(ids)
  }

  async function _post(ids) {
    selectedIds.value = []
    await onAfter(ids)
  }

  // ── Listeners globales: Escape y click-fuera ──
  function _onKeyDown(e) {
    if (e.key === 'Escape' && selectedIds.value.length > 0) clear()
  }
  function _onDocClick(e) {
    if (!selectedIds.value.length) return
    for (const sel of ignoreSelectors) {
      if (e.target.closest(sel)) return
    }
    clear()
  }

  onMounted(() => {
    window.addEventListener('keydown', _onKeyDown)
    document.addEventListener('click', _onDocClick, true)
  })
  onUnmounted(() => {
    window.removeEventListener('keydown', _onKeyDown)
    document.removeEventListener('click', _onDocClick, true)
  })

  return {
    selectedIds,
    toggle,
    add,
    clear,
    isSelected,
    bulkPut,
    bulkPutWith,
    bulkDelete,
  }
}
