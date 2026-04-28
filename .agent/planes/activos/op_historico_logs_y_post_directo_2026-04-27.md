# Plan — Histórico OPs + observación nueva + POST directo (espía)

## Pedido de Santi (2026-04-27)

1. Cambiar formato de **observación** de la OP creada:
   - **Antes**: `"OP solicitudes #69,68"`
   - **Ahora**: `"Crema de mani 130g, crema de mani 230g, etc - Usr: Santiago S - Op Solicitudes #69,68"`
   - Orden: `<lista productos> - Usr: <nombre usuario> - Op Solicitudes <ids>`

2. **Tabla histórica `prod_ops_creadas`** con todo lo que se programa:
   - Columnas: id, op_effi, fecha, usuario, solicitudes_ids, payload_json (lo enviado a Effi), log_creacion (stdout/stderr), duracion_seg, estado, error
   - Permite auditar quién creó qué OP, con qué materiales/cantidades editadas, y revisar logs si hay falla

3. **Logs detallados** del proceso:
   - Stdout del script Playwright capturado en BD
   - Tiempo total medido
   - Si falla, error capturado para debug

4. **POST directo (background)**: investigar si Effi acepta POST HTTP directo saltándose Playwright. Si funciona, OPs bajan de 60-90s a ~3-5s. Espía en paralelo mientras Santi sigue trabajando.

## Implementación

### 4.A Backend (sync, tarea principal)
- Migración SQL: `CREATE TABLE prod_ops_creadas`
- Modificar `POST /api/produccion/crear-op-effi`:
  - Tomar usuario del JWT (nuevo: `Depends(require_auth)`)
  - Construir observación con formato nuevo (productos primero, usuario, solicitudes)
  - Capturar duración (`time.time()` antes/después)
  - INSERT en `prod_ops_creadas` con todo (payload + log + duración)
  - Si falla, INSERT con `estado='error'` + `error=stderr`
- Nuevo endpoint `GET /api/produccion/ops-historico` (opcional, futuro UI para listar)

### 4.B Frontend (mínimo)
- El dialog ya envía solicitudes_ids/materiales/productos/otros_costos. No hay cambios.
- Header de Authorization ya va automático.

### 4.C Background (espía POST directo)
- Script `_espiar_post_op.js` mejorado: corregir selectores del form
- Capturar la request final POST (no las de telemetría New Relic)
- Documentar URL, headers, formato del payload en `.agent/docs/EFFI_POST_DIRECTO.md`
- Si funciona: implementar versión Python con `requests.post` para reemplazar Playwright

## Estado
- 1 (observación): TODO
- 2 (tabla histórica): TODO
- 3 (logs): TODO
- 4 (POST directo): background (resultado en .agent/docs/EFFI_POST_DIRECTO.md)
