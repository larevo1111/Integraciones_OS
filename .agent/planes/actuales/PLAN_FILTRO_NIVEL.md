# Plan: Filtro de visibilidad por nivel de usuario

**Fecha**: 2026-04-01
**Objetivo**: Un usuario solo ve datos de usuarios con nivel inferior + los propios.
**Commit antes del cambio**: `46e23df` (feat: recargarSidebar)

---

## Regla de negocio

- Usuario nivel N ve: sus propios datos + datos de usuarios con nivel < N
- Ejemplo: Santi (9) ve todo. Larevo (7) ve nivel 6 y menos + los propios. Jen (3) ve nivel 2 y menos + los propios.

---

## Implementación: Caché de niveles en memoria

### Paso 1: Crear caché de niveles en server.js

- Al iniciar el servidor, cargar `SELECT Email, Nivel_Acceso FROM sys_usuarios` de BD comunidad
- Guardar en objeto: `{ 'email': nivel, ... }`
- Refrescar cada 5 minutos con `setInterval`
- Si falla la query, mantener caché anterior (fallback seguro)

### Paso 2: Crear función helper `filtrarPorNivel(items, reqUsuario, campoEmail)`

- Recibe array de items, usuario del request, y nombre del campo que tiene el email
- Para tareas: filtrar por `responsables` (array de la tabla relacional)
- Para proyectos: filtrar por `responsables` (array de g_proyectos_responsables)
- Lógica: mantener item si ALGÚN responsable tiene nivel <= reqNivel O si reqEmail es responsable

### Paso 3: Aplicar en endpoints (solo en los GET que devuelven listas)

| Endpoint | Campo a filtrar | Notas |
|---|---|---|
| GET /api/gestion/tareas | responsables (array) | Lista principal |
| GET /api/gestion/tareas/completadas | responsables (array) | Completadas |
| GET /api/gestion/tareas/:id/subtareas | responsables (array) | Subtareas |
| GET /api/gestion/proyectos | responsables (array) | Sidebar + tablas |
| GET /api/gestion/jornadas/equipo | email del usuario | Jornadas equipo |

### Endpoints que NO se filtran (y por qué)

| Endpoint | Razón |
|---|---|
| GET /api/gestion/tareas/:id | Individual — si tiene el ID ya tiene acceso |
| GET /api/gestion/proyectos/:id | Individual |
| POST/PUT/DELETE tareas | Escritura — no son listas |
| POST/PUT/DELETE proyectos | Escritura |
| GET /api/gestion/categorias | Catálogo compartido |
| GET /api/gestion/etiquetas | Catálogo compartido |
| GET /api/gestion/usuarios | Lista de usuarios (necesaria para selectores) |
| GET /api/gestion/jornadas/hoy | Solo la propia |
| GET /api/gestion/ops, remisiones, pedidos | Datos de Effi, no tienen responsable |

---

## Archivos a modificar

1. **server.js** — SOLO este archivo:
   - Agregar caché de niveles (arriba, después de las constantes)
   - Agregar función `filtrarPorNivel()`
   - Aplicar en 5 endpoints GET

## Archivos que NO se tocan

- Frontend (no cambia nada visual)
- Base de datos (no se crean tablas)
- Router, stores, componentes

---

## Verificación

1. Santi (nivel 9): ve todas las tareas/proyectos
2. Si existiera usuario nivel 3: solo vería sus tareas + las de nivel 2 y 1
3. Catálogos (categorías, etiquetas, usuarios): se siguen viendo completos
4. Crear/editar tarea: sigue funcionando igual
5. Jornadas equipo: solo ve jornadas de usuarios con nivel inferior

---

## Rollback

Si hay problemas: `git revert HEAD` o `git reset --hard 46e23df`
