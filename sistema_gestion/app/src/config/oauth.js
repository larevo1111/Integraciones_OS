// Google OAuth config — hardcoded EN CÓDIGO a propósito.
//
// El client_id de Google OAuth es PÚBLICO (queda visible en el HTML del iframe
// del botón "Continuar con Google" — cualquiera lo ve abriendo DevTools). NO es
// un secret y NO necesita variables de entorno.
//
// Histórico (incidente 4-may-2026 → 6-may-2026):
//   1. Estaba en .env (gitignored). El 4-may alguien hizo `npm run build` en el
//      VPS sin .env → bundle quedó con clientId: undefined.
//   2. El Service Worker propagó la versión rota a usuarios el 6-may → login
//      empezó a fallar con "Missing required parameter: client_id".
//   3. Se intentó migrar a `quasar.config.js > build.env` pero ese mecanismo no
//      inyecta `import.meta.env.VITE_*` correctamente en este setup → bundle
//      quedaba igual con `clientId: void 0`.
//   4. Solución definitiva: import desde este archivo committeado. Sin
//      variables de entorno, sin .env, sin plugins de Vite. Cualquier
//      `npm run build` en cualquier servidor genera el bundle correcto.
//
// Si en algún momento se necesita rotar el client_id, se cambia acá y se
// hace commit. Punto.
export const GOOGLE_CLIENT_ID = '290093919454-j2l1el0p624v65cada556pdc3r2gm6k7.apps.googleusercontent.com'
