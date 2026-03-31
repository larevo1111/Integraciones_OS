# Inventario OS — Políticas de Acceso y Seguridad

## Archivo de configuración

**`inventario/politicas.json`** — fuente de verdad única para permisos.

El frontend carga este archivo al iniciar y aplica `v-if` por acción.
Para cambiar permisos: editar el JSON, rebuild frontend, reiniciar servicio.

## Niveles de usuario

Los niveles vienen del JWT de autenticación (campo `nivel`), que se hereda
de `sys_usuarios.Nivel_Acceso` en la BD `os_comunidad` de Hostinger.

| Nivel | Perfil | Acciones permitidas |
|---|---|---|
| 1 | Contador | Ver inventario, contar, notas, fotos |
| 3 | Coordinador | + Agregar artículos no listados |
| 5 | Supervisor | + Nuevo inventario, reiniciar, cerrar, ver auditoría |
| 7 | Admin | + Eliminar inventario, administrar rangos/unidades |

## Acciones y nivel mínimo requerido

| Acción | Nivel | Descripción |
|---|---|---|
| `ver_inventario` | 1 | Ver artículos y conteos |
| `contar` | 1 | Registrar conteo físico |
| `agregar_nota` | 1 | Agregar notas a artículos |
| `tomar_foto` | 1 | Tomar foto de artículo |
| `agregar_articulo` | 3 | Agregar artículo no listado a bodega |
| `nuevo_inventario` | 5 | Crear evento de inventario con fecha de corte |
| `reiniciar_inventario` | 5 | Borrar conteos de un inventario (mantiene artículos) |
| `cerrar_inventario` | 5 | Cerrar inventario (bloquea edición de conteos) |
| `ver_auditoria` | 5 | Ver historial de cambios |
| `administrar_rangos` | 7 | Editar rangos y unidades |
| `eliminar_inventario` | 7 | Eliminar un inventario completo |

## Cómo se aplica en el frontend

Cada control usa la función `puede(accion)`:

```javascript
// En el template:
<button v-if="puede('nuevo_inventario')" ...>

// En el script:
function puede(accion) {
  const config = politicas.acciones[accion]
  return config && nivelUsuario >= config.nivel_minimo
}
```

## Cómo agregar un nuevo permiso

1. Agregar la acción en `politicas.json` → `acciones`
2. En el frontend, usar `v-if="puede('nombre_accion')"` en el componente
3. Documentar aquí en la tabla de acciones

## Auditoría

Toda acción que modifica datos queda registrada en `inv_auditorias`:
- Quién (usuario)
- Cuándo (timestamp)
- Qué cambió (valor anterior → nuevo)
- Tipo de acción (conteo, edición, nota, foto, reinicio, cierre)
