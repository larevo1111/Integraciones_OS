---
name: inventario-fisico
description: >
  App de inventario físico inv.oscomunidad.com. Triggers: inventario, conteo, rango, auditoría, inv.oscomunidad, stock físico, depuración inventario.
---

# Skill: Inventario Físico — Origen Silvestre

> Leer antes de crear o modificar cualquier componente, endpoint o tabla de la app de inventario.
> Contexto profundo: `.agent/contextos/inventario_fisico.md`
> Políticas de acceso: `inventario/POLITICAS_ACCESO.md`

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Vue 3 + Vite (sin Quasar), dark mode responsive |
| API | FastAPI (Python), puerto 9401 |
| Systemd | `os-inventario-api.service` |
| URL | inv.oscomunidad.com (Cloudflare tunnel) |
| Auth | Google OAuth, JWT compartido con sistema gestión |
| BD propia | `os_inventario` (MariaDB local) |

---

## Base de datos — `os_inventario`

### Tablas

| Tabla | Descripción | Filas típicas |
|---|---|---|
| `inv_conteos` | Conteos por artículo+bodega+fecha. Campos: `cantidad_contada`, `nota`, `foto_url`, `estado` (pendiente/contado/verificado) | ~500/inventario |
| `inv_rangos` | Unidad (KG/GRS/UND/LT), grupo (MP/PP/PT/INS/DS), rango min/max por artículo | 489 |
| `inv_auditorias` | Historial de cambios acumulativa: quién, cuándo, qué cambió, tipo acción | crece |

### Tablas fuente (read-only desde effi_data)

| Tabla | Registros | Uso |
|---|---|---|
| `zeffi_inventario` | 489 vigentes | Stock actual por bodega (campos TEXTO con coma decimal) |
| `zeffi_trazabilidad` | 65,117 | Movimientos (cantidad TEXTO con coma decimal y signo) |
| `zeffi_produccion_encabezados` | 81 vigentes generadas | OPs que afectan inventario |
| `zeffi_materiales` | 309 | Materias primas de OPs vigentes |
| `zeffi_articulos_producidos` | 142 | Productos terminados de OPs vigentes |
| `zeffi_bodegas` | 15 activas | Bodegas disponibles |

---

## Grupos de artículos (clasificación automática)

| Grupo | Lógica | Artículos |
|---|---|---|
| **MP** | Materia Prima (T01.xx, no en productos producidos) | 190 |
| **PP** | Producto en Proceso (aparece en zeffi_articulos_producidos) | 45 |
| **PT** | Producto Terminado (categoría TPT.xx) | 80 |
| **INS** | Insumos (T03.xx: envases, tapas, etiquetas) | 142 |
| **DS** | Desarrollo (no en producción aún) | 32 |

## Unidades

| Unidad | Detección en nombre del artículo | Artículos |
|---|---|---|
| **KG** | KG, KILO, KL | 71 |
| **GRS** | GRS, GRAMOS, G | 198 |
| **UND** | Sin unidad explícita o UND | 218 |
| **LT** | LT, LITRO | 2 |

---

## Niveles de acceso

| Nivel | Perfil | Acciones permitidas |
|---|---|---|
| 1 | Contador | Ver inventario, contar, notas, fotos |
| 3 | Coordinador | + Agregar artículos no listados |
| 5 | Supervisor | + Nuevo inventario, reiniciar, cerrar, ver auditoría |
| 7 | Admin | + Eliminar inventario, administrar rangos/unidades |

**Implementación frontend**: función `puede(accion)` que compara `nivelUsuario >= config.nivel_minimo`.
**Archivo de configuración**: `inventario/politicas.json` (fuente única de permisos).

---

## API FastAPI — endpoints

### Auth
```
POST /api/auth/google     — Login con token Google → JWT
GET  /api/auth/me         — Datos del usuario actual
```

### Inventarios
```
GET    /api/inventarios              — Lista inventarios por fecha
POST   /api/inventarios              — Crear nuevo (fecha_corte, genera artículos)
DELETE /api/inventarios/:fecha       — Eliminar (admin)
POST   /api/inventarios/:fecha/cerrar    — Cerrar para edición (supervisor+)
POST   /api/inventarios/:fecha/reiniciar — Reiniciar conteos (supervisor+)
```

### Conteos
```
GET  /api/inventarios/:fecha/conteos           — Conteos del inventario
PUT  /api/inventarios/:fecha/conteos/:id       — Actualizar conteo (cantidad, nota)
POST /api/inventarios/:fecha/conteos/:id/foto  — Subir foto
```

### Rangos y configuración
```
GET  /api/rangos                    — Rangos por artículo (min/max/unidad/grupo)
PUT  /api/rangos/:cod_articulo      — Actualizar rango (admin)
GET  /api/auditorias                — Historial de cambios
```

---

## Flujo de uso

```
1. Login Google OAuth
2. Panel lateral → seleccionar inventario por fecha (o crear nuevo)
3. Tabla principal → chips filtro (Todos/Pendientes/Contados/Diferencias) + chips bodega
4. Para cada artículo:
   a. Stepper +/- para ajuste rápido de cantidad
   b. Si fuera de rango → alerta visual con sugerencia
   c. Menú ⋮ → agregar nota / tomar foto / ver foto
5. Supervisor cierra inventario cuando conteo está completo
```

---

## Gotchas técnicos

- **Campos TEXTO con coma decimal**: `zeffi_inventario.stock_*` y `zeffi_trazabilidad.cantidad` usan coma como separador decimal ("1000,00"). Siempre `REPLACE(',', '.')` y `CAST(... AS DECIMAL(15,2))`.
- **Signos en trazabilidad**: positivo = ingreso a inventario, negativo = egreso. Tipos: ORDEN DE PRODUCCION, FACTURA DE VENTA, TRASLADO, AJUSTE, etc.
- **IDs de OPs**: formato numérico puro (1985, 2088). Excepción febrero 2025: usaron "PPAL-NNN".
- **Reconstrucción de stock a fecha**: `stock_a_fecha = stock_actual - SUM(movimientos desde fecha+1 hasta hoy)`.
- **Ajuste por OPs generadas**: para cada OP vigente no procesada, devolver materias primas (sumar) y quitar productos terminados (restar).
- **15 bodegas activas**: Principal, Villa de Aburra, Apica, El Salvador, etc. Chips filtro muestran solo las que tienen stock.
- **Vue 3 + Vite (sin Quasar)**: NO usar componentes Quasar. Estilos propios con CSS variables dark mode.

---

## Build y deploy

```bash
# Build frontend
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/inventario/frontend
npm run build
# Output: inventario/static/

# Reiniciar API
sudo systemctl restart os-inventario-api.service

# Logs
journalctl -u os-inventario-api -f
```

---

## Archivos clave

| Archivo | Propósito |
|---|---|
| `inventario/api/main.py` | FastAPI app + rutas + auth |
| `inventario/frontend/src/App.vue` | SPA única (todo el frontend) |
| `inventario/politicas.json` | Configuración de permisos por nivel |
| `inventario/POLITICAS_ACCESO.md` | Documentación de permisos |
| `.agent/contextos/inventario_fisico.md` | Contexto profundo del módulo |

---

## Módulos pendientes (planificados)

| # | Módulo | Estado |
|---|---|---|
| 1 | Foto de inventario a fecha (reconstrucción stock) | Pendiente |
| 2 | Ajuste por OPs generadas (materias primas / productos) | Pendiente |
| 3 | App de conteo físico (funcionalidad actual) | Implementado |
| 4 | Detección errores de unidades | Implementado |
| 5 | Verificación de inconsistencias | Pendiente |
| 6 | Informe final (resumen diferencias) | Pendiente |
