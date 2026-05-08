/**
 * Helper único para convertir artículos de /api/articulos al shape que
 * espera el Combobox (value/label/subtitle/badge), reusable en todas las
 * vistas que muestran selector de artículo (solicitudes, recetas, OPs).
 *
 * Regla 5S: una operación = una función. Si necesitás una variante,
 * pasá flags como argumento. NUNCA crear un map paralelo en otra página.
 */
export function articuloToOption(a) {
  const stock = (a.stock ?? '') !== '' ? a.stock : '?'
  const unidad = a.unidad ? ' ' + a.unidad : ''
  return {
    value: a.cod,
    label: `${a.cod} · ${a.nombre}`,
    subtitle: `Stock: ${stock}${unidad}`,
    badge: a.tipo,
    // campos extra que distintas pantallas usan al seleccionar
    nombre: a.nombre,
    tipo: a.tipo,
    grupo_producto: a.grupo_producto || '',
    costo_manual: a.costo_manual || 0,
    stock: a.stock,
    unidad: a.unidad,
  }
}
