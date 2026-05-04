# Effi — POST directo `/app/remision_c/crear`

**Estado**: investigación parcial, falta capturar 1 POST real para validar.

## Endpoint
```
POST https://effi.com.co/app/remision_c/crear
Content-Type: application/x-www-form-urlencoded
Cookies: session.json
```

## Form parseado (HTML del modal "Crear remisión")

### Hidden inputs (defaults conocidos)
| Campo | Default | Notas |
|---|---|---|
| `proveedor` | '' | id Effi del proveedor (resolver via búsqueda) |
| `id_concepto[]` | random 21 dígitos | Uno por línea de concepto. Se usa como clave en `impuestos[<id>][]` |
| `observacion_concepto[]` | '' | |
| `lote[]` | '' | |
| `serie[]` | '' | |
| `gift[]` | '0' | |
| `base_retencion[]` | '' | |
| `valor_retencion[]` | '' | |
| `total_descuento` | '0' | |
| `total_retencion` | '0' | |
| `total_transaccion` | '0' | |
| `sucursal_anticipo[]` | '' | |
| `id_anticipo[]` | '' | |
| `action` | '1' | (crear=1) |
| `json_ref` | '' | |
| `session_empresa` | '12355' | leer del HTML actual |
| `session_usuario` | 'origensilvestre.col@gmail.com' | leer del HTML actual |

### Inputs visibles (texto)
| Campo | Default | Notas |
|---|---|---|
| `fecha_compra` | hoy (`2026-05-04` formato YYYY-MM-DD) | |
| `trm` | '1' | TRM moneda |
| `remision_proveedor` | '' | número de remisión externa del proveedor |
| `descuento_global` | '0.00' | |
| `articulo[]` | '' | id Effi del artículo |
| `descripcion[]` | '' | autocompleta al elegir artículo |
| `cantidad[]` | '1' | |
| `bruto[]` | '0' | calculado |
| `descuento[]` | '0' | |
| `total_concepto[]` | '0' | calculado |
| `bruto_transaccion` | '0' | suma totales |
| `subtotal_transaccion` | '0' | |
| `total_impuesto` | '0' | |
| `prontopago` | '' | descuento prontopago |
| `fecha_prontopago` | '' | |
| `valor_forma_pago[]` | '0.00' | |
| `valor_medio_pago[]` | '0.00' | |

### Selects
| Campo | Default seleccionado | Otras opciones probables |
|---|---|---|
| `sucursal` | '1' (Principal) | |
| `bodega` | 'default' (no seleccionada — hay que poner '1' para Principal) | |
| `centro_costos` | '1' (Principal) | |
| `divisa` | 'default' (hay que ponerla — probablemente 1 = COP) | |
| `direccion_proveedor` | 'default' (autocompleta al elegir proveedor) | |
| `t_egreso[]` | 'default' (tipo egreso por línea — probablemente 1=compra normal) | |
| `precio[]` | (sin options — input de texto numérico) | precio unitario |
| `impuestos[<id_concepto>][]` | '1' (IVA 19%) | otros: 5%, 0%, etc |
| `retencion[]` | 'default' | |
| `t_forma_pago[]` | 'default' (probablemente 1=Contado) | |
| `medio_pago[]` | '1' (Efectivo) | |
| `caja_medio_pago[]` | '1Ǆ2' (CAJA PRINCIPAL OS) | **separador `Ǆ`** entre cuenta y caja |
| `cuenta_medio_pago[]` | 'default' | |

### Textareas
| Campo | Default |
|---|---|
| `garantia` | '' |
| `observacion` | '' |
| `observacion_medio_pago[]` | '' |

## Estructura de body (a probar)

```python
payload = [
    # Header
    ('sucursal', '1'),
    ('bodega', '1'),
    ('centro_costos', '1'),
    ('divisa', '1'),  # PROBAR
    ('proveedor', '<id_proveedor>'),
    ('direccion_proveedor', '<id_direccion>'),  # auto al elegir proveedor
    ('fecha_compra', '2026-05-04'),
    ('remision_proveedor', ''),
    ('trm', '1'),
    ('descuento_global', '0.00'),
    ('garantia', ''),
    ('observacion', '...'),
    ('session_empresa', '12355'),
    ('session_usuario', 'origensilvestre.col@gmail.com'),
    ('action', '1'),
    ('json_ref', ''),

    # Por cada línea de concepto:
    ('id_concepto[]', '<random 21 dígitos>'),
    ('articulo[]', '<cod>'),
    ('descripcion[]', '<auto>'),
    ('t_egreso[]', '1'),  # PROBAR
    ('cantidad[]', '36'),
    ('precio[]', '2205'),
    ('descuento[]', '0'),
    ('bruto[]', '79380'),  # cantidad * precio
    ('total_concepto[]', '79380'),
    ('lote[]', ''),
    ('serie[]', ''),
    ('observacion_concepto[]', ''),
    ('gift[]', '0'),
    (f'impuestos[{id_concepto}][]', '1'),  # IVA 19%

    # Totales
    ('bruto_transaccion', '<suma>'),
    ('subtotal_transaccion', '<suma>'),
    ('total_descuento', '0'),
    ('total_impuesto', '<19%>'),
    ('total_retencion', '0'),
    ('total_transaccion', '<final>'),

    # Forma pago (mínimo: Contado/Efectivo)
    ('t_forma_pago[]', '1'),  # PROBAR (¿Contado=1?)
    ('valor_forma_pago[]', '<total>'),
    ('medio_pago[]', '1'),    # Efectivo
    ('caja_medio_pago[]', '1Ǆ2'),
    ('cuenta_medio_pago[]', 'default'),  # PROBAR
    ('valor_medio_pago[]', '<total>'),
    ('observacion_medio_pago[]', ''),

    # Anticipo (vacíos)
    ('sucursal_anticipo[]', ''),
    ('id_anticipo[]', ''),

    # Retención (vacíos)
    ('retencion[]', 'default'),
    ('valor_retencion[]', ''),
    ('base_retencion[]', ''),

    # Prontopago
    ('prontopago', ''),
    ('fecha_prontopago', ''),
]
```

## Pendiente para construir el script

1. **Validar** con 1 POST real (capturar con Chrome DevTools — pendiente de restart Claude — o con Playwright route hook)
2. Resolver IDs por nombre:
   - `proveedor` → buscar por NIT (Effi expone `/app/tercero/buscar` o similar)
   - `direccion_proveedor` → del proveedor seleccionado
   - `t_egreso[]` → tipo de egreso (probablemente 1=compra)
3. Construir `import_remision_compra_post.py` con la misma firma que `import_orden_produccion_post.py` (toma JSON, hace POST, parsea respuesta)

## Validación de éxito
Igual que en otros endpoints Effi: respuesta HTTP 200 NO garantiza éxito. Verificar `body == 'OK'` o JSON con `{ok: true}`. Cualquier otra cosa = fallo.

## Doc relacionado
- `.claude/skills/effi-tecnico/SKILL.md` §3 (3 endpoints artículos POST) + §13 (tokens cifrados)
- `scripts/import_orden_produccion_post.py` — patrón de referencia
- `scripts/import_articulo_crear_post.py` — patrón de referencia (defaults completos)
