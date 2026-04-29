# Migración Producción + Inventario al VPS Contabo — 2026-04-28

## Objetivo
Mover las APIs `os-produccion-api` (puerto 9600) y `os-inventario-api` (puerto 9401) del servidor local al VPS Contabo, eliminando el SSH tunnel hacia la BD `inventario_produccion_effi` (la BD ya está en VPS). Beneficios: cero problemas de tunnel SSH, latencia menor, paridad con Sistema Gestión.

## Principio aplicado
Ver MANIFESTO §8A: paths/hosts relativos. La migración NO debe tocar código — solo `.env`, service files y DNS.

## Fase A — Repo (versionable, sin tocar infra)
- [x] Documentar regla "paths relativos" en CLAUDE.md y MANIFESTO §8A
- [x] `.env.example`: documentar modo `direct` (BD local en mismo servidor)
- [x] Service file `scripts/produccion/os-produccion-api.service`
- [x] Service file `scripts/inventario/os-inventario-api.service` (limpiar dep `mariadb.service`)
- [x] Este plan

## Fase B — Setup en VPS (yo, con OK genérico de Santi)
1. SSH al VPS, `git pull` en `/home/osserver/Proyectos_Antigravity/Integraciones_OS`
2. Crear `integracion_conexionesbd.env` en VPS (no en git) con:
   - `DB_INVENTARIO_SSH_HOST=direct` + `DB_INVENTARIO_REMOTE_HOST=127.0.0.1` + `DB_INVENTARIO_REMOTE_PORT=3306`
   - `DB_INTEGRACION_SSH_HOST=direct` + `DB_INTEGRACION_REMOTE_HOST=127.0.0.1` + `DB_INTEGRACION_REMOTE_PORT=3306`
   - Resto de variables (creds, DB_NAME) iguales al local
3. Buildear frontend Producción en VPS: `cd produccion && npm install && npm run build`
4. Copiar `scripts/session.json` del local al VPS (cookies activas Effi — fuera del repo, sensible)
5. Copiar service files a `/etc/systemd/system/` (ajustar `WorkingDirectory` si distinto)
6. `systemctl daemon-reload && systemctl enable --now os-produccion-api os-inventario-api`
7. Verificar `curl localhost:9600/api/recetas?limit=1` y `curl localhost:9401/api/inventario/inconsistencias?limit=1` desde el VPS

## Fase C — Cloudflared del VPS (cambio de infra, requiere OK)
1. Editar `/etc/cloudflared/config.yml` del VPS: cambiar `inv.oscomunidad.com` de `localhost:9401` a `localhost:9600` (porque el frontend completo lo sirve la API de Producción)
2. `systemctl restart cloudflared` en VPS

## Fase D — DNS Cloudflare (cambio de infra, requiere OK explícito)
1. En Cloudflare DNS: cambiar CNAME de `inv.oscomunidad.com` para que apunte al tunnel del VPS (`fa4a4f3d-5eeb-43fa-ae09-b838e084bb9a.cfargotunnel.com`) en lugar del local (`9cacb3dc-...cfargotunnel.com`)
2. Esperar propagación (~1 min)
3. Verificar desde fuera: `curl -I https://inv.oscomunidad.com`

## Fase E — Apagado del local (post-migración exitosa)
1. Quitar entry `inv.oscomunidad.com` de `/etc/cloudflared/config.yml` LOCAL
2. `systemctl restart cloudflared` local
3. `systemctl stop os-produccion-api os-inventario-api` local (NO disable — dejar como respaldo)
4. Esperar 1 semana antes de `disable`

## Riesgos / Rollback
- Si después del corte DNS algo falla: cambiar el CNAME de vuelta al tunnel local. La app local sigue prendida hasta Fase E.
- Si el VPS cae: las apps caen también (igual que Gestión).

## Tareas para Subagentes
- Ya se usó Explore para mapear arquitectura (reporte en conversación).

## Tareas para Antigravity
- Ninguna en esta tarea.

## Estado
- 2026-04-28: Fase A completada. Listo para Fase B.
