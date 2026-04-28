# Effi — POST directo para crear OP (investigación)

**Fecha**: 2026-04-27
**Método**: Espionaje con Playwright + interceptor `page.on('request')` durante la creación de OP 2219.

## Endpoint final identificado

```
POST https://effi.com.co/app/orden_produccion/crear
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Referer: https://effi.com.co/app/orden_produccion
Cookie: <sesión laravel/php>
```

**Status response**: 200 (sin body — Effi devuelve éxito vacío + el id de OP queda en `MAX(id_orden)`)

## Payload (form-urlencoded)

### Campos generales
| Campo | Ejemplo | Notas |
|---|---|---|
| `sucursal` | `1` | Siempre 1 (Principal) |
| `bodega` | `1` | 1 = Principal |
| `fecha_inicio` | `27/04/2026` | Formato DD/MM/YYYY |
| `fecha_fin` | `27/04/2026` | DD/MM/YYYY |
| `encargado` | **`536`** | ⚠️ ID INTERNO de empleado, NO el CC. Hay que mapear CC → ID. |
| `observacion` | `ESPIA POST - test min` | Texto libre |
| `tercero` | `` (vacío) | Opcional |
| `maquina` | `default` | Constante |
| `session_empresa` | `12355` | Hidden field (de la sesión) |
| `session_usuario` | `origensilvestre.col@gmail.com` | Hidden field (de la sesión) |

### Materiales (arrays con `[]`)
- `articuloM[]` = cod material (ej: `114`)
- `cantidadM[]` = cantidad (ej: `0.05`)
- `costoM[]` = costo formato **"17,000"** (con coma, sin punto)
- `loteM[]` = `` (vacío default)
- `serieM[]` = `` (vacío default)
- `descripcionM[]` = nombre del material (ej: `MANI SIN CASCARA TOSTADO X KILO`)

### Productos (arrays con `[]`)
- `articuloP[]`, `cantidadP[]`, `precioP[]`, `loteP[]`, `serieP[]`, `descripcionP[]`

### Otros costos (arrays con `[]`)
- `costo_produccion[]` = tipo_costo_id (ej: `13`)
- `cantidad[]` = horas (ej: `0.5`)
- `costo[]` = costo formato `"7,000"`

### Totales calculados (Effi los acepta y los recalcula)
- `costo_material` = suma materiales
- `otros_costos` = suma otros
- `precio_venta` = suma precios × cantidades
- `beneficio` = venta − costo total

## Otros endpoints internos descubiertos

```
POST /app/sucursal/llena_campos_vigentes_sucursal       (al cambiar sucursal)
POST /app/articulo/llena_articulo_buscar_stock          (al seleccionar artículo en modal)
POST /app/tercero/tercero/llena_tercero_buscar          (busca encargado por CC)
POST /app/orden_produccion/llena_costos_produccion      (lista tipos de costo)
```

→ El `llena_tercero_buscar` es el que resuelve `CC 74084937 → ID interno 536`. **Este HAY que llamarlo primero** para obtener el ID.

## Implementación propuesta (Python)

```python
import requests, json
from urllib.parse import urlencode

# 1. Cargar sesión (cookies extraídas de Playwright storage_state)
with open('scripts/session.json') as f:
    state = json.load(f)
cookies = {c['name']: c['value'] for c in state['cookies']}

s = requests.Session()
s.cookies.update(cookies)
s.headers.update({
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://effi.com.co/app/orden_produccion',
    'User-Agent': 'Mozilla/5.0 ...',
})

# 2. Resolver encargado CC → ID interno
r = s.post('https://effi.com.co/app/tercero/tercero/llena_tercero_buscar',
           data={'busqueda': '74084937'})
encargado_id = parse_id_from_response(r.text)  # 536

# 3. Construir payload con arrays []
data = [
    ('sucursal', '1'),
    ('bodega', '1'),
    ('fecha_inicio', '27/04/2026'),
    ('fecha_fin', '27/04/2026'),
    ('encargado', str(encargado_id)),
    ('observacion', 'OP creada vía POST'),
    ('tercero', ''),
    ('maquina', 'default'),
    ('session_empresa', '12355'),
    ('session_usuario', 'origensilvestre.col@gmail.com'),
    # ... totales calculados
    ('costo_material', '850'),
    ('otros_costos', '3500'),
    ('precio_venta', '5997'),
    ('beneficio', '1647'),
]
# Materiales
for m in materiales:
    data.append(('articuloM[]', m['cod']))
    data.append(('cantidadM[]', str(m['cantidad'])))
    data.append(('costoM[]', formato_coma(m['costo'])))   # "17,000"
    data.append(('loteM[]', m.get('lote', '')))
    data.append(('serieM[]', m.get('serie', '')))
    data.append(('descripcionM[]', m['nombre']))
# Productos: igual
# Costos: igual

# 4. Enviar
r = s.post('https://effi.com.co/app/orden_produccion/crear', data=data)
# OP ID se obtiene de SELECT MAX(id_orden) FROM ... después
```

## Tiempo estimado

| Método | Tiempo OP |
|---|---|
| Playwright actual | 60-90s |
| POST directo (este) | 2-5s |

## Riesgos

1. **CSRF token**: el form HTML normalmente lleva `_token` o `csrf_token` hidden. NO apareció en este POST. Significa que Effi NO valida CSRF en este endpoint (probable, dado que es legacy). Verificar.
2. **Sesión expirada**: si las cookies caducan, hay que regenerar con Playwright (igual que ahora — ya tenemos `scripts/session.js`).
3. **Cambios en el form**: si Effi cambia los nombres de campos, el POST se rompe. Playwright es más resiliente.
4. **Validaciones en backend**: Effi puede rechazar ciertos formatos. Probar a fondo antes de migrar.

## Próximos pasos (NO implementar sin autorización de Santi)

1. Crear `scripts/import_orden_produccion_post.py` (Python con `requests`)
2. Probar con OP de ensayo y comparar tiempo + resultado vs Playwright
3. Si funciona, migrar `_ejecutar_op_background` para usar Python en vez de subprocess Node
4. Mantener Playwright como fallback (si POST falla por algo, reintentar con script viejo)

## OP creada en este test
**OP 2219** en Effi (ya está creada — anular manualmente).
