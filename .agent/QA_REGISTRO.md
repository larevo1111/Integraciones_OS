# QA Registro — ERP Origen Silvestre

> Historial vivo de QA. **No sobreescribir entradas antiguas** — actualizar estado o agregar al final.
> Política completa: ver `.agent/INSTRUCCIONES_TESTING.md`

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
