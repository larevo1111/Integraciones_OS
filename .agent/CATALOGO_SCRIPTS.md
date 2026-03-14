# Catálogo de Scripts — Integraciones_OS

> Referencia completa para agentes y operadores.
> **Actualizar este archivo cada vez que se cree, modifique o elimine un script.**

---

## Ubicación base
```
/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/
```
Alias activos (symlinks en el host):
- `/repo/scripts` → misma carpeta
- `/scripts` → misma carpeta
- `/exports` → `/home/osserver/playwright/exports/`

---

## Protocolo — Cómo documentar un script nuevo

Al crear cualquier script nuevo, agregar una entrada en la sección correspondiente con:

```
### nombre_del_script.ext
- **Propósito**: qué hace en una línea
- **Tipo**: [export | import | orquestador | utilidad | test]
- **Ejecución manual**: comando exacto para correrlo
- **Salida**: qué archivos genera o qué imprime
- **Tabla(s) MariaDB**: tabla(s) que crea/modifica (si aplica)
- **Dependencias**: otros scripts o archivos que necesita
- **Notas**: comportamientos especiales, errores conocidos, límites
```

---

## 1. Orquestadores y Scripts Maestros

### orquestador.py
- **Propósito**: Ejecuta el pipeline completo Effi → MariaDB con notificaciones
- **Tipo**: orquestador
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/orquestador.py
  python3 scripts/orquestador.py --forzar   # ignora horario operativo
  ```
- **Salida**: logs en stdout + `logs/pipeline.log`; email siempre; Telegram solo en error
- **Tabla(s) MariaDB**: ninguna directamente (delega a import_all.js y los 8 scripts calcular_resumen_*)
- **Dependencias**: `export_all.sh`, `import_all.js`, todos los `calcular_resumen_ventas_*.py` (pasos 3a/3b/3c/3d/4a/4b/4c/4d), `sync_catalogo_articulos.py`, `sync_hostinger.py`, `sync_espocrm_marketing.py`, `sync_espocrm_contactos.py`, `sync_espocrm_to_hostinger.py`, `generar_plantilla_import_effi.py`, `import_clientes_effi.js`, `scripts/.env`
- **Horario operativo**: Lun–Sáb, 06:00–20:00 (systemd timer cada 2h)
- **Systemd**:
  ```bash
  systemctl status effi-pipeline.timer     # estado y próxima ejecución
  journalctl -u effi-pipeline -f           # logs en tiempo real
  systemctl start effi-pipeline.service    # ejecutar ahora
  ```
- **Notas**: `--forzar` bypasea el horario (útil para pruebas). Credenciales en `scripts/.env`.

---

### export_all.sh
- **Propósito**: Corre los 26 scripts de exportación Effi en secuencia
- **Tipo**: orquestador
- **Ejecución manual**:
  ```bash
  bash /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/export_all.sh
  ```
- **Salida**: stdout con progreso por script + línea `RESULTADO: ✅ N ok ❌ N errores`
- **Dependencias**: los 26 `export_*.js`, Node.js en PATH
- **Notas**: reintento automático en caso de fallo (espera 15s y vuelve a intentar). Pausa 8s entre scripts para no sobrecargar Effi.

---

### import_all.js
- **Propósito**: Lee todos los `.xlsx` exportados y los importa a MariaDB `effi_data`
- **Tipo**: import
- **Ejecución manual**:
  ```bash
  node /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/import_all.js
  ```
- **Salida**: stdout con progreso por tabla + línea `✅ N tablas importadas ❌ N errores`
- **Tabla(s) MariaDB**: todas las de `effi_data` (39 tablas). Estrategia: TRUNCATE + INSERT
- **Dependencias**: `exports/` con archivos `.xlsx` generados por los export scripts
- **Notas**: detecta automáticamente HTML ISO-8859 disfrazado de `.xlsx` (mayoría de Effi) vs Excel real. Ignora tablas en `SKIP_TABLES`. Todas las columnas son TEXT + `_pk` AUTO_INCREMENT.

---

### calcular_resumen_ventas.py
- **Propósito**: Calcula y actualiza la tabla resumen mensual de ventas `resumen_ventas_facturas_mes`
- **Tipo**: import / analítica
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_facturas_mes — N meses actualizados`
- **Tabla(s) MariaDB**: `resumen_ventas_facturas_mes` (crea si no existe, UPSERT por mes)
- **Dependencias**: tablas `zeffi_facturas_venta_encabezados`, `zeffi_facturas_venta_detalle`, `zeffi_ordenes_venta_encabezados`; driver `mysql-connector-python`
- **Columnas clave** (38 total):
  - `fin_*`: financiero (ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, ventas_netas, devoluciones, ingresos_netos)
  - `cto_*`: costo y utilidad (costo_manual, utilidad_bruta, margen_pct)
  - `vol_*`: volumen (unidades, num_facturas, ticket_promedio)
  - `cli_*`: clientes (activos, nuevos, ventas_por_cliente)
  - `car_*`: cartera (saldo pendiente de cobro)
  - `cat_*`: catálogo (num_referencias, ventas_por_referencia, num_canales)
  - `con_*`: consignación (total OVs creadas ese mes, excluye errores operativos ≤1 día)
  - `top_*`: tops del mes (canal, cliente, producto)
  - `pry_*`: proyección lineal al cierre del mes — **solo mes en curso, NULL para meses cerrados**
  - `ant_*`: comparativo año anterior (ventas_netas, var_pct, consignacion, var_pct)
- **Notas**: todos los campos numéricos de Effi usan coma decimal; el script castea con `REPLACE(field, ',', '.')`. `vigencia` no existe en encabezados (export solo vigentes). Consignación excluye OVs anuladas en ≤1 día sin keywords de liquidación. Campos `_pct` almacenados como decimal 0–1 (no multiplicados por 100).

### calcular_resumen_ventas_canal.py
- **Propósito**: Calcula y actualiza `resumen_ventas_facturas_canal_mes` — resumen mensual de ventas agrupado por canal de marketing
- **Tipo**: import / analítica (paso 3b del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_canal.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_facturas_canal_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_facturas_canal_mes` (PK: `mes, canal`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_facturas_venta_detalle`, `zeffi_ordenes_venta_encabezados`; driver `mysql-connector-python`
- **Columnas clave** (32 total, PK compuesto: mes + canal):
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, **fin_pct_del_mes** (% participación canal en total mes)
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_facturas (COUNT DISTINCT id_numeracion), ticket_promedio
  - `cli_*`: clientes_activos, clientes_nuevos, vtas_por_cliente
  - `cat_*`: num_referencias
  - `top_*`: top_cliente, top_cliente_ventas, top_producto_cod/nombre/ventas
  - `con_*`: **con_consignacion_pp** (OVs atribuidas al canal via id_cliente → canal histórico)
  - `pry_*`: proyección lineal — solo mes en curso, NULL para meses cerrados
  - `ant_*`: ventas_netas, var_pct, **ant_consignacion_pp**, **ant_var_consignacion_pct**
- **Diferencias vs `resumen_ventas_facturas_mes`**: NO incluye cartera (`car_`), devoluciones. AGREGA `fin_pct_del_mes` y `con_consignacion_pp`.
- **Notas**:
  - Campo número de factura en detalle: `id_numeracion` (no `numero_factura`).
  - Canales vacíos/NULL se normalizan a `'Sin canal'`.
  - Consignaciones atribuidas por canal via mapping id_cliente → canal más frecuente en historial de facturas (Opción A). Filas con solo consignaciones (sin facturas ese mes) se crean con valores de facturas en 0.
  - SUM(canal_mes) vs resumen_mes: diff = 0.00 exacto (verificado 2026-03).

### calcular_resumen_ventas_cliente.py
- **Propósito**: Calcula y actualiza `resumen_ventas_facturas_cliente_mes` — resumen mensual de ventas por cliente
- **Tipo**: import / analítica (paso 3c del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_cliente.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_facturas_cliente_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_facturas_cliente_mes` (PK: `mes, id_cliente`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_facturas_venta_detalle`, `zeffi_clientes`, `zeffi_ordenes_venta_encabezados`; driver `mysql-connector-python`
- **Columnas clave** (34 total, PK compuesto: mes + id_cliente):
  - Dimensiones: `cliente`, `ciudad`, `departamento`, `canal` (tipo_de_marketing del maestro), `vendedor`
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_facturas, ticket_promedio
  - `cat_*`: num_referencias
  - `top_*`: top_producto_cod/nombre/ventas
  - `con_*`: con_consignacion_pp (OVs directamente por id_cliente)
  - `cli_*`: cli_es_nuevo (1 si primera factura histórica del cliente)
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct, ant_consignacion_pp, ant_var_consignacion_pct
- **Notas**:
  - `canal` viene del maestro `zeffi_clientes.tipo_de_marketing` (JOIN por numero_de_identificacion ↔ id_cliente). Si no hay coincidencia: `'Sin canal'`.
  - Consignaciones directas por id_cliente (sin necesidad de mapping de canal).
  - SUM(cliente_mes) vs resumen_mes: diff ≤ 0.26 (solo redondeo DECIMAL).

### calcular_resumen_ventas_producto.py
- **Propósito**: Calcula y actualiza `resumen_ventas_facturas_producto_mes` — resumen mensual de ventas por referencia de producto
- **Tipo**: import / analítica (paso 3d del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_producto.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_facturas_producto_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_facturas_producto_mes` (PK: `mes, cod_articulo`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_facturas_venta_detalle`; driver `mysql-connector-python`
- **Columnas clave** (30 total, PK compuesto: mes + cod_articulo):
  - Dimensiones: `nombre` (descripcion_articulo), `categoria` (categoria_articulo), `marca` (marca_articulo)
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, **fin_pct_del_mes**
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_facturas (facturas con este producto), precio_unitario_prom
  - `cli_*`: clientes_activos (clientes distintos que compraron el producto)
  - `top_*`: top_cliente/ventas, top_canal/ventas
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct, **ant_unidades**, **ant_var_unidades_pct** (variación unidades YoY)
- **Notas**:
  - `cod_articulo` en facturas = `id` en `zeffi_inventario` (tasa de match 97%).
  - Dimensiones vienen directo del detalle (no requiere JOIN con inventario).
  - NO incluye consignaciones (OVs no tienen producto por factura de consignación global).
  - SUM(producto_mes) vs resumen_mes: diff ≤ 0.25 (solo redondeo DECIMAL).

### calcular_resumen_ventas_remisiones_canal_mes.py
- **Propósito**: Calcula y actualiza `resumen_ventas_remisiones_canal_mes` — resumen mensual de remisiones agrupado por canal de marketing
- **Tipo**: import / analítica (paso 4b del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_remisiones_canal_mes.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_remisiones_canal_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_remisiones_canal_mes` (PK: `mes, canal`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_remisiones_venta_encabezados`, `zeffi_remisiones_venta_detalle`; driver `mysql-connector-python`
- **Columnas clave** (32 total, PK compuesto: mes + canal):
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, ventas_netas, **fin_pct_del_mes**
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_remisiones, ticket_promedio
  - `cli_*`: clientes_activos, clientes_nuevos, vtas_por_cliente
  - `cat_*`: num_referencias
  - `top_*`: top_cliente/ventas, top_producto_cod/nombre/ventas
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct
- **Notas**:
  - Canal de `tipo_de_markting` (typo sin 'e') en encabezados; NULL/vacío → `'Sin canal'`.
  - Financiero del encabezado (cn() con REPLACE coma). Volumen/costo del detalle.
  - `pct()` clamp aplicado a todos los `_pct` (previene overflow en remisiones tipo consumo interno con subtotal=0).
  - 351 filas (29 meses × ~12 canales). diff vs fuente = 0.00.

### calcular_resumen_ventas_remisiones_cliente_mes.py
- **Propósito**: Calcula y actualiza `resumen_ventas_remisiones_cliente_mes` — resumen mensual de remisiones por cliente
- **Tipo**: import / analítica (paso 4c del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_remisiones_cliente_mes.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_remisiones_cliente_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_remisiones_cliente_mes` (PK: `mes, id_cliente`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_remisiones_venta_encabezados`, `zeffi_remisiones_venta_detalle`; driver `mysql-connector-python`
- **Columnas clave** (34 total, PK compuesto: mes + id_cliente):
  - Dimensiones: `cliente`, `ciudad`, `departamento`, `canal` (canal dominante por subtotal en ese mes), `vendedor`
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, ventas_netas
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_remisiones, ticket_promedio
  - `cat_*`: num_referencias
  - `top_*`: top_producto_cod/nombre/ventas
  - `rem_*`: rem_pendientes, rem_facturadas, rem_pct_facturadas (estado actual por cliente-mes)
  - `cli_*`: cli_es_nuevo (1 si es la primera remisión histórica del cliente)
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct
- **Notas**:
  - `canal` = canal con mayor subtotal del cliente en ese mes (dinámico, no del maestro).
  - `cli_es_nuevo` basado en primera remisión histórica (mínimo fecha por id_cliente en encabezados).
  - 1141 filas. diff vs fuente = 0.00.

### calcular_resumen_ventas_remisiones_producto_mes.py
- **Propósito**: Calcula y actualiza `resumen_ventas_remisiones_producto_mes` — resumen mensual de remisiones por referencia de producto
- **Tipo**: import / analítica (paso 4d del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_remisiones_producto_mes.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_remisiones_producto_mes — N filas actualizadas`
- **Tabla(s) MariaDB**: `resumen_ventas_remisiones_producto_mes` (PK: `mes, cod_articulo`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_remisiones_venta_encabezados`, `zeffi_remisiones_venta_detalle`; driver `mysql-connector-python`
- **Columnas clave** (30 total, PK compuesto: mes + cod_articulo):
  - Dimensiones: `nombre`, `categoria`, `marca`
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, ventas_netas, **fin_pct_del_mes**
  - `cto_*`: costo_total, utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, num_remisiones, precio_unitario_prom
  - `cli_*`: clientes_activos (clientes distintos con este producto)
  - `top_*`: top_cliente/ventas, top_canal/ventas
  - `cat_canal_principal`: canal con más ventas de ese producto ese mes
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct, ant_unidades, ant_var_unidades_pct
- **Notas**:
  - Todo el financiero/costo desde detalle JOIN encabezados (encabezados aporta canal y fecha).
  - 1228 filas. diff vs fuente = 0.00.

### sync_catalogo_articulos.py — Paso 4e
- **Propósito**: Detecta artículos vendidos que no están en `catalogo_articulos`, los agrega y asigna `grupo_producto` automáticamente (regex determinístico primero; Groq llama-3.1-8b-instant si quedan sin resolver)
- **Tipo**: import / analítica (paso 4e del pipeline — corre antes de sync_hostinger)
- **Ejecución manual**:
  ```bash
  python3 scripts/sync_catalogo_articulos.py            # modo normal
  python3 scripts/sync_catalogo_articulos.py --dry-run  # solo muestra novedades sin escribir
  ```
- **Salida**: stdout con número de artículos nuevos detectados y grupos asignados
- **Tabla(s) MariaDB**: `effi_data.catalogo_articulos` (INSERT para nuevos, UPDATE para grupos pendientes)
- **Dependencias**: `zeffi_facturas_venta_detalle` (para detectar cod_articulo vendidos), `scripts/.env` (GROQ_API_KEY — opcional, solo si hay sin resolver)
- **Notas**: Solo actúa sobre artículos SIN `grupo_producto` asignado. El regex cubre los patrones actuales de nomenclatura de OS. Groq solo se llama si hay artículos que el regex no resolvió bien. La tabla `catalogo_articulos` se sincroniza a Hostinger en el paso 5 (sync_hostinger.py).

---

### asignar_grupo_producto.py — Paso 4f + Herramienta manual
- **Propósito**: Asigna `grupo_producto` en `catalogo_articulos` para artículos ya vendidos que aún no tienen grupo. Corre automáticamente en el pipeline (paso 4f) y también es útil como herramienta manual.
- **Tipo**: import / analítica (paso 4f) + utilidad manual
- **Ejecución manual**:
  ```bash
  python3 scripts/asignar_grupo_producto.py            # solo los que faltan (sin grupo)
  python3 scripts/asignar_grupo_producto.py --dry-run  # preview sin escribir
  python3 scripts/asignar_grupo_producto.py --todos    # reasigna todos (útil si cambia el criterio)
  python3 scripts/asignar_grupo_producto.py --groq     # usa Groq para los sin grupo
  ```
- **Salida**: stdout con artículos procesados y grupos asignados
- **Tabla(s) MariaDB**: `effi_data.catalogo_articulos` (UPDATE grupo_producto)
- **Dependencias**: `scripts/.env` (GROQ_API_KEY — opcional, solo con --groq)
- **Notas**: En el pipeline (paso 4f) se ejecuta con `--groq`. Si no hay artículos sin grupo, termina en milisegundos (no-op). Si la GROQ_API_KEY no está configurada, el paso de Groq se salta sin error. La diferencia con `sync_catalogo_articulos.py` (paso 4e): ese script detecta e inserta artículos NUEVOS; este script asigna grupo a artículos ya existentes en el catálogo que quedaron sin grupo (ej. si el regex no los resolvió en una corrida anterior).

---

### calcular_resumen_ventas_remisiones_mes.py
- **Propósito**: Calcula y actualiza `resumen_ventas_remisiones_mes` — resumen mensual de ventas por remisión (paralelo a facturas_mes)
- **Tipo**: import / analítica (paso 4a del pipeline)
- **Ejecución manual**:
  ```bash
  python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/calcular_resumen_ventas_remisiones_mes.py
  ```
- **Salida**: stdout con `✅ resumen_ventas_remisiones_mes — N meses actualizados`
- **Tabla(s) MariaDB**: `resumen_ventas_remisiones_mes` (PK: `mes`; crea si no existe, UPSERT)
- **Dependencias**: `zeffi_remisiones_venta_encabezados`, `zeffi_remisiones_venta_detalle`, `zeffi_devoluciones_venta_encabezados`; driver `mysql-connector-python`
- **Columnas clave** (38 total, PK: mes):
  - `fin_*`: ventas_brutas, descuentos, pct_descuento, ventas_netas_sin_iva, impuestos, ventas_netas, devoluciones, ingresos_netos
  - `cto_*`: costo_total (de detalle), utilidad_bruta, margen_utilidad_pct
  - `vol_*`: unidades_vendidas, **num_remisiones**, ticket_promedio
  - `cli_*`: clientes_activos, clientes_nuevos (primera remisión histórica), vtas_por_cliente
  - `car_*`: saldo (pdte_de_cobro)
  - `cat_*`: num_referencias, vtas_por_referencia, num_canales
  - `rem_*`: **rem_pendientes**, **rem_facturadas**, **rem_pct_facturadas** — conteos actuales de estado
  - `top_*`: top_canal/ventas, top_cliente/ventas, top_producto_cod/nombre/ventas
  - `pry_*`: proyección lineal — solo mes en curso
  - `ant_*`: ventas_netas, var_pct
- **Notas técnicas**:
  - **Filtro de inclusión**: `estado_remision = 'Pendiente de facturar'` OR `observacion_de_anulacion LIKE 'Remisión convertida a factura de venta%'`. Excluye anulaciones reales (348 remisiones).
  - Encabezados: formato coma decimal → `cn()` con REPLACE. Detalle: números planos → `cn_det()` con CAST directo.
  - `fin_ventas_netas_sin_iva = subtotal` (del encabezado, sin IVA). `fin_ventas_netas = total_neto` (incluye IVA).
  - `rem_pct_facturadas` es dinámico — puede aumentar con el tiempo conforme remisiones pendientes se convierten.
  - Canal: `tipo_de_markting` (typo sin 'e') en encabezados; `tipo_de_marketing_cliente` en detalle.
  - 29 meses (2023-11 a 2026-03). diff_total vs fuente = 0.00.

---

## 1b. Scripts EspoCRM (integración bidireccional)

### sync_espocrm_marketing.py — Paso 6b
- **Propósito**: Sincroniza enums dinámicos (tipoDeMarketing, tarifaPrecios, vendedorEffi) y campos custom de Contact en EspoCRM desde Effi
- **Tipo**: utilidad
- **Ejecución manual**: `python3 scripts/sync_espocrm_marketing.py`
- **Salida**: `✅ sync_espocrm_marketing — actualizado: N marketing | N tarifas | N vendedores`
- **Tabla(s)**: entityDefs + i18n + layout en contenedor `espocrm` vía docker cp
- **Notas**: Solo hace rebuild si detecta cambios. Enums fijos hardcodeados: tipoCliente (6 valores), tipoIdentificacion, tipoPersona. Campos bool: enviadoAEffi.

---

### sync_espocrm_contactos.py — Paso 6c
- **Propósito**: Sincroniza clientes vigentes de Effi (zeffi_clientes) → Contact en EspoCRM. Upsert por numero_identificacion.
- **Tipo**: utilidad
- **Ejecución manual**: `python3 scripts/sync_espocrm_contactos.py`
- **Salida**: `✅ sync_espocrm_contactos — N contactos (X nuevos, Y actualizados, Z omitidos)`
- **Tabla(s)**: `contact`, `email_address`, `entity_email_address`, `phone_number`, `entity_phone_number` en espocrm
- **Notas**: Setea fuente='Effi' en todos los contactos importados. Traduce ciudad Effi → formato "Ciudad - Departamento" para campo `ciudad_nombre` (normalización sin tildes + alias: Cali→Santiago De Cali, Cartagena→Cartagena De Indias). Escribe dirección en campo custom `direccion` (NO en address_street nativo). Resuelve vendedor → assigned_user_id via nombre completo.

---

### sync_espocrm_to_hostinger.py — Paso 6d
- **Propósito**: Exporta tabla `contact` de EspoCRM local → `crm_contactos` en Hostinger (u768061575_os_integracion). Para visibilidad en NocoDB.
- **Tipo**: utilidad
- **Ejecución manual**: `python3 scripts/sync_espocrm_to_hostinger.py`
- **Salida**: `✅ sync_espocrm_to_hostinger — N contactos → crm_contactos en Hostinger`
- **Tabla(s) Hostinger**: `crm_contactos` (DROP+CREATE+INSERT en lotes de 500)
- **Conexión**: SSH tunnel a Hostinger (mismo mecanismo que sync_hostinger.py)
- **Campos**: id, nombre_completo, first/last_name, numero_identificacion, tipo_identificacion, tipo_persona, email, telefono, direccion, direccion_linea2, ciudad_nombre, tipo_de_marketing, tipo_cliente, tarifa_precios, forma_pago, vendedor_effi, fuente, enviado_a_effi, descripcion

---

### bootstrap_ciudades_espocrm.py — Ejecución única
- **Propósito**: Crea la entidad Ciudad en EspoCRM y la puebla con 12,237 ciudades de Colombia, Ecuador, Rep. Dominicana y Guatemala (desde plantilla_importacion_cliente.xlsx)
- **Tipo**: bootstrap (solo correr una vez)
- **Ejecución manual**: `python3 scripts/bootstrap_ciudades_espocrm.py`
- **Salida**: `✅ bootstrap_ciudades_espocrm — completo`
- **Tabla(s)**: `ciudad` en espocrm (creada via rebuild.php). Agrega `ciudad_id` a `contact`.
- **Notas**: Idempotente (INSERT IGNORE por id_effi UNIQUE). Ya se ejecutó — NO volver a correr salvo que se limpie la BD.

---

### generar_plantilla_import_effi.py — Paso 7a
- **Propósito**: Lee contactos EspoCRM con fuente='CRM' y enviado_a_effi=0 → genera XLSX con formato de plantilla de importación de Effi
- **Tipo**: utilidad
- **Ejecución manual**:
  ```bash
  python3 scripts/generar_plantilla_import_effi.py            # solo pendientes
  python3 scripts/generar_plantilla_import_effi.py --todos     # re-exportar todos
  python3 scripts/generar_plantilla_import_effi.py --no-marcar # sin marcar enviado
  ```
- **Salida**: `/tmp/import_clientes_effi_<fecha>.xlsx` con 36 columnas
- **Mapeos**: tipo_identificacion→id_effi (hardcoded), ciudad_nombre→código DANE via codigos_ciudades_dane, tarifa→id (zeffi_tarifas_precios), marketing→id (zeffi_tipos_marketing), tipo_persona→1/2, regimen→4/5, email_responsable fijo, sucursal=1, moneda=COP. Dirección = concatenación de `direccion` + `direccion_linea2`.
- **Notas**: Tras generar, marca contactos como enviado_a_effi=1 (a menos que --no-marcar). Si no hay pendientes, imprime "sin contactos CRM pendientes" y termina (exit 0, sin XLSX).

---

### import_clientes_effi.js — Paso 7b
- **Propósito**: Sube el XLSX generado por `generar_plantilla_import_effi.py` a Effi vía Playwright (importación masiva de contactos)
- **Tipo**: utilidad
- **Ejecución manual**:
  ```bash
  node scripts/import_clientes_effi.js                          # usa /tmp/import_clientes_effi_<hoy>.xlsx
  node scripts/import_clientes_effi.js /ruta/al/archivo.xlsx    # ruta explícita
  ```
- **Salida**: screenshot en `/exports/import_effi_resultado_<fecha>.png`; `✅ import_clientes_effi — importación completada`
- **Flujo Playwright**: Navega a `/app/tercero/contacto` → click "Crear o modificar contactos masivamente" → `input[name="userfile"]` first → `#btn_submit` → espera 5s → screenshot
- **Dependencias**: `session.js`, archivo XLSX en `/tmp/`, Effi accesible
- **Notas**: Se ejecuta automáticamente en el pipeline (paso 7b) solo si el paso 7a generó un XLSX con contactos pendientes. Si no hay pendientes, se omite sin error.

---

## 2. Infraestructura / Utilidades

### session.js
- **Propósito**: Gestiona la sesión autenticada de Playwright contra Effi
- **Tipo**: utilidad
- **Ejecución manual**: no se ejecuta directamente, es `require('./session')`
- **Salida**: `{ browser, context, page }` ya autenticado
- **Dependencias**: Playwright, `/scripts/session.json` (estado de sesión guardado)
- **Notas**: reutiliza sesión si `session.json` existe y está válida. Si la sesión expiró, hace login automático con `ORIGENSILVESTRE.COL@GMAIL.COM`. Guarda nueva sesión en `/scripts/session.json`.

---

### utils.js
- **Propósito**: Funciones helper compartidas entre scripts
- **Tipo**: utilidad
- **Ejecución manual**: no se ejecuta directamente, es `require('./utils')`
- **Funciones**:
  - `contarFilas(filePath)` → número de filas de datos en un `.xlsx` (excluye cabecera)
- **Dependencias**: librería `xlsx`

---

### test.js
- **Propósito**: Script de prueba/diagnóstico de conexión o sesión
- **Tipo**: test
- **Ejecución manual**:
  ```bash
  node /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/test.js
  ```

---

## 3. Scripts de Exportación Effi (26 scripts)

> **Patrón común**: cada script abre Effi con Playwright, descarga el Excel del módulo,
> lo guarda en `/exports/<modulo>/`, imprime `✅ Exportado: /ruta/archivo.xlsx (N filas)`.
> En caso de error: screenshot en `/exports/error_<modulo>_<timestamp>.png` + `exit 1`.

### export_clientes.js
- **Módulo Effi**: Terceros → Clientes
- **Archivos generados**: `/exports/clientes/clientes_<fecha>.xlsx`
- **Tabla MariaDB**: `clientes`
- **Tipo archivo**: HTML disfrazado de xlsx (ISO-8859)

### export_proveedores.js
- **Módulo Effi**: Terceros → Proveedores
- **Archivos generados**: `/exports/proveedores/proveedores_<fecha>.xlsx`
- **Tabla MariaDB**: `proveedores`
- **Tipo archivo**: HTML disfrazado de xlsx (ISO-8859)

### export_bodegas.js
- **Módulo Effi**: Inventario → Bodegas
- **Archivos generados**: `/exports/bodegas/bodegas_<fecha>.xlsx`
- **Tabla MariaDB**: `bodegas`
- **Tipo archivo**: HTML disfrazado de xlsx (ISO-8859)

### export_inventario.js
- **Módulo Effi**: Inventario → Artículos
- **Archivos generados**: `/exports/inventario/inventario_<fecha>.xlsx`
- **Tabla MariaDB**: `inventario`
- **Tipo archivo**: HTML disfrazado de xlsx (ISO-8859)

### export_trazabilidad.js
- **Módulo Effi**: Inventario → Trazabilidad
- **Archivos generados**: `/exports/trazabilidad/trazabilidad_<fecha>.xlsx`
- **Tabla MariaDB**: `trazabilidad`

### export_ajustes_inventario.js
- **Módulo Effi**: Inventario → Ajustes
- **Archivos generados**: `/exports/ajustes_inventario/ajustes_inventario_<fecha>.xlsx`
- **Tabla MariaDB**: `ajustes_inventario`

### export_traslados_inventario.js
- **Módulo Effi**: Inventario → Traslados
- **Archivos generados**: `/exports/traslados_inventario/traslados_inventario_<fecha>.xlsx`
- **Tabla MariaDB**: `traslados_inventario`

### export_categorias_articulos.js
- **Módulo Effi**: Inventario → Categorías
- **Archivos generados**: `/exports/categorias_articulos/categorias_articulos_<fecha>.xlsx`
- **Tabla MariaDB**: `categorias_articulos`

### export_ordenes_compra.js
- **Módulo Effi**: Compras → Órdenes de compra
- **Archivos generados**: `/exports/ordenes_compra/ordenes_compra_<fecha>.xlsx`
- **Tabla MariaDB**: `ordenes_compra`

### export_facturas_compra.js
- **Módulo Effi**: Compras → Facturas de compra
- **Archivos generados**: `/exports/facturas_compra/facturas_compra_<fecha>.xlsx`
- **Tabla MariaDB**: `facturas_compra`

### export_remisiones_compra.js
- **Módulo Effi**: Compras → Remisiones de compra
- **Archivos generados**: `/exports/remisiones_compra/remisiones_compra_<fecha>.xlsx`
- **Tabla MariaDB**: `remisiones_compra`

### export_cotizaciones_ventas.js
- **Módulo Effi**: Ventas → Cotizaciones
- **Archivos generados**: `/exports/cotizaciones_ventas/cotizaciones_ventas_<fecha>.xlsx`
- **Tabla MariaDB**: `cotizaciones_ventas`

### export_ordenes_venta.js
- **Módulo Effi**: Ventas → Órdenes de venta
- **Archivos generados**: `/exports/ordenes_venta/ordenes_venta_encabezados_<fecha>.xlsx`, `ordenes_venta_detalle_<fecha>.xlsx`
- **Tablas MariaDB**: `ordenes_venta_encabezados`, `ordenes_venta_detalle`

### export_facturas_venta.js
- **Módulo Effi**: Ventas → Facturas de venta
- **Archivos generados**: `/exports/facturas_venta/facturas_venta_encabezados_<fecha>.xlsx`, `facturas_venta_detalle_<fecha>.xlsx`
- **Tablas MariaDB**: `facturas_venta_encabezados`, `facturas_venta_detalle`
- **Tipo archivo**: Excel real (encabezados), descarga HTTP con cookies (detalle)

### export_notas_credito_venta.js
- **Módulo Effi**: Ventas → Notas crédito
- **Archivos generados**: `/exports/notas_credito_venta/notas_credito_venta_encabezados_<fecha>.xlsx`, `notas_credito_venta_detalle_<fecha>.xlsx`
- **Tablas MariaDB**: `notas_credito_venta_encabezados`, `notas_credito_venta_detalle`

### export_remisiones_venta.js
- **Módulo Effi**: Ventas → Remisiones de venta
- **Archivos generados**: `/exports/remisiones_venta/remisiones_venta_encabezados_<fecha>.xlsx`, `remisiones_venta_detalle_<fecha>.xlsx`
- **Tablas MariaDB**: `remisiones_venta_encabezados`, `remisiones_venta_detalle`

### export_devoluciones_venta.js
- **Módulo Effi**: Ventas → Devoluciones
- **Archivos generados**: `/exports/devoluciones_venta/devoluciones_venta_<fecha>.xlsx`
- **Tabla MariaDB**: `devoluciones_venta`
- **Notas**: falla en el primer intento por timeout de red → `export_all.sh` lo reintenta automáticamente (resuelto con el mecanismo de retry).

### export_cuentas_por_pagar.js
- **Módulo Effi**: Tesorería → Cuentas por pagar
- **Archivos generados**: `/exports/cuentas_por_pagar/cuentas_por_pagar_<fecha>.xlsx`
- **Tabla MariaDB**: `cuentas_por_pagar`

### export_cuentas_por_cobrar.js
- **Módulo Effi**: Tesorería → Cuentas por cobrar
- **Archivos generados**: `/exports/cuentas_por_cobrar/cuentas_por_cobrar_<fecha>.xlsx`
- **Tabla MariaDB**: `cuentas_por_cobrar`

### export_comprobantes_ingreso.js
- **Módulo Effi**: Tesorería → Comprobantes de ingreso
- **Archivos generados**: `/exports/comprobantes_ingreso/comprobantes_ingreso_<fecha>.xlsx`
- **Tabla MariaDB**: `comprobantes_ingreso`

### export_guias_transporte.js
- **Módulo Effi**: Logística → Guías de transporte
- **Archivos generados**: `/exports/guias_transporte/guias_transporte_<fecha>.xlsx` (solo si hay registros)
- **Tabla MariaDB**: `guias_transporte`
- **Notas**: si la página muestra "0 guías de transporte encontradas", el script termina con `exit 0` sin generar archivo (comportamiento correcto — no es un error).

### export_produccion_encabezados.js
- **Módulo Effi**: Producción → Órdenes (encabezados)
- **Archivos generados**: `/exports/produccion_encabezados/produccion_encabezados_<fecha>.xlsx`
- **Tabla MariaDB**: `produccion_encabezados`

### export_produccion_reportes.js
- **Módulo Effi**: Producción → Reportes
- **Archivos generados**: `/exports/produccion_reportes/produccion_reportes_<fecha>.xlsx`
- **Tabla MariaDB**: `produccion_reportes`

### export_costos_produccion.js
- **Módulo Effi**: Producción → Costos
- **Archivos generados**: `/exports/costos_produccion/costos_produccion_<fecha>.xlsx`
- **Tabla MariaDB**: `costos_produccion`

### export_tipos_egresos.js
- **Módulo Effi**: Configuración → Tipos de egresos
- **Archivos generados**: `/exports/tipos_egresos/tipos_egresos_<fecha>.xlsx`
- **Tabla MariaDB**: `tipos_egresos`

### export_tipos_marketing.js
- **Módulo Effi**: Configuración → Tipos de marketing
- **Archivos generados**: `/exports/tipos_marketing/tipos_marketing_<fecha>.xlsx`
- **Tabla MariaDB**: `tipos_marketing`

---

## 4. Skills / Comandos Claude (`.claude/commands/`)

Skills disponibles para agentes Claude Code. Se invocan con `/nombre-skill` en la conversación.
**⚠️ LEER ANTES de construir cualquier cosa — evitan errores ya documentados.**

### Skills de Base de Datos y Backend

| Skill | Cuándo usarlo |
|---|---|
| `/effi-database` | Credenciales MariaDB, tablas `zeffi_*`, gotchas críticos de columnas (fecha_creacion_factura, descripcion_articulo, id_numeracion), conexión desde host/Docker, patrones Python/Node para queries |
| `/effi-negocio` | Modelo de negocio: qué significa "vigente", consignación, canales, tarifas, flujo de ventas, cómo interpretar los datos de Effi |

### Skills de Frontend ERP

| Skill | Cuándo usarlo |
|---|---|
| `/erp-frontend` | Arquitectura completa del ERP (Vue+Quasar+Express), URL pública, paths clave, todos los endpoints de la API, páginas existentes con árbol drill-down, cómo hacer deploy |
| `/tabla-vista` | Construir cualquier vista con tablas: patrón completo de página de detalle con KPIs + acordeones, componente OsDataTable, CSS obligatorio, errores frecuentes, breadcrumb contextual |
| `/menu-erp` | Estructura del menú dinámico desde `sys_menu` (Hostinger), cómo agregar módulos y submenús |

### Skills de Integración

| Skill | Cuándo usarlo |
|---|---|
| `/espocrm-integracion` | EspoCRM: campos custom en Contact, sistema de municipios, flujo CRM→Effi, scripts de sync, queries de diagnóstico |
| `/playwright-effi` | Construir scripts de exportación Effi: mecanismos de descarga (window.open, HTML disfrazado), manejo de sesión, errores conocidos |
| `/telegram-pipeline` | Notificaciones Telegram del pipeline: configuración del bot, formato de mensajes, cuándo enviar email vs Telegram |

### Skill de Agentes IA

| Skill | Cuándo usarlo |
|---|---|
| `.agent/skills/manejo_ia.md` | Regla de los 3 Pasos (anti-alucinación) para cualquier bot IA que consulte la BD. Arquitectura obligatoria para el bot Telegram. |

> **Nota**: Al crear un nuevo skill, agregar entrada en esta tabla. Archivo en `.claude/commands/nombre.md`.

---

## 5. Comandos de diagnóstico rápido

```bash
# Estado del pipeline automático
systemctl status effi-pipeline.timer

# Próxima ejecución
systemctl list-timers effi-pipeline.timer

# Logs recientes
journalctl -u effi-pipeline --since "24 hours ago"
tail -100 /home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/pipeline.log

# Ejecutar pipeline completo ahora (forzado)
python3 scripts/orquestador.py --forzar

# Solo export
bash scripts/export_all.sh

# Solo import
node scripts/import_all.js

# Solo un script de export específico
node scripts/export_clientes.js

# Ver cuántos registros hay en una tabla (tablas tienen prefijo zeffi_)
mysql -u osadmin -pEpist2487. effi_data -e "SELECT COUNT(*) FROM zeffi_clientes;" 2>/dev/null
```
