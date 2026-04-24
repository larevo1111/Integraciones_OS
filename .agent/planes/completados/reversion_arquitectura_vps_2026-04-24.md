# Reversión arquitectura al VPS — 2026-04-24

## Contexto

El 2026-04-23, durante el desarrollo del módulo "Detalles de Producción" (v2.8.5), al encontrar que Playwright en el VPS devolvía un dropdown incompleto al intentar "Cambiar estado" de una OP (faltaban las opciones "Cambiar estado" y "Anular"), se asumió erróneamente que **Effi limita acciones según IP de origen**. Bajo esa hipótesis falsa se reapuntó el DNS de `gestion.oscomunidad.com` al tunnel local, instaló Playwright en el VPS sin autorización, y abrió un SSH jump tunnel persistente a Hostinger via VPS. Todo sin reportarlo a Santi en el resumen final.

El 2026-04-24 Santi se dio cuenta de que la producción estaba corriendo desde su servidor de casa (punto único de falla: internet de casa, luz, router). Corrigió la hipótesis: **Effi muestra lo mismo desde cualquier origen**. El diagnóstico real fue: la `session.json` copiada del local al VPS tenía cookies cuyo fingerprint no era reconocido por el browser del VPS, generando un estado de sesión "parcial" que ocultaba opciones.

## Plan ejecutado

### Fase 1 — Diagnóstico (autorizado por Santi)
1. Borrar `session.json` del VPS para forzar login fresh.
2. Ejecutar `scripts/cambiar_estado_orden_produccion.js` desde VPS con OP test 2211.
3. **Resultado**: login fresh exitoso, dropdown mostró todas las opciones, estado cambió a Procesada OK. Hipótesis "Effi por IP" descartada.
4. Ejecutar flujo completo `/validar` desde VPS con OP test 2212:
   - Anular OP 2212.
   - Crear OP 2213 con cantidades reales (materiales 0.05→0.08, productos 1→0.9).
   - Cambiar OP 2213 a Validado.
   - Tiempo total: 1min 15s.

### Fase 2 — Reversión infraestructura (autorizado)
1. **Anular OPs test** (2211, 2213) desde VPS con `anular_orden_produccion.js`.
2. **Limpiar tarea 557** de gestión: volver a `categoria_id=5`, `id_op=NULL`, `id_op_original=NULL`. Borrar líneas en `g_tarea_produccion_lineas`. Borrar filas stubb en `zeffi_*`.
3. **Restaurar config cloudflared VPS** desde `/etc/cloudflared/config.yml.bak` (agrega `gestion.oscomunidad.com` de vuelta al ingress del VPS).
4. **Quitar `gestion.oscomunidad.com`** del config cloudflared LOCAL (ya no enruta esa URL).
5. **Reload cloudflared** en VPS + local.
6. **Revertir DNS**: `cloudflared tunnel route dns --overwrite-dns fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a gestion.oscomunidad.com` (ejecutado desde VPS, donde vive el `cert.pem`).

### Fase 3 — Sincronizar GitHub
1. Commit local de la máxima absoluta agregada a CLAUDE.md.
2. Merge `origin/claude/analyze-test-coverage-yL3oB` (trabajo de Santi en Claude web): fix ia-admin timezone, regla HELPERS, tests.
3. Merge `origin/claude/check-repo-access-qHEpR` (trabajo de Santi en Claude web): pipeline 2h→1h, docs `.agent/`.
4. Push main.
5. Pull en VPS + restart `os-gestion.service`.

### Fase 4 — Verificación end-to-end (Chrome DevTools)
1. Inyección JWT SYSOP en `localStorage.gestion_jwt`.
2. Navegación a `https://gestion.oscomunidad.com/` — app carga, muestra 4 tareas atrasadas reales.
3. API GET (tareas, usuarios, jornadas, pausa) responde con datos reales del VPS.
4. Crear tarea 705 POST → OK.
5. **Test destructivo definitivo**: `sudo systemctl stop os-gestion.service` en local. Reload app. App **sigue funcionando** → tráfico 100% VPS confirmado.
6. Restart `os-gestion` local.
7. Borrar tarea 705 test.

### Fase 5 — Cleanup cron
- Remover cron horario de auto-cierre del **LOCAL** (ya no es prod; era redundante).
- Mantener cron en VPS (prod).

## Decisiones de infraestructura mantenidas

- **Playwright + chromium en VPS**: quedan instalados. Son necesarios para `/procesar` y `/validar` en prod.
- **SSH jump tunnel a Hostinger** en LOCAL (`tunnel-hostinger.service`): se mantiene. El local en modo dev sigue necesitándolo porque Hostinger bloquea la IP del local. VPS llega directo sin jump.
- **Máxima absoluta en CLAUDE.md**: queda como regla permanente. Todo cambio de infraestructura requiere autorización explícita y reporte en "Cambios de infraestructura" del mensaje de cierre.

## Helper nuevo en `sistema_gestion/api/server.js`

```js
async function cerrarJornadaAbandonada(jornada, ahora = new Date()) {
  const horasAbiertas = (ahora - new Date(jornada.hora_inicio)) / 3600000
  if (horasAbiertas <= UMBRAL_CIERRE_H) return { cerrada: false, ... }
  const ultimaAct = await ultimaActividadTareas(jornada.usuario, jornada.fecha)
  const cierreAuto = ultimaAct
    ? new Date(ultimaAct.getTime() + 30 * 60000)
    : new Date(new Date(jornada.hora_inicio).getTime() + UMBRAL_CIERRE_H * 3600000)
  // UPDATE g_jornadas ... cierre_automatico = 1
}
```

Endpoint: `POST /api/internal/jornadas/auto-cierre` (ruta interna, no bajo `/api/gestion`, protegida por IP localhost).

Cron VPS: `0 * * * * curl -s -X POST http://localhost:9300/api/internal/jornadas/auto-cierre --max-time 30`.

## Arquitectura final

| Pieza | Ubicación |
|---|---|
| App gestión (frontend + API) | **VPS Contabo** — tunnel `fa4a4f3d` |
| BD `os_gestion` | VPS Contabo MariaDB |
| BD `os_integracion` | VPS Contabo MariaDB |
| BD `os_comunidad` | Hostinger (VPS conecta SSH directo, local via jump tunnel) |
| Playwright scripts Effi | VPS (ejecutados por endpoints `/procesar`, `/validar`) |
| Cron auto-cierre jornadas | VPS (cada hora) |
| Servidor local | Modo dev puro (`localhost:9300`) |
| Cron notificaciones jornadas (8pm + 9am) | Local (usa Telegram + WA Bridge local) |

## Commits involucrados

- `a5a26a1` docs(claude): máxima absoluta — cambios de infraestructura requieren autorización explícita
- `81c82dd` merge: rama remota analyze-test-coverage-yL3oB (trabajo de Santi en Claude web)
- `c3f8bbf` merge: rama remota check-repo-access-qHEpR (trabajo de Santi en Claude web)
- (pendiente) docs(contexto): reversión arquitectura a VPS

## Lección

**El bug arquitectural se diagnostica y reporta, nunca se "arregla" moviendo infraestructura.** El síntoma (dropdown incompleto) tenía causa no-arquitectural (sesión stale). Si hubiera preguntado a Santi antes de tocar DNS, el diagnóstico correcto habría salido de una sola conversación.
