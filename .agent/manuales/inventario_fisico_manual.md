# Manual de Inventario Fisico — Origen Silvestre

**Version**: 2.0 — 2026-04-06
**Scope**: App web de conteo de inventario fisico vs teorico. Independiente del ERP y del sistema de gestion.
**URL**: inv.oscomunidad.com
**Puerto**: 9401
**Systemd**: os-inventario-api.service

---

## Indice

1. [Que es y para que sirve](#1-proposito)
2. [Stack tecnico](#2-stack)
3. [Infraestructura](#3-infraestructura)
4. [Base de datos os_inventario](#4-bd)
5. [Tabla inv_catalogo_articulos](#5-catalogo)
6. [Tablas fuente de effi_data](#6-tablas-fuente)
7. [Regla critica: timestamps Effi en UTC](#7-timestamps)
8. [Scripts](#8-scripts)
9. [API — endpoints](#9-api)
10. [Frontend](#10-frontend)
11. [Grupos de articulos](#11-grupos)
12. [Unidades y validacion de rango](#12-unidades)
13. [Niveles de acceso y politicas](#13-acceso)
14. [Inventario teorico — formula completa](#14-teorico)
15. [Flujo: crear un nuevo inventario](#15-flujo-crear)
16. [Flujo: conteo fisico](#16-flujo-conteo)
17. [Flujo: asignar articulo no matriculado](#17-flujo-asignar)
18. [Flujo: sync catalogo Effi](#18-flujo-sync)
19. [Flujo: ajuste de inventario en Effi](#19-flujo-ajuste)
20. [Build y deploy](#20-build)
21. [Troubleshooting](#21-troubleshooting)

---

## 1. Que es y para que sirve {#1-proposito}

Sistema para gestionar inventario fisico de Origen Silvestre. Permite:

- Reconstruir stock a cualquier fecha de corte desde trazabilidad de Effi
- Capturar conteos fisicos en celular, tablet o desktop
- Ajustar por ordenes de produccion (OPs) generadas pero no ejecutadas
- Detectar errores de unidades (kg vs gramos, litros vs ml)
- Comparar fisico vs teorico y detectar inconsistencias
- Auditar cada accion (quien conto, cuando, valor anterior/nuevo)

La app es independiente del ERP frontend y del sistema de gestion. Tiene su propia BD, su propio backend y su propio subdominio.

---

## 2. Stack tecnico {#2-stack}

| Capa | Tecnologia |
|---|---|
| Frontend | Vue 3 + Vite (sin Quasar). Componente unico App.vue |
| Backend | FastAPI (Python) con uvicorn |
| BD | MariaDB local — base `os_inventario` |
| Auth | Google OAuth → JWT (mismo secret y Client ID que sistema_gestion) |
| Servidor web | FastAPI sirve frontend estatico + API |
| Proxy | Cloudflared → inv.oscomunidad.com → localhost:9401 |
| Proceso | systemd `os-inventario-api.service` |

---

## 3. Infraestructura {#3-infraestructura}

| Recurso | Detalle |
|---|---|
| URL publica | inv.oscomunidad.com |
| Puerto local | 9401 |
| Servicio systemd | os-inventario-api.service |
| Directorio base | /home/osserver/Proyectos_Antigravity/Integraciones_OS |
| Backend | scripts/inventario/api.py |
| Frontend source | inventario/frontend/src/App.vue |
| Frontend build | inventario/static/ (servido por FastAPI) |
| CSS | inventario/frontend/src/styles.css |
| Fotos | inventario/fotos/ |
| Politicas | inventario/politicas.json |
| Config depuracion | scripts/inventario/config_depuracion.json |
| Snapshots | inventario/snapshots/ |

Reiniciar servicio:

```bash
sudo systemctl restart os-inventario-api
```

---

## 4. Base de datos os_inventario {#4-bd}

Tres tablas principales mas una de calculo teorico.

### inv_conteos

Una fila por cada combinacion articulo + bodega + fecha de inventario.

| Campo | Tipo | Descripcion |
|---|---|---|
| id | INT AUTO_INCREMENT | PK |
| fecha_inventario | DATE | Fecha del evento de inventario |
| bodega | VARCHAR | Nombre de la bodega (Principal, Jenifer, etc.) |
| id_effi | VARCHAR | ID del articulo en Effi |
| cod_barras | VARCHAR | Codigo de barras |
| nombre | VARCHAR | Nombre del articulo |
| categoria | VARCHAR | Categoria Effi (T01.xx, TPT.xx, etc.) |
| excluido | TINYINT | 1 = excluido del conteo, 0 = inventariable |
| razon_exclusion | VARCHAR | Razon de exclusion (si aplica) |
| inventario_teorico | DECIMAL(12,2) | Stock calculado a la fecha de corte |
| inventario_fisico | DECIMAL(12,2) | Conteo fisico ingresado por el usuario |
| diferencia | DECIMAL(12,2) | fisico - teorico |
| costo_promedio | DECIMAL(12,2) | Costo promedio del articulo |
| estado | ENUM | pendiente / contado / verificado |
| contado_por | VARCHAR | Email del usuario que conto |
| fecha_conteo | DATETIME | Cuando se registro el conteo |
| notas | TEXT | Notas del contador |
| foto | VARCHAR | Nombre del archivo de foto (UUID) |

### inv_rangos

Una fila por articulo. Almacena unidad, grupo y rangos para validacion.

| Campo | Tipo | Descripcion |
|---|---|---|
| id | INT AUTO_INCREMENT | PK |
| id_effi | VARCHAR | ID del articulo en Effi |
| nombre | VARCHAR | Nombre del articulo |
| grupo | VARCHAR | MP, PP, PT, INS, DS, DES, NM |
| unidad | VARCHAR | KG, GRS, UND, LT, ML |
| rango_min | DECIMAL(12,2) | Valor minimo esperado |
| rango_max | DECIMAL(12,2) | Valor maximo esperado |
| promedio | DECIMAL(12,2) | Stock promedio historico |
| factor_error | INT | Factor de error tipico (1000 para KG/LT, NULL para otros) |

### inv_auditorias

Registro inmutable de toda accion que modifica datos.

| Campo | Tipo | Descripcion |
|---|---|---|
| id | INT AUTO_INCREMENT | PK |
| conteo_id | INT | FK a inv_conteos.id (0 para acciones globales) |
| accion | VARCHAR | conteo, edicion, nota, foto, reactivar, calcular_teorico, nuevo_inventario, reiniciar_inventario, cerrar_inventario, eliminar_inventario, no_matriculado |
| usuario | VARCHAR | Email del usuario |
| valor_anterior | TEXT | Valor antes del cambio |
| valor_nuevo | TEXT | Valor despues del cambio |
| detalle | TEXT | Contexto adicional |
| created_at | DATETIME | Timestamp automatico |

### inv_teorico

Resultado del calculo de inventario teorico a fecha de corte.

| Campo | Tipo | Descripcion |
|---|---|---|
| id | INT AUTO_INCREMENT | PK |
| fecha_corte | DATE | Fecha de corte del calculo |
| cod_articulo | VARCHAR(50) | ID del articulo |
| nombre_articulo | VARCHAR(255) | Nombre |
| stock_effi | DECIMAL(12,2) | Stock actual en zeffi_inventario |
| ajuste_trazabilidad | DECIMAL(12,2) | Suma neta de movimientos post-corte |
| ajuste_ops_materiales | DECIMAL(12,2) | Materiales de OPs generadas al corte |
| ajuste_ops_productos | DECIMAL(12,2) | Productos de OPs generadas al corte |
| stock_teorico | DECIMAL(12,2) | Resultado final de la formula |
| ops_generadas_count | INT | Cantidad de OPs incluidas |
| ops_incluidas | TEXT | JSON con IDs de OPs usadas |
| calculado_en | DATETIME | Timestamp del calculo |
| UK | (fecha_corte, cod_articulo) | Unico por fecha + articulo |

---

## 5. Tabla inv_catalogo_articulos {#5-catalogo}

Catalogo de articulos de Effi con unidad y grupo precalculados. Vive en `effi_data` (local) y en `u768061575_os_integracion` (Hostinger). Mismo patron que `crm_contactos`.

**Se actualiza de 2 formas:**
1. Cada 1 hora — paso 6e del pipeline (`sync_inventario_catalogo.py`)
2. Bajo demanda — boton "Sync Effi" en la app de inventario

**Script:** `scripts/sync_inventario_catalogo.py`

| Campo | Tipo | Descripcion |
|---|---|---|
| id_effi | VARCHAR(20) PK | ID del articulo en Effi |
| cod_barras | VARCHAR(50) | Codigo de barras |
| nombre | VARCHAR(255) | Nombre del articulo |
| categoria | VARCHAR(100) | Categoria Effi (T01.xx, TPT.xx, etc.) |
| vigencia | VARCHAR(20) | Siempre "Vigente" (solo se importan vigentes) |
| tipo_articulo | VARCHAR(50) | Tipo de articulo en Effi |
| gestion_stock | VARCHAR(10) | "Si" o "No" |
| costo_promedio | DECIMAL(15,2) | Costo promedio |
| stock_total | DECIMAL(15,2) | Stock total empresa |
| unidad | VARCHAR(5) | Detectada por regex del nombre (KG/GRS/UND/LT/ML) |
| grupo | VARCHAR(5) | Calculado: MP/PP/PT/INS/DS/DES (cruce con OPs) |
| actualizado_en | DATETIME | Timestamp de ultima sincronizacion |

**Por que existe esta tabla y no se usa `zeffi_inventario` directamente:**
`import_all.js` hace DROP TABLE + CREATE en cada ejecucion del pipeline (cada 1h). Cualquier columna extra (unidad, grupo) se pierde. `inv_catalogo_articulos` usa CREATE IF NOT EXISTS + TRUNCATE + INSERT — la estructura sobrevive. Mismo patron que `crm_contactos` de EspoCRM.

**Quien la usa:**
- El endpoint `/api/inventario/articulos/buscar` (modal de asignar articulos NM)
- El boton "Sync Effi" en la toolbar del frontend

---

## 6. Tablas fuente de effi_data {#6-tablas-fuente}

El sistema lee datos de 6 tablas de la BD `effi_data` (staging del pipeline Effi).

### zeffi_inventario

Stock actual por articulo. ~489 articulos vigentes.

- `id` — ID del articulo (texto)
- `nombre`, `categoria`, `vigencia`, `gestion_de_stock`
- `stock_total_empresa` — stock total (texto con coma decimal)
- `stock_bodega_principal_sucursal_principal`, `stock_bodega_jenifer_...`, etc. — stock por bodega
- `costo_promedio`, `costo_manual`, `ultimo_costo` — costos (texto con coma decimal)
- `cod_barras` — codigo de barras

Todos los campos numericos son TEXT con coma como separador decimal. Para operar:
```sql
CAST(REPLACE(campo, ',', '.') AS DECIMAL(12,2))
```

### zeffi_trazabilidad

Movimientos de inventario. ~65,000 registros (vigentes + anulados).

- `id_articulo` — ID del articulo
- `articulo` — nombre
- `transaccion` — tipo y numero (ej: "ORDEN DE PRODUCCION: 2088")
- `tipo_de_movimiento` — "Creacion de transaccion" o "Anulacion de transaccion"
- `vigencia_de_transaccion` — "Transaccion vigente" o "Transaccion anulada"
- `cantidad` — texto con coma decimal. Positivo = ingreso a bodega, negativo = egreso
- `bodega` — nombre de bodega
- `fecha` — timestamp EN UTC (ver seccion 6)

Para la formula de inventario teorico, NO filtrar por vigencia. Las anulaciones tienen signos invertidos y se cancelan solas matematicamente.

### zeffi_produccion_encabezados

Ordenes de produccion (OPs).

- `id_orden` — ID numerico secuencial
- `estado` — Generada / Procesada
- `vigencia` — Vigente / Anulado
- `fecha_de_creacion` — timestamp EN UTC

### zeffi_cambios_estado

Historial de cambios de estado de OPs. No registra el estado inicial (Generada se asume por defecto).

- `id_orden` — FK a produccion_encabezados
- `nuevo_estado` — estado al que cambio
- `f_cambio_de_estado` — timestamp EN UTC

### zeffi_materiales

Materias primas consumidas por cada OP.

- `id_orden` — FK a produccion_encabezados
- `cod_material` — ID del articulo consumido
- `descripcion_material` — nombre
- `cantidad` — texto con coma decimal
- `vigencia` — "Orden vigente" (NO "Vigente" — diferencia critica)

### zeffi_articulos_producidos

Productos terminados generados por cada OP.

- `id_orden` — FK a produccion_encabezados
- `cod_articulo` — ID del articulo producido
- `descripcion_articulo_producido` — nombre
- `cantidad` — texto con coma decimal
- `vigencia` — "Orden vigente"

---

## 7. Regla critica: timestamps Effi en UTC {#7-timestamps}

**Todas las timestamps de tablas Effi (zeffi_*) estan en UTC, NO en hora Colombia.**

Tablas afectadas:
- `zeffi_trazabilidad.fecha`
- `zeffi_cambios_estado.f_cambio_de_estado`
- `zeffi_produccion_encabezados.fecha_de_creacion`

Al comparar contra una fecha de corte en hora Colombia (UTC-5), hay que convertir el corte sumando 5 horas:

```sql
-- MAL: compara hora Colombia contra UTC, desfase de 5 horas
WHERE fecha > '2026-03-31 23:59:59'

-- BIEN: convierte corte Colombia a UTC
WHERE fecha > DATE_ADD('2026-03-31 23:59:59', INTERVAL 5 HOUR)
```

Bug real documentado: OPs procesadas a las 7pm Colombia aparecian como "1 de abril 00:02 UTC". El script las trataba como post-corte e incluia 38 OPs falsas.

---

## 8. Scripts {#8-scripts}

### depurar_inventario.py

Crea un nuevo evento de inventario. Lee articulos de `zeffi_inventario`, aplica reglas de exclusion de `config_depuracion.json`, y genera filas por articulo+bodega en `inv_conteos`.

```bash
python3 scripts/inventario/depurar_inventario.py --fecha 2026-03-31
```

- Sin `--fecha` usa la fecha de hoy
- Borra filas previas de la misma fecha (re-ejecucion segura)
- Articulos con stock en multiples bodegas generan una fila por bodega
- Articulos sin stock van a bodega "Principal" con stock 0
- Excluidos van con `excluido=1` y bodega "—"

Reglas de exclusion (en `config_depuracion.json`):
- Sin gestion de stock (`gestion_de_stock = 'No'`)
- Sin categoria
- Categoria T999% (obsoletos)
- Categoria XMATERIAL% (material POP)
- Categoria GASTOS% (no son articulos fisicos)
- Categoria T05% (activos fijos, moldes, herramientas, consumibles)

De ~489 vigentes se obtienen ~300 inventariables.

### calcular_rangos.py

Genera tabla `inv_rangos` con unidad, grupo y rangos de validacion por articulo.

```bash
python3 scripts/inventario/calcular_rangos.py
```

- Trunca y regenera toda la tabla
- Detecta unidad del nombre del articulo (regex)
- Detecta grupo cruzando con `zeffi_articulos_producidos`
- Calcula rangos min/max basados en stock actual

### calcular_inventario_teorico.py

Calcula inventario teorico a una fecha de corte usando la formula de 4 terminos (ver seccion 13).

```bash
python3 scripts/inventario/calcular_inventario_teorico.py --fecha 2026-03-31
```

- Sin `--fecha` usa la fecha de hoy
- Guarda resultado en `inv_teorico` (DELETE + INSERT por fecha)
- Actualiza `inventario_teorico` y `diferencia` en `inv_conteos`
- Timeout de 120 segundos cuando se llama desde la API

### snapshot_inventario.sh

Corre pipeline Effi completo y guarda copia de `zeffi_inventario` en CSV.

```bash
bash scripts/inventario/snapshot_inventario.sh
```

- Ejecuta `orquestador.py --forzar` (pipeline completo)
- Exporta inventario a `inventario/snapshots/inventario_YYYY-MM-DD_HHMM.csv`
- Para cron: programar antes del conteo fisico para tener datos frescos

### config_depuracion.json

Archivo de configuracion (no es script). Define reglas de exclusion para `depurar_inventario.py`.

```json
{
  "excluir_sin_gestion_stock": true,
  "excluir_sin_categoria": true,
  "excluir_categorias": [
    {"patron": "T999%", "razon": "Productos obsoletos"},
    {"patron": "XMATERIAL%", "razon": "Material POP"},
    {"patron": "GASTOS%", "razon": "No son articulos fisicos"},
    {"patron": "T05%", "razon": "Activos fijos y consumibles"}
  ]
}
```

Para agregar una exclusion nueva: agregar entrada en `excluir_categorias` con patron SQL LIKE y razon.

### sync_inventario_catalogo.py

Sincroniza articulos de `zeffi_inventario` a `inv_catalogo_articulos` con unidad y grupo precalculados. Guarda en effi_data local + Hostinger.

```bash
python3 scripts/sync_inventario_catalogo.py
```

- Lee articulos vigentes de `zeffi_inventario`
- Cruza con `zeffi_articulos_producidos` para detectar grupo PP
- Detecta unidad por regex del nombre
- DROP + CREATE + INSERT en `effi_data.inv_catalogo_articulos` (local)
- DROP + CREATE + INSERT en `u768061575_os_integracion.inv_catalogo_articulos` (Hostinger via SSH tunnel)
- Paso 6e del pipeline (despues de sync EspoCRM → Hostinger)
- Tambien se ejecuta desde el boton "Sync Effi" de la app

### import_ajuste_inventario.js

Script Playwright para crear ajustes de inventario en Effi. Importa conceptos desde un Excel.

```bash
node scripts/import_ajuste_inventario.js <bodega_id> <archivo.xlsx> [observacion]
```

**Parametros:**
- `bodega_id` (obligatorio): ID de bodega en Effi
- `archivo.xlsx` (obligatorio): Excel con formato plantilla Effi
- `observacion` (opcional): texto para Observacion. Default: "SYS GENERATED - Ajuste inventario, [fecha hora]"

**IDs de bodegas de Effi:**

| ID | Bodega |
|---|---|
| 1 | Principal |
| 2 | Villa de aburra |
| 3 | Apica |
| 4 | El Salvador |
| 5 | Feria Santa Elena |
| 6 | DON LUIS SAN MIGUEL |
| 7 | LA TIERRITA |
| 8 | Jenifer |
| 10 | REGINALDO |
| 13 | Desarrollo de Producto |
| 14 | Ricardo |
| 15 | Mercado Libre |
| 16 | Santiago |
| 17 | Productos No Conformes Bod PPAL |
| 18 | FERIA CAMPESINA SAN CARLOS |

**Formato del Excel (7 columnas obligatorias):**

| Columna | Descripcion | Ejemplo |
|---|---|---|
| Código Effi: Artículo * | ID del articulo en Effi | 275 |
| Descripción * | Nombre (Effi lo autocompleta del codigo) | CHOCOBEETAL X KG |
| Lote | Lote (opcional) | |
| Serie | Serie (opcional) | |
| Costo * | Costo unitario (>= 0, obligatorio > 0 si no existe) | 1 |
| Tipo de ajuste * | 1 = Ingreso, 2 = Egreso | 1 |
| Cantidad * | Cantidad a ajustar | 0.5 |

**Plantilla de referencia:** `plantilla_importacion_ajuste_inventario.xlsx` (raiz del repo)

**Flujo Playwright:**
1. Navega a `effi.com.co/app/ajuste_inventario`
2. Click "Crear" → abre modal
3. Selecciona Sucursal (Principal) y Bodega via jQuery Chosen API
4. Click "Importar conceptos" (`#importarConceptos_CR`)
5. Sube Excel en el modal de importacion
6. Click "Importar conceptos" (`#formulario_IC #btn_submit`)
7. Elimina filas vacias de conceptos (Effi agrega una por defecto)
8. Llena campo Observacion
9. Click "Crear ajuste de inventario"
10. Verifica errores de validacion
11. Screenshots en `/exports/ajuste_*.png`

**Caso de uso: traslado entre bodegas**

Effi no tiene un modulo de traslado directo accesible por API. Para mover stock de bodega A a bodega B, se hacen 2 ajustes:

```bash
# 1. Egreso de la bodega origen
node scripts/import_ajuste_inventario.js 13 /tmp/egreso.xlsx "SYS GENERATED - Traslado Desarrollo -> Principal"

# 2. Ingreso a la bodega destino
node scripts/import_ajuste_inventario.js 1 /tmp/ingreso.xlsx "SYS GENERATED - Traslado Desarrollo -> Principal"
```

El Excel de egreso usa Tipo de ajuste = 2, el de ingreso usa Tipo de ajuste = 1. Mismos articulos y cantidades.

---

## 9. API — endpoints {#9-api}

Archivo: `scripts/inventario/api.py`. FastAPI corriendo en puerto 9401.

### Lectura

| Metodo | Ruta | Parametros | Retorna |
|---|---|---|---|
| GET | /api/inventario/politicas | — | JSON de politicas de acceso |
| GET | /api/inventario/fechas | — | Lista de fechas de inventario con conteos totales/contados/diferencias |
| GET | /api/inventario/bodegas | ?fecha=YYYY-MM-DD | Bodegas con stock para esa fecha (con conteos) |
| GET | /api/inventario/bodegas/todas | ?fecha=YYYY-MM-DD | TODAS las bodegas (con y sin articulos) |
| GET | /api/inventario/articulos | ?fecha=...&bodega=...&filtro=...&busqueda=... | Articulos para contar. filtro: pendientes/contados/diferencias |
| GET | /api/inventario/excluidos | ?fecha=YYYY-MM-DD | Articulos excluidos del inventario |
| GET | /api/inventario/resumen | ?fecha=...&bodega=... | Totales: total/contados/pendientes/ok/con_diferencia |
| GET | /api/inventario/articulos/buscar | ?q=texto | Busca en inv_catalogo_articulos (con unidad y grupo) |
| GET | /api/inventario/fotos/{nombre} | — | Sirve archivo de foto |
| GET | /api/inventario/teorico/estado | ?fecha=YYYY-MM-DD | Info del ultimo calculo teorico |

### Escritura

| Metodo | Ruta | Body | Retorna |
|---|---|---|---|
| PUT | /api/inventario/articulos/{id}/conteo | `{inventario_fisico, contado_por}` | Diferencia calculada |
| PUT | /api/inventario/articulos/{id}/nota | `{notas, usuario}` | OK |
| POST | /api/inventario/articulos/{id}/foto | Form: usuario + file | Nombre de foto |
| POST | /api/inventario/articulos/agregar | `{fecha_inventario, bodega, id_effi, contado_por}` | Nombre del articulo |
| PUT | /api/inventario/articulos/{id}/reactivar | `{usuario}` | OK |
| POST | /api/inventario/articulos/no-matriculado | Form: fecha, bodega, nombre, unidad, cantidad, costo, notas, usuario, foto | ID nuevo |
| POST | /api/inventario/articulos/asignar | `{conteo_id, id_effi_nuevo, nombre_effi, categoria_effi, cod_barras, usuario}` | OK + nota automatica |

### Gestion (nivel >= 5)

| Metodo | Ruta | Body | Retorna |
|---|---|---|---|
| POST | /api/inventario/nuevo | `{fecha_inventario, usuario}` | Output del depurador |
| POST | /api/inventario/reiniciar | `{fecha_inventario, usuario}` | Cantidad reiniciados |
| POST | /api/inventario/cerrar | `{fecha_inventario, usuario}` | Cantidad cerrados |
| POST | /api/inventario/eliminar | `{fecha_inventario, usuario}` | Cantidad eliminados |
| POST | /api/inventario/calcular-teorico | `{fecha_inventario, usuario}` | Output del calculo |
| POST | /api/inventario/sync-effi | — | Lanza export+import+sync catalogo en background |
| GET | /api/inventario/sync-effi/estado | — | Estado de la sincronizacion (idle/exportando/importando/ok/error) |

### Autenticacion

Todos los endpoints requieren JWT en header `Authorization: Bearer <token>`. El JWT se genera con Google OAuth (mismo flujo que sistema_gestion). El secret es compartido.

La funcion `verificar_jwt()` valida el token. Si expira o es invalido retorna 401.

### Frontend estatico

FastAPI sirve el build de produccion desde `inventario/static/`. Monta `/assets` como StaticFiles y cualquier otra ruta no-API retorna `index.html` (SPA fallback).

---

## 10. Frontend {#10-frontend}

### Estructura

Un solo componente: `inventario/frontend/src/App.vue`. Contiene todo: login, tabla, filtros, modales, panel lateral.

Archivos:
- `inventario/frontend/src/App.vue` — componente unico
- `inventario/frontend/src/styles.css` — variables CSS del design system OS (dark mode)
- `inventario/frontend/src/main.js` — punto de entrada
- `inventario/frontend/vite.config.js` — configuracion Vite
- `inventario/static/` — build de produccion

### Login

Google OAuth con el mismo Client ID que sistema_gestion. Al autenticar, el backend genera un JWT con datos del usuario (email, nombre, nivel). El frontend guarda el JWT en localStorage.

### Tabla principal

- Columnas: articulo, grupo, unidad, teorico, fisico, diferencia
- Popups de filtro/ordenamiento por columna (patron GestionTable)
- Busqueda por nombre, ID o codigo de barras

### Filtros

Chips en la parte superior:
- Todos / Pendientes / Contados / Diferencias

Chips de bodega:
- Muestra solo bodegas con stock
- Boton (+) para ver todas las bodegas disponibles

### Panel lateral

Panel retractil a la izquierda para:
- Seleccionar entre inventarios (fechas disponibles)
- Ver resumen de progreso por fecha

### Conteo

- Input `type="text"` con `inputmode="decimal"` (acepta punto y coma como separador)
- Stepper +/- para ajuste rapido
- Al guardar: calcula diferencia = fisico - teorico automaticamente
- `guardarConteo()` actualiza `articulo.inventario_fisico` ANTES del await fetch (UX inmediata)

### Tags

- Grupo: tags de color (MP, PP, PT, INS, DS, DES, NM)
- Unidad: tag junto al nombre (KG, GRS, UND, LT)

### Mini menu (tres puntos)

Boton con icono de tres puntos en cada fila. Opciones:
- Agregar nota
- Tomar foto
- Ver foto (si existe)
- Asignar articulo (solo para articulos NM-*, nivel >= 5) — abre modal de asignacion

### Boton Sync Effi

Boton azul en la toolbar (nivel >= 5). Actualiza el catalogo de articulos de Effi bajo demanda.
- Click → lanza en background: export Playwright + import_all + sync_inventario_catalogo
- Spinner animado mientras corre. Estados: Descargando / Importando / OK / Error
- Se desactiva mientras hay sync en curso
- Util cuando se matricula un articulo nuevo en Effi y se necesita que aparezca en el modal de asignar

### Responsive

Funciona en desktop, tablet y movil. Layout adaptativo.

### Gotchas del frontend

- El reloj usa DOM directo (`getElementById`), NO ref reactivo — evita re-render que borre inputs activos
- Las fotos se guardan en `inventario/fotos/` con UUID, referencia en `inv_conteos.foto`
- El build de produccion va a `inventario/static/` y FastAPI lo sirve

---

## 11. Grupos de articulos {#11-grupos}

Campo `grupo` en `inv_rangos`. Asignado automaticamente por `calcular_rangos.py`.

| Grupo | Nombre | Logica de clasificacion |
|---|---|---|
| MP | Materia Prima | Categoria T01.xx que NO aparece en `zeffi_articulos_producidos` |
| PP | Producto en Proceso | Cualquier articulo que aparece como producido en una OP |
| PT | Producto Terminado | Categoria TPT.xx (articulos de venta directa) |
| INS | Insumos | Categoria T03.xx (envases, tapas, etiquetas, bolsas, cajas) |
| DS | Desarrollo | Categoria que contiene "DESARROLLO DE PRODUCTO" |
| DES | Desperdicio | Nombre contiene "DESPERDICIO" o "DESPERDI" |
| NM | No Matriculado | Categoria empieza con "NO MATRICULADO" o ID empieza con "NM-" |

Prioridad de clasificacion (la primera que matchea gana):
1. DES (por nombre)
2. NM (por categoria o ID)
3. PT (por categoria TPT)
4. INS (por categoria T03)
5. DS (por categoria DESARROLLO)
6. PP (por cruce con zeffi_articulos_producidos)
7. MP (default para T01.xx)

---

## 12. Unidades y validacion de rango {#12-unidades}

### Deteccion de unidad

Campo `unidad` en `inv_rangos`. Detectada automaticamente del nombre del articulo por regex en `calcular_rangos.py`.

| Unidad | Patron de deteccion | Ejemplo |
|---|---|---|
| KG | Nombre contiene KG, KILO, KL | "ACEITE COCO X KG" |
| GRS | Nombre contiene GRS, GRAMOS, G | "MIEL 250 GRS" |
| LT | Nombre contiene LT, LITRO, LTS | "ACEITE X LT" |
| ML | Nombre contiene ML, MILILITROS | "ESENCIA 100 ML" |
| UND | Sin unidad en nombre, o explicito | "TAPA DORADA" |

Default: UND (si ninguna regex matchea).

### Rangos

Cada articulo tiene `rango_min` y `rango_max` en `inv_rangos`, calculados asi:
- KG / LT: min = 0.1, max = maximo(200, stock_actual * 3)
- UND / GRS / ML: min = 1, max = maximo(500, stock_actual * 3)

### Factor de error

- KG: factor_error = 1000 (error tipico: poner gramos en vez de kilos)
- LT: factor_error = 1000 (error tipico: poner ml en vez de litros)
- Otros: NULL

### Validacion al contar

Cuando el usuario ingresa un valor fuera de rango:
1. Aparece modal de alerta con sugerencia de correccion
2. Si el factor_error aplica, sugiere dividir o multiplicar por 1000
3. El valor 0 siempre es permitido (no dispara alerta)
4. Si el usuario confirma el valor fuera de rango, se guarda pero queda en auditoria

---

## 13. Niveles de acceso y politicas {#13-acceso}

Fuente de verdad: `inventario/politicas.json`.

Los niveles vienen del JWT (campo `nivel`), que se hereda de `sys_usuarios.Nivel_Acceso` en la BD `os_comunidad` de Hostinger.

### Perfiles

| Nivel | Perfil | Descripcion |
|---|---|---|
| 1 | Contador | Personal operativo. Cuenta y documenta |
| 3 | Coordinador | Puede agregar articulos no listados |
| 5 | Supervisor | Gestiona inventarios (crear, reiniciar, cerrar) |
| 7 | Admin | Control total. Puede eliminar y configurar |

### Acciones por nivel

| Accion | Nivel minimo | Descripcion |
|---|---|---|
| ver_inventario | 1 | Ver articulos y conteos |
| contar | 1 | Registrar conteo fisico |
| agregar_nota | 1 | Agregar notas a articulos |
| tomar_foto | 1 | Tomar foto de articulo |
| agregar_articulo | 3 | Agregar articulo no listado a una bodega |
| asignar_articulo | 5 | Vincular articulo NM con articulo de Effi |
| nuevo_inventario | 5 | Crear evento de inventario con fecha de corte |
| reiniciar_inventario | 5 | Borrar conteos (mantiene articulos) |
| cerrar_inventario | 5 | Cerrar inventario (bloquea edicion) |
| ver_auditoria | 5 | Ver historial de cambios |
| administrar_rangos | 7 | Editar rangos y unidades |
| eliminar_inventario | 7 | Eliminar un inventario completo |

### Implementacion en frontend

```javascript
function puede(accion) {
  const config = politicas.acciones[accion]
  return config && nivelUsuario >= config.nivel_minimo
}
```

Cada boton o seccion usa `v-if="puede('nombre_accion')"`.

### Como agregar un nuevo permiso

1. Agregar la accion en `inventario/politicas.json` bajo `acciones`
2. En el frontend, usar `v-if="puede('nombre_accion')"` en el componente
3. Documentar en `inventario/POLITICAS_ACCESO.md`

---

## 14. Inventario teorico — formula completa {#14-teorico}

### Formula

```
Inventario teorico en fecha_corte =
  stock_actual (zeffi_inventario, hoy)
  - movimientos_netos_post_corte (trazabilidad entre fecha_corte+1 y hoy)
  + materiales de OPs con estado='Generada' al corte
  - productos de OPs con estado='Generada' al corte
```

Agrupado por `cod_articulo` (suma de todas las bodegas).

### Termino 1 — Stock actual

Punto de partida. Es lo que Effi reporta hoy en `zeffi_inventario.stock_total_empresa`.

### Termino 2 — Trazabilidad post-corte

"Rebobinar" el tiempo. Si entre el corte y hoy entraron 20 unidades por una compra, hay que restarlas para reconstruir el stock del corte.

```sql
SELECT id_articulo,
       SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS neto
FROM zeffi_trazabilidad
WHERE fecha > DATE_ADD('YYYY-MM-DD 23:59:59', INTERVAL 5 HOUR)
GROUP BY id_articulo
```

Se usa TODOS los registros (creaciones + anulaciones). Las anulaciones tienen signos invertidos y se cancelan solas.

### Termino 3 — Materiales de OPs generadas

Effi registra el efecto de una OP al crearla, no al ejecutarla. Para una OP "Generada" al corte, Effi ya desconto materiales del stock, pero fisicamente esas materias primas aun estaban en bodega. Hay que devolverlas (sumar).

### Termino 4 — Productos de OPs generadas

El mismo caso inverso: Effi ya sumo los productos terminados, pero fisicamente no se han producido. Hay que quitarlos (restar).

### Como determinar el estado de una OP en fecha historica

Tabla clave: `zeffi_cambios_estado`. No registra el estado inicial. Si una OP no tiene registros, su estado es "Generada" (por defecto).

```sql
SELECT nuevo_estado
FROM zeffi_cambios_estado
WHERE id_orden = 'X'
  AND f_cambio_de_estado <= DATE_ADD('fecha_corte 23:59:59', INTERVAL 5 HOUR)
ORDER BY f_cambio_de_estado DESC, _pk DESC
LIMIT 1;
-- Si no retorna filas = estado 'Generada'
```

OPs generadas al corte = OPs que cumplen:
1. `fecha_de_creacion <= corte` (existian al corte, en UTC con ajuste)
2. `vigencia = 'Vigente'` (no anuladas)
3. Estado al corte = 'Generada' (por historial de cambios o por ausencia de cambios)

### Vigencia en materiales y articulos producidos

Filtrar por `vigencia = 'Orden vigente'` (NO "Vigente" — diferencia critica).

---

## 15. Flujo: crear un nuevo inventario {#15-flujo-crear}

Requisito: nivel >= 5 (Supervisor).

1. El supervisor abre la app y va al panel lateral
2. Presiona "Nuevo inventario" y selecciona fecha de corte
3. El frontend llama `POST /api/inventario/nuevo` con fecha y usuario
4. El backend ejecuta `depurar_inventario.py --fecha YYYY-MM-DD`
5. El script lee `zeffi_inventario`, aplica reglas de exclusion, genera filas por articulo+bodega en `inv_conteos`
6. Se registra auditoria del evento
7. El supervisor puede luego presionar "Actualizar datos teoricos"
8. El frontend llama `POST /api/inventario/calcular-teorico`
9. El backend ejecuta `calcular_inventario_teorico.py --fecha YYYY-MM-DD`
10. Se calcula stock teorico y se actualiza `inv_conteos.inventario_teorico`

Antes de crear el inventario, es recomendable correr `snapshot_inventario.sh` para tener datos frescos del pipeline.

---

## 16. Flujo: conteo fisico {#16-flujo-conteo}

Requisito: nivel >= 1 (Contador).

1. El contador abre la app en su celular/tablet
2. Selecciona la fecha de inventario en el panel lateral
3. Selecciona la bodega donde va a contar
4. Filtra por "Pendientes" para ver solo lo que falta
5. Para cada articulo:
   - Ingresa la cantidad fisica en el campo de conteo
   - Acepta punto o coma como separador decimal
   - Puede usar los botones +/- para ajustar
6. Si el valor esta fuera de rango, aparece alerta con sugerencia
7. Al confirmar, se calcula diferencia = fisico - teorico
8. Opcionalmente: agregar nota o tomar foto (menu de tres puntos)

Acciones adicionales durante el conteo:
- Si encuentra un articulo que no esta en la lista: "Agregar articulo" (nivel >= 3)
- Si encuentra un articulo no matriculado en Effi: "Articulo no matriculado" (nivel >= 3)
- Si un articulo excluido deberia contarse: "Reactivar" desde la vista de excluidos

---

## 17. Flujo: asignar articulo no matriculado {#17-flujo-asignar}

Requisito: nivel >= 5 (Supervisor). Solo para articulos con ID que empieza con "NM-".

**Contexto:** Cuando un producto encontrado durante el conteo no existe en Effi, se agrega como "No Matriculado" (NM). Despues, un supervisor puede vincularlo con un articulo real de Effi.

1. El supervisor ve un articulo con tag "No Matriculado" (celeste)
2. Abre el menu de tres puntos (⋮) → click en "Asignar articulo"
3. Se abre el modal de asignacion mostrando el articulo NM arriba (nombre + unidad)
4. Busca el articulo de Effi por nombre o codigo en el campo de busqueda
5. Los resultados muestran nombre, ID, categoria y **unidad detectada**
6. Al seleccionar un articulo, aparece comparacion visual de unidades:
   - Verde: "Unidades coinciden" (KG = KG)
   - Amarillo: "¡Unidades diferentes!" (UND ≠ KG)
7. Puede cambiar la seleccion con boton "Cambiar"
8. Click "Confirmar asignacion"

**Que hace al confirmar:**
- Actualiza `id_effi`, `nombre`, `categoria`, `cod_barras` del conteo
- Genera nota automatica con: fecha, hora, usuario, nombre anterior, unidad anterior, ID Effi nuevo, nombre Effi, unidad Effi, categoria
- Registra auditoria (accion: `asignacion`)
- El articulo deja de ser NM y toma la categoria/grupo del articulo Effi

**Nota sobre unidad y grupo post-asignacion:**
El articulo asignado puede no tener entrada en `inv_rangos`. El backend detecta grupo y unidad al vuelo: usa `detectar_unidad()` (regex del nombre) y cruza con `zeffi_articulos_producidos` para detectar PP. Si no matchea, aplica la logica de categorias (TPT→PT, T03→INS, etc.).

---

## 18. Flujo: sync catalogo Effi {#18-flujo-sync}

Requisito: nivel >= 5 (Supervisor).

**Cuando usarlo:** Si se matriculo un articulo nuevo en Effi y se necesita que aparezca en la busqueda del modal de asignar (o en cualquier funcionalidad que lea de `inv_catalogo_articulos`).

1. Click en boton "Sync Effi" (azul, en la toolbar)
2. El icono empieza a girar y el texto cambia a "Descargando..."
3. El backend ejecuta en background:
   - `node scripts/export_inventario.js` — Playwright descarga Excel de Effi (~1 min)
   - `node scripts/import_all.js` — importa todos los Excel a effi_data
   - `python3 scripts/sync_inventario_catalogo.py` — genera inv_catalogo_articulos con unidad y grupo
4. El frontend hace polling cada 3 segundos a `/api/inventario/sync-effi/estado`
5. Al terminar: muestra mensaje de exito con cantidad de articulos, vuelve a idle
6. Si hay error: muestra mensaje de error

**El proceso tarda 2-3 minutos.** No se puede clickear dos veces (bloqueado mientras hay sync).

**Tambien se ejecuta automaticamente** cada 1h como paso 6e del pipeline (orquestador.py).

---

## 19. Flujo: ajuste de inventario en Effi {#19-flujo-ajuste}

### Concepto fundamental — fecha de corte

**El ajuste de inventario se calcula SIEMPRE contra la fecha de corte del inventario, NUNCA contra el stock del día en que se aplica.**

Ejemplo: si al 31 de marzo el teórico era 100 y el físico fue 80, la diferencia es -20. Esos -20 son un error que existía al 31 de marzo y se arrastra para siempre en el stock de Effi hasta que se corrija. No importa si el ajuste se aplica el 1 de abril, el 15 o el 30 — la diferencia sigue siendo -20 porque es un desfase fijo del corte.

**Lo que pase después del corte (ventas, producción, compras) no afecta la diferencia del ajuste.** Si entre el 31 de marzo y hoy se vendieron 30 unidades, el stock actual será 100 - 30 = 70. Con el ajuste de -20 queda en 50. Eso es correcto: el stock real al 31 era 80, menos 30 vendidas = 50 hoy.

**Regla**: ajuste = físico_al_corte - teórico_al_corte. Si negativo → egreso. Si positivo → ingreso. Se aplica en cualquier fecha posterior y el resultado es correcto.

**Error común a evitar**: pensar que el ajuste "resta doble" porque entre el corte y la aplicación hubo movimientos. NO. El ajuste corrige un error fijo del pasado, los movimientos posteriores son operación normal.

Script Playwright para crear ajustes de inventario directamente en Effi.

**Cuando usarlo:** Despues de analizar las diferencias del inventario fisico vs teorico, para corregir el stock en Effi.

### Ajuste simple (una bodega)

```bash
node scripts/import_ajuste_inventario.js <bodega_id> <archivo.xlsx> [observacion]
```

Ejemplo:
```bash
node scripts/import_ajuste_inventario.js 1 /tmp/ajuste_principal.xlsx "SYS GENERATED - Ajuste inventario marzo, Santiago Sierra, 2026-04-06"
```

### Traslado entre bodegas (2 ajustes)

Effi no tiene modulo de traslado accesible por script. Para mover stock de bodega A a B:

```bash
# 1. Generar Excel de egreso (Tipo de ajuste = 2) y de ingreso (Tipo de ajuste = 1)
# 2. Ejecutar ambos ajustes
node scripts/import_ajuste_inventario.js 13 /tmp/egreso_desarrollo.xlsx "SYS GENERATED - Traslado Desarrollo -> Principal"
node scripts/import_ajuste_inventario.js 1  /tmp/ingreso_principal.xlsx "SYS GENERATED - Traslado Desarrollo -> Principal"
```

### Generar Excel de ajuste desde Python

```python
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Conceptos'
ws.append(['Código Effi: Artículo *', 'Descripción *', 'Lote', 'Serie', 'Costo *', 'Tipo de ajuste *', 'Cantidad *'])
ws.append([275, 'CHOCOBEETAL X KG', '', '', 1, 1, 0.5])  # 1=Ingreso
ws.append([405, 'CHOCOBEETAL OS 130 GRS', '', '', 1, 2, 3])  # 2=Egreso
wb.save('/tmp/ajuste.xlsx')
```

**Reglas del Excel:**
- Costo debe ser > 0 (al menos 1) — Effi lo requiere
- Lote y Serie: string vacio si no aplica (no None/null)
- Tipo de ajuste: 1 = Ingreso (aumenta stock), 2 = Egreso (disminuye stock)
- El script elimina automaticamente filas vacias que Effi agrega por defecto

---

## 20. Build y deploy {#20-build}

### Build del frontend

```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/inventario/frontend
npx vite build
```

El build va a `inventario/static/` que FastAPI sirve automaticamente.

### Reiniciar servicio

```bash
sudo systemctl restart os-inventario-api
```

### Verificar estado

```bash
sudo systemctl status os-inventario-api
```

### Test rapido de la API

```bash
curl -s "http://127.0.0.1:9401/api/inventario/resumen?fecha=2026-03-31"
```

### Regenerar rangos (despues de cambios en articulos)

```bash
python3 scripts/inventario/calcular_rangos.py
```

### Crear inventario desde linea de comandos

```bash
python3 scripts/inventario/depurar_inventario.py --fecha 2026-03-31
python3 scripts/inventario/calcular_inventario_teorico.py --fecha 2026-03-31
```

---

## 21. Troubleshooting {#21-troubleshooting}

### La API no responde

```bash
sudo systemctl status os-inventario-api
sudo journalctl -u os-inventario-api --no-pager -n 50
```

Si esta caido, reiniciar:
```bash
sudo systemctl restart os-inventario-api
```

### El inventario teorico muestra valores incorrectos

1. Verificar que el pipeline corrio recientemente (datos frescos en effi_data)
2. Verificar timestamps: los datos Effi estan en UTC, el corte en hora Colombia
3. Re-calcular:
```bash
python3 scripts/inventario/calcular_inventario_teorico.py --fecha YYYY-MM-DD
```

### Articulos aparecen excluidos que no deberian

Revisar `scripts/inventario/config_depuracion.json`. Si un patron de exclusion es demasiado amplio, ajustar el patron. Tambien se puede reactivar un articulo individual desde la interfaz (nivel >= 3).

### El conteo no se guarda

Verificar conexion a MariaDB:
```bash
mysql -u osadmin -pEpist2487. os_inventario -e "SELECT COUNT(*) FROM inv_conteos" 2>/dev/null
```

### Error "Articulo no encontrado en Effi" al agregar

El articulo no existe en `zeffi_inventario` con `vigencia = 'Vigente'`. Puede ser que:
- El pipeline no ha corrido y el articulo es nuevo
- El articulo fue dado de baja en Effi

### Fotos no se muestran

Verificar que el directorio `inventario/fotos/` existe y tiene permisos de escritura. Las fotos se sirven por `GET /api/inventario/fotos/{nombre}`.

### Diferencia entre contados y teorico despues de recalcular

Al recalcular el teorico (`POST /api/inventario/calcular-teorico`), se actualiza `inventario_teorico` y se recalcula `diferencia` para los articulos que ya tenian conteo fisico. Esto es normal — el teorico puede cambiar si hay nuevos movimientos en trazabilidad o si OPs cambiaron de estado.

### La fecha del inventario ya existe

El script `depurar_inventario.py` hace DELETE + INSERT para la fecha. Si se ejecuta de nuevo, borra los conteos existentes. Solo hacerlo si se quiere reiniciar completamente.

---

## Documentacion relacionada

- `.agent/contextos/inventario_fisico.md` — contexto del modulo con estado actual y pendientes
- `.agent/skills/inventario-fisico/SKILL.md` — skill con stack, BD, endpoints, flujos y gotchas
- `.agent/docs/MANUAL_EFFI_PRODUCCION_INVENTARIOS.md` — manual completo de tablas Effi de produccion e inventarios
- `inventario/POLITICAS_ACCESO.md` — documentacion de politicas de acceso
- `inventario/politicas.json` — configuracion de permisos
- `plantilla_importacion_ajuste_inventario.xlsx` — plantilla Excel para ajustes de inventario en Effi
- `scripts/sync_inventario_catalogo.py` — sync catalogo articulos (paso 6e del pipeline)
- `scripts/import_ajuste_inventario.js` — script Playwright para crear ajustes en Effi
