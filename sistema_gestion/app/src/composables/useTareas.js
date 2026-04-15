/**
 * useTareas.js — Función centralizada de creación de tareas (5S)
 * TODAS las creaciones de tareas en la app pasan por aquí.
 */
import { api } from 'src/services/api'

/**
 * Crea una tarea nueva via POST /api/gestion/tareas
 * @param {Object} body - campos de la tarea (titulo, categoria_id, proyecto_id, etc.)
 * @returns {Object} tarea creada
 */
export async function crearTarea(body) {
  const data = await api('/api/gestion/tareas', {
    method: 'POST',
    body: JSON.stringify(body)
  })
  return data.tarea
}

/**
 * Crea una subtarea heredando categoria y proyecto del padre
 * @param {Object} padre - tarea padre (necesita .id, .categoria_id, .proyecto_id)
 * @param {string} titulo
 * @param {Object} extras - campos adicionales opcionales (responsable, responsables, etc.)
 * @returns {Object} subtarea creada
 */
export async function crearSubtarea(padre, titulo, extras = {}) {
  return crearTarea({
    titulo,
    parent_id: padre.id,
    categoria_id: padre.categoria_id,
    proyecto_id: padre.proyecto_id || null,
    ...extras
  })
}

/**
 * Sugiere una categoría por IA dado el título de la tarea
 * @param {string} titulo
 * @returns {Object|null} { categoria_id, categoria_nombre } o null si falla
 */
export async function sugerirCategoria(titulo) {
  if (!titulo || titulo.length < 4) return null
  try {
    const data = await api(`/api/gestion/sugerir-categoria?titulo=${encodeURIComponent(titulo)}`)
    if (data.ok && data.categoria_id) return data
    console.warn('[IA] sugerencia sin resultado:', data)
    return null
  } catch (e) {
    console.error('[IA] sugerencia falló:', e.message)
    return null
  }
}
