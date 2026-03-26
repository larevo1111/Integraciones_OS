# Plan: Diseño meta-chips fila + cronómetro compacto panel

**Estado**: ✅ APROBADO por Santi (sesión 2026-03-17)

## Objetivo

### A) Fila de tarea — meta chips TickTick-style
```
[○][●] Título ................. [● Ventas] [Mañana] [1h30] [📁 alirio] [↳]
                                  cat chip   fecha    dur    proy chip   sub
```
- Cada dato = micro-chip de 16px con border-radius 3px
- Categoría: dot + nombre truncado, fondo rgba(color, 0.12), texto del color
- Fecha: sin fondo, texto gris (rojo si vencida)
- Duración: sin fondo, texto secondary, solo si tiempo_real_min > 0
- Proyecto: dot + nombre truncado, fondo rgba(color, 0.10)
- ↳ botón: icono `subdirectory_arrow_right` 11px, siempre visible opacity:0.3, accent en hover
- Quitar: cat-dot izquierdo NO (lo mantenemos como marcador de color rápido)
- Quitar: hover ref de Vue (el ↳ es siempre visible con CSS)

### B) Cronómetro panel — inline compact
```
Cronómetro   [●][▶] --:--       ← pulsante + play/pause, 11px mono
```
- Botón: círculo 22px, solo icono play_arrow/pause 12px, verde cuando activo
- Tiempo: 11px monospace inline, gris si parado, verde accent si corriendo
- Sin texto "Iniciar"/"Detener", sin icono timer grande
- Pausa = llama a /detener (guarda el segmento)

### C) Tiempos real/estimado — una sola field-row
```
Tiempo       Real [0]h [0]m  |  Est [1]h [30]m
```
- Inputs 32px ancho x 20px alto, font 10px
- Labels "Real"/"Est" en 9px uppercase
- Separador | sutil
- Todo en una sola línea como los demás campos

## Checklist

- [x] 1. TareaItem.vue — chips + hexAlpha helper + ↳ button
- [x] 2. Cronometro.vue — rewrite completo (crono-inline)
- [x] 3. TareaPanel.vue — reemplazar tiempos-section por 2 field-rows + CSS scoped
- [x] 4. app.scss — meta-chip CSS + crono-inline CSS + limpiar obsoletos
- [x] 5. Build + deploy + commit

## Tareas para Antigravity (QA visual)
- [ ] Screenshot fila con chips: cat, fecha, proyecto
- [ ] Screenshot cronómetro antes de iniciar y después de iniciar
- [ ] Screenshot sección tiempos en panel
- [ ] Verificar en mobile (320px viewport) que chips no desbordan
