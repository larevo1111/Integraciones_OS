# Plan — Test y Puesta a Punto de Agentes IA para Demo

**Fecha**: 2026-05-08
**Owner**: Claude Code
**Motivo**: Demo de Santi mañana (2026-05-09). Dejar el ia_service y los super agentes confiables y bien configurados.

## Contexto / hallazgos del arranque

- Estoy ejecutando desde el **VPS Contabo** (`94.72.115.156`).
- El `ia_service` (puerto 5100) y los **Super Agentes** (Claude Code y OpenCode subprocess) viven en el **servidor local de casa**, no en el VPS.
- Acceso público al ia_service: vía `https://ia.oscomunidad.com/api/ia/*` (Express del admin proxea al servicio).
- Todos los endpoints `/api/ia/*` requieren JWT (Bearer). Generador: `scripts/gen_jwt_dev.sh` → JWT 7 días para SYSOP / Ori_Sil_2 con nivel 9.
- Health: `{"status":"ok","db":"ok","ia_service":"ok"}` ✅
- 17 agentes en BD, 16 activos. Todos con API key. Verificado smoke test con gemini-flash → respuesta OK, $0.000129 / 1684 tokens.
- No hay endpoint público para **ejecutar** Super Agentes. Los SA solo se disparan desde el bot Telegram (en server local). El admin web solo permite lectura de config y sesiones.

## Decisiones acordadas con Santi

- Agente principal del ia_service para la demo: **gemini-flash**.
- Cambios sólo en BD vía endpoints admin web (no SSH al server local, no tocar Python).
- Tests rigurosos: 10 al ia_service, ~10 a cada SA. Para SA → smoke check (limitación de acceso, ver más abajo).

## Alcance ajustado

**A. ia_service normal con gemini-flash forzado (10 tests)**

| # | Tipo | Pregunta | Criterio OK |
|---|---|---|---|
| 1 | analisis_datos (SQL) | "¿Cuánto vendimos hoy?" | respuesta con cifra o "no hay ventas hoy" + sql ejecutado |
| 2 | analisis_datos (SQL) | "Top 5 clientes por ventas en abril" | tabla con 5 filas |
| 3 | analisis_datos (SQL) | "¿Cuántas órdenes de producción hay vigentes?" | cifra correcta |
| 4 | analisis_datos (SQL) | "Stock actual de tabletas chocolate templado" | cifras por SKU |
| 5 | conversacion | "Qué es la mercancía en consignación, en una línea" | texto claro |
| 6 | conversacion | "Cómo se calcula el costo de una OP en Effi" | explicación |
| 7 | conversacion + memoria | "Y cómo se diferencia del costo realizado?" (follow-up del 6) | continúa hilo |
| 8 | redaccion | "Redactá un email de seguimiento al cliente Cía Nacional sobre la cotización 1610" | email completo |
| 9 | redaccion | "Hacé un resumen ejecutivo de 3 viñetas sobre las ventas de abril" | 3 bullets |
| 10 | clasificacion (utilitaria /ia/simple) | "Despachar pedido a Muebles La 33" → enum [Ventas, Logistica, Producción, Soporte] | "Logistica" |

Para cada test registrar: latencia, tokens in/out, costo, agente final, formato, ¿pasa criterio?, comentario.

**B. Configuración a aplicar antes de los tests**

1. `bot_sesiones`: cambiar agente_preferido del usuario admin (santi) de `ollama-qwen-coder` → `gemini-flash`.
2. `ia_tipos_consulta`:
   - `conversacion.agente_preferido` → `gemini-flash`
   - `redaccion.agente_preferido` → `gemini-flash`
   - `clasificacion.agente_preferido` → `gemini-flash`
   - (Mantener `analisis_datos.agente_preferido = gemini-flash` que ya está.)
3. Verificar que `gemini-flash` tenga `nivel_minimo<=1` y `activo=1`.

**C. Smoke check Super Agentes** (limitado — acceso solo a metadata)

Para cada SA (Claude Code + OpenCode):
1. GET `/api/ia/superagente/config` — verificar config presente (binario, modelo, timeout, etc.)
2. GET `/api/ia/superagente/sesiones?limit=10` — verificar últimas sesiones, ver si hubo errores
3. Inspeccionar `sa_sesiones` y `sa_cambios` recientes — última actividad, fallas
4. Si no hay sesiones recientes (<24h): pedir a Santi una sesión rápida via Telegram para validar antes de la demo.

**Limitación honesta**: no puedo ejecutar `claude -p` ni `opencode` desde el VPS. La demo de los SA debe hacerse desde el bot Telegram de Santi.

## Plan de ejecución

1. ⏳ Aplicar config (default gemini-flash) → `PUT /api/ia/agentes-admin/...` y `PATCH /api/ia/tipos-admin/...`
2. ⏳ Ejecutar los 10 tests del ia_service via `POST /api/ia/consultar` (forzando agente=gemini-flash o NULL para usar default)
3. ⏳ Smoke check SA (lectura de config + sesiones recientes)
4. ⏳ Si algún test falla: ajustar config en BD vía web admin y re-correr
5. ⏳ Reporte final en `.agent/informes/test_agentes_2026-05-08/REPORTE.md` con:
   - Tabla de los 10 tests con resultados
   - Estado de SA (config + última actividad)
   - Costo total de la sesión de tests
   - Checklist de "todo listo para demo" o "estos 3 puntos requieren atención"

## Cambios de infraestructura
**Ninguno previsto.** Sólo cambios en BD `ia_service_os` vía endpoints autenticados del admin web.

## Estado
**✅ Completado — 2026-05-08** (con salvedad de 2 tests SA via Telegram que dependen de Santi)

### Resultados
- ia_service con `gemini-flash`: **10/10 tests OK**, costo $0.0093 USD
- Super Agentes: config OK, sesiones requieren validación Telegram (no se pueden ejecutar desde VPS)
- 2 bugs identificados y registrados en PENDIENTES.md (P2, no bloquean demo)

### Reporte completo
[.agent/informes/test_agentes_2026-05-08/REPORTE.md](../../informes/test_agentes_2026-05-08/REPORTE.md)

### Datos crudos
- [.agent/informes/test_agentes_2026-05-08/ia_service_tests.csv](../../informes/test_agentes_2026-05-08/ia_service_tests.csv)
- [.agent/informes/test_agentes_2026-05-08/ia_service_tests.json](../../informes/test_agentes_2026-05-08/ia_service_tests.json)
- [.agent/informes/test_agentes_2026-05-08/super_agentes_smoke.txt](../../informes/test_agentes_2026-05-08/super_agentes_smoke.txt)

→ Mover a `.agent/planes/completados/` después de que Santi confirme tests SA via Telegram.
