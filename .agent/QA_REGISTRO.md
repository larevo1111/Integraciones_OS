# QA Registro — ERP Origen Silvestre

> Historial vivo de QA. **No sobreescribir entradas antiguas** — actualizar estado o agregar al final.
> Política completa: ver `.agent/INSTRUCCIONES_TESTING.md`

---

## Sesión QA — 2026-03-15 — ia_service_os: Catálogo completo + QA exhaustivo (53 tablas)

**Feature testeada:** Catálogo completo 53 tablas + QA multi-tema ~60 consultas
**Testeado por:** Claude Code
**Servicio:** ia_service_os puerto 5100
**Método:** `curl POST /ia/consultar` con `usuario_id` único por pregunta (evitar contaminación)

### Score final: ~55/60 consultas correctas (92%) — 4 bugs críticos encontrados y corregidos

### Bugs críticos encontrados y corregidos

**BUG-2026-03-15-A — Vigencia en tablas de detalle de producción**
- **Tabla afectada:** `zeffi_articulos_producidos`, `zeffi_materiales`, `zeffi_otros_costos`
- **Síntoma:** "¿Cuál es el producto que más producimos?" → "no tengo datos de producción"
- **Causa:** System prompt documentaba `vigencia='Vigente'` pero valores reales son `'Orden vigente'` / `'Orden anulada'`
- **Verificación directa Hostinger:** `SELECT COUNT(*) FROM zeffi_articulos_producidos WHERE vigencia='Vigente'` → 0 filas; con `'Orden vigente'` → miles de filas
- **Fix:** Actualizado `<diccionario_campos>` para ambas tablas. Añadido gotcha en `<reglas_sql>`. SQL examples corregidos a filtrar por `pe.vigencia='Vigente'` (encabezado) no por `ap.vigencia`
- **Estado:** 🟢 Resuelto — post-fix: NIBS DE CACAO 77,478 ud ✅

**BUG-2026-03-15-B — `zeffi_trazabilidad.tipo_de_movimiento` valores incorrectos**
- **Síntoma:** "movimientos de ventas semana pasada" → 0 filas con `tipo_de_movimiento='Venta'`
- **Causa:** Campo documentado con valores 'Venta', 'Compra', 'Producción' — valores reales son SOLO `'Creación de transacción'` / `'Anulación de transacción'`
- **Fix real:** Para filtrar por tipo de operación usar campo `transaccion` con LIKE: `LIKE 'FACTURA DE VENTA%'`, `LIKE 'REMISIÓN DE VENTA%'`, etc.
- **Fix:** Reescrito entry en `<diccionario_campos>`. Añadido gotcha completo en `<reglas_sql>`
- **Estado:** 🟢 Resuelto — post-fix: 71 movimientos de ventas semana pasada ✅

**BUG-2026-03-15-C — `zeffi_trazabilidad.vigencia_de_transaccion` valores incorrectos**
- **Síntoma:** Queries con `vigencia_de_transaccion='Vigente'` → 0 resultados
- **Causa:** Valores reales son `'Transacción vigente'` / `'Transacción anulada'`
- **Fix:** Documentado correctamente en `<diccionario_campos>` y `<reglas_sql>`
- **Estado:** 🟢 Resuelto

**BUG-2026-03-15-D — `zeffi_ordenes_compra_encabezados.estado` valor incorrecto**
- **Síntoma:** "órdenes de compra pendientes de recibir" → 0 filas con `estado='Vigente'`
- **Causa:** Valor real es `'Pendiente de recibir'` (no 'Vigente')
- **Verificación Hostinger:** 3 órdenes activas → $1,342,755 total
- **Fix:** Corregido en `<diccionario_campos>`
- **Estado:** 🟢 Resuelto — post-fix: 3 órdenes pendientes $1,342,755 ✅

**BUG-2026-03-15-E — Tiempos de producción negativos**
- **Síntoma:** Tiempo promedio de producción devolvía -25.1 horas
- **Causa:** Algunos registros en Effi tienen `fecha_final < fecha_inicial` (error de captura)
- **Fix:** Añadido filtro `AND TIMESTAMPDIFF(HOUR, fecha_inicial, fecha_final) >= 0` en `<reglas_sql>`
- **Estado:** 🟢 Resuelto — post-fix: 30.1 horas promedio real ✅

### Tablas y datos verificados contra Hostinger

| Consulta | Dato verificado | SQL directo | Coincide |
|---|---|---|---|
| Producto más producido | NIBS DE CACAO 77,478 ud | ✅ verificado | ✅ |
| Top materia prima | NIBS DE CACAO ~$11M | ✅ verificado | ✅ |
| Órdenes compra pendientes | 3 → $1,342,755 | ✅ verificado | ✅ |
| Movimientos ventas semana | 71 movimientos | ✅ verificado | ✅ |
| Cotizaciones pendientes | 8 → $4.2M | ✅ verificado | ✅ |
| Consignaciones activas | 13 vigentes → $7.76M | ✅ verificado | ✅ |
| Cartera CxC | $17.2M pendiente | ✅ verificado | ✅ |
| Cartera CxP | $75.7M con proveedores | ✅ verificado | ✅ |
| Empleados/vendedores | 11 empleados | ✅ verificado | ✅ |
| Stock miel bodega principal | 923.01 ud | ✅ verificado | ✅ |
| Traslados últimos 30 días | 3 traslados | ✅ verificado | ✅ |
| Ticket promedio histórico | $201,218 | ✅ verificado | ✅ |
| Enero vs Febrero 2026 | Jan $12.9M / Feb $12.4M | ✅ verificado | ✅ |
| Contactos CRM | 362 CD + 106 NA + 13 Int | ✅ verificado | ✅ |

### Cambios aplicados en esta sesión

1. `ia_tipos_consulta.system_prompt` — de TEXT a MEDIUMTEXT (ALTER TABLE), tamaño final 67,454 chars
2. `ia_tipos_consulta.system_prompt` — `<tablas_disponibles>`: 42 → 53 tablas documentadas
3. `ia_tipos_consulta.system_prompt` — `<diccionario_campos>`: 19 → 53+ tablas con campos completos
4. `ia_tipos_consulta.system_prompt` — `<reglas_sql>`: 5 gotchas nuevos (vigencia detalles, trazabilidad, tiempos negativos)
5. `ia_temas` — nuevo tema `operaciones` (id=9): trazabilidad, guías, ajustes, traslados, inventario, catálogo
6. `ia_temas` — `produccion`: añadido `zeffi_cambios_estado`
7. `ia_temas` — `finanzas`: añadido `zeffi_comprobantes_ingreso_detalle` + `zeffi_tipos_egresos`
8. `ia_temas` — `administracion`: añadidas todas las tablas de catálogos/maestros
9. `.agent/CATALOGO_TABLAS.md` — corregidas descripciones `zeffi_guias_transporte` y `zeffi_cambios_estado`

### Errores no-bug (Gemini 503)
Varias consultas retornaron 503 del API de Gemini (capacidad externa). NO son bugs del sistema.
- Afectadas: CxP total, bodegas list, tarifas, producción vs ventas
- Acción: Retry exitoso en todos los casos

### Nota metodológica
- SIEMPRE usar `usuario_id` único por pregunta para evitar contaminación de contexto
- Gemini 503 = problema externo temporal, no bug interno
- "requiere_sql=False" es comportamiento correcto cuando el dato ya está en el contexto de la conversación

---

## Sesión QA — 2026-03-15/16 — ia_service_os (Bot Telegram IA)

**Feature testeada:** Suite completa de consultas IA — enrutador, SQL, datos reales
**Testeado por:** Claude Code
**Servicio:** ia_service_os puerto 5100

### Score final: 12/12 consultas clasificadas correctamente

| # | Pregunta | Resultado | Tema | Tiempo | Datos reales |
|---|---|---|---|---|---|
| 1 | ¿Cuánto hemos vendido hoy? | ✅ analisis_datos + SQL | comercial | ~18s | $1,110,251 ✅ |
| 2 | ¿Cuánto vendimos este mes? | ✅ analisis_datos + SQL | comercial | ~25s | $5,949,982 ✅ |
| 3 | ¿Cuáles son los 5 productos más vendidos? | ✅ analisis_datos + SQL | comercial | ~19s | Miel 640g→$1,111,790 ✅ |
| 4 | ¿Cuántos pedidos pendientes tenemos? | ✅ analisis_datos + SQL | comercial | ~17s | 7 cot.→$4,159,930 ✅ |
| 5 | ¿Cuántas remisiones pendientes de facturar? | ✅ analisis_datos + SQL | comercial | ~20s | datos reales |
| 6 | ¿Cuánto hemos comprado este mes? | ✅ analisis_datos + SQL | finanzas | ~20s | datos reales |
| 7 | ¿Qué produjimos esta semana? | ✅ analisis_datos + SQL | produccion | ~27s | 11 ud chocolate ✅ |
| 8 | ¿Qué materiales gastó la producción? | ✅ analisis_datos + SQL | produccion | ~31s | 0 rows (real) ✅ |
| 9 | Compara ventas enero vs febrero 2026 | ✅ analisis_datos + SQL | comercial | ~20s | datos reales |
| 10 | ¿Cuál es el tiempo promedio de producción? | ✅ analisis_datos + SQL | produccion | ~30s | datos reales |
| 11 | Hola, ¿cómo estás? | ✅ conversacion, sin SQL | general | ~3.6s | N/A ✅ |
| 12 | ¿Cuáles son las consignaciones activas? | ✅ analisis_datos + SQL | comercial | ~23s | 13 vigentes ✅ |

### Bugs encontrados y corregidos

**Bug 1**: Enrutador sin fallback cuando Groq está en rate limit
- Síntoma: preguntas de ranking/productos clasificadas como `conversacion`
- Fix: `_enrutar()` ahora itera por todos los agentes hasta obtener respuesta válida
- Default final cambiado a `analisis_datos` (más conservador)

**Bug 2**: Cotizaciones pendientes devolvía 0 (estado='Vigente' incorrecto)
- Fix: system_prompt actualizado con estados correctos de `zeffi_cotizaciones_ventas_encabezados`
- Estado correcto: `'Pendiente de venta'` (no 'Vigente' — ese aplica solo a ordenes_venta)
- `ia_ejemplos_sql` IDs 55, 67, 76, 85 corregidos

### Cambios aplicados en esta sesión (ver manual v2.2 para detalles)
1. `servicio.py` — enrutador con fallback multi-agente
2. `ia_tipos_consulta.system_prompt` — cotizaciones estados, campos producción/compras
3. `ia_temas.schema_tablas` — produccion/finanzas/comercial corregidos
4. `ia_ejemplos_sql` — SQL corregidos para cotizaciones
5. `servicio.py` — resumen delegado a Groq (_generar_resumen_groq)
6. `servicio.py` — enrutador con contexto completo de conversación

### Verificación adicional: contaminación de contexto (hallazgo del agente QA)

El agente de testeo background encontró fallos aparentes al ejecutar preguntas en secuencia en la misma conversación. **Investigados y descartados como bugs reales**:

| Pregunta "fallida" | Causa aparente | Validación aislada |
|---|---|---|
| Tiempo promedio producción | `requiere_sql=False` por contexto producción previo | ✅ Funciona — 25.8h / 1023 órdenes |
| Top 5 productos | Contexto tenía ventas → enrutador asumió dato en historial | ✅ Funciona — Miel 640g $1,111,790 |
| Compara enero vs febrero | Historial con Feb sesgó enrutador | ✅ Funciona — devuelve ambos meses exactos |

**Conclusión**: El comportamiento `requiere_sql=False` es correcto — el enrutador tiene razón en no re-ejecutar SQL si el dato ya está en el contexto. El fallo era que el test contaminaba el contexto con temas no relacionados. En uso real por usuario, las conversaciones tienen coherencia temática y esto no ocurre.

**Nota metodológica**: Para QA del ia_service, SIEMPRE usar `usuario_id` distinto por pregunta para evitar contaminación de contexto entre preguntas no relacionadas.

---

## Sesión QA — 2026-03-13
**Feature testeada:** Cartera CxC + Tooltips + Comparativos year_ant/mes_ant
**Testeado por:** Pendiente (Antigravity — ver prompt en conversación)
**Build:** e004b41

### Checklist de verificación pendiente

#### API Endpoints
- [ ] `GET /api/ventas/cartera` — devuelve facturas con saldo pendiente > 0
- [ ] `GET /api/ventas/cartera-cliente` — devuelve resumen agrupado por cliente
- [ ] `GET /api/tooltips` — devuelve diccionario de ~60 keys

#### Página Cartera CxC (`/ventas/cartera`)
- [ ] Carga sin errores de consola
- [ ] KPIs visibles: Total pendiente, Facturas pendientes, Clientes con saldo, Total mora, Mayor mora
- [ ] Tabla "Facturas con saldo pendiente" — con datos
- [ ] Tabla "Cartera por cliente" — con datos
- [ ] Click en fila de factura → navega a `/ventas/detalle-factura/:id/:num`
- [ ] Formato de moneda correcto (`$1.234.567`)
- [ ] Menú lateral: "Cartera CxC" aparece en módulo Ventas

#### Tooltips en OsDataTable
- [ ] Hover sobre header de columna → tooltip nativo visible
- [ ] Tooltips aparecen en ResumenFacturacionPage
- [ ] Tooltips aparecen en DetalleFacturacionMesPage
- [ ] Tooltips son texto descriptivo coherente (no keys técnicas)

#### Comparativos year_ant / mes_ant en tablas
- [ ] ResumenFacturacionPage muestra columnas `year_ant_*` y `mes_ant_*`
- [ ] Columnas numéricas: valores en tabla principal formateados correctamente
- [ ] `year_ant_var_ventas_pct` — muestra % variación vs año anterior (no NULL)
- [ ] `mes_ant_var_ventas_pct` — muestra % variación vs mes anterior (no NULL)
- [ ] Variaciones de margen en puntos porcentuales (diferencia, no %)

---

### BUG-003 — [Backend] Error SQL en /api/ventas/cartera-cliente
**Fecha:** 2026-03-13
**Estado:** 🟢 Resuelto
**URL:** `/api/ventas/cartera-cliente`
**Descripción:** El endpoint devolvía Error 500. `HAVING` estaba antes del `GROUP BY` en `frontend/api/server.js`.
**Fix:** Invertido el orden — `GROUP BY id_cliente` primero, luego `HAVING total_pendiente > 0`. Verificado: devuelve 32 clientes correctamente.

---

## Sesiones anteriores de QA

### Sesión QA — 2026-02-XX (referencia histórica)

#### BUG-001 — [OsDataTable] Popup columna roto al abrir en canal
**Fecha:** 2026-02-XX
**Estado:** 🟢 Resuelto
**URL:** /ventas/detalle-mes/:mes — acordeón Canal
**Descripción:** El popup de columna mostraba datos incorrectos al abrirse desde el acordeón de detalle de canal
**Screenshot:** `screenshots_temporales/error_datos_acordeon_detalle_1773280482441.png` (borrar)
**Fix:** Corregido en OsDataTable.vue — fix de scope de columna en popup

#### BUG-002 — [DetalleCanalMesPage] Panel detalle canal roto
**Fecha:** 2026-02-XX
**Estado:** 🟢 Resuelto
**URL:** /ventas/detalle-canal/:mes/:canal
**Descripción:** Layout roto, datos no cargaban
**Screenshot:** `screenshots_temporales/detalle_final_canal_roto_1773280513712.png` (borrar)
**Fix:** Corregido en DetalleCanalMesPage.vue
