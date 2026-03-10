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
- **Tabla(s) MariaDB**: ninguna directamente (delega a import_all.js y calcular_resumen_ventas.py)
- **Dependencias**: `export_all.sh`, `import_all.js`, `calcular_resumen_ventas.py`, `scripts/.env`
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

| Skill | Archivo | Contenido |
|---|---|---|
| `/playwright-effi` | `.claude/commands/playwright-effi.md` | Patrones, mecanismos de descarga y errores conocidos para scripts de exportación Effi con Playwright |
| `/effi-database` | `.claude/commands/effi-database.md` | Credenciales, tablas `zeffi_*`, conexión desde host/Docker, por qué los comandos se cuelgan, patrones Python/Node |
| `/effi-negocio` | `.claude/commands/effi-negocio.md` | Modelo de negocio Effi: qué significa "vigente", consignación, canales, tarifas, flujo de ventas, fechas a usar |
| `/telegram-pipeline` | `.claude/commands/telegram-pipeline.md` | Configuración del bot Telegram para notificaciones del pipeline |

> **Nota**: Al crear un nuevo skill, agregar entrada en esta tabla.

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
