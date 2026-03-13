# QA Registro — ERP Origen Silvestre

> Historial vivo de QA. **No sobreescribir entradas antiguas** — actualizar estado o agregar al final.
> Política completa: ver `.agent/INSTRUCCIONES_TESTING.md`

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
