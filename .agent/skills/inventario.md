# Skill: Inventario Físico OS

## Cuándo usar
Al trabajar en el módulo de inventario físico: app web, scripts de depuración, API, conteos, validación de unidades.

## Contexto rápido
- **App**: `inv.oscomunidad.com` — Vue 3 + Vite frontend, FastAPI backend
- **Puerto**: 9401 — systemd `os-inventario-api.service`
- **BD**: `os_inventario` — tablas: `inv_conteos`, `inv_rangos`, `inv_auditorias`
- **Auth**: Google OAuth (JWT compartido con sistema_gestion, mismo secret)
- **Frontend**: `inventario/frontend/src/App.vue` (componente único)
- **Backend**: `scripts/inventario/api.py`
- **Config**: `inventario/politicas.json` (permisos), `scripts/inventario/config_depuracion.json` (exclusiones)

## Archivos clave

| Archivo | Propósito |
|---|---|
| `scripts/inventario/api.py` | FastAPI — API REST + sirve frontend |
| `scripts/inventario/depurar_inventario.py` | Genera filas en inv_conteos por fecha |
| `scripts/inventario/calcular_rangos.py` | Genera inv_rangos (unidades, grupos, rangos) |
| `scripts/inventario/config_depuracion.json` | Reglas de exclusión de artículos |
| `inventario/frontend/src/App.vue` | Frontend completo (login + tabla + modales) |
| `inventario/frontend/src/styles.css` | Variables CSS design system OS |
| `inventario/politicas.json` | Permisos por acción y nivel de usuario |
| `inventario/POLITICAS_ACCESO.md` | Documentación de políticas |
| `inventario/fotos/` | Fotos capturadas durante conteo |

## Grupos de artículos
- **MP** (Materia Prima): T01.xx sin aparición en OPs
- **PP** (Producto en Proceso): producido en OPs (cruce con zeffi_articulos_producidos)
- **PT** (Producto Terminado): categoría TPT.xx
- **INS** (Insumos): categoría T03.xx
- **DS** (Desarrollo): categoría DESARROLLO DE PRODUCTO

## Comandos frecuentes

```bash
# Crear inventario para una fecha
python3 scripts/inventario/depurar_inventario.py --fecha 2026-03-31

# Regenerar rangos y grupos
python3 scripts/inventario/calcular_rangos.py

# Reiniciar servicio
sudo systemctl restart os-inventario-api

# Build frontend
cd inventario/frontend && npx vite build

# Test API
curl -s "http://127.0.0.1:9401/api/inventario/resumen?fecha=2026-03-31&bodega=Principal"
```

## Gotchas
- El reloj usa DOM directo (getElementById), NO ref reactivo — para no causar re-render que borre inputs
- Input de conteo: `type="text"` + `inputmode="decimal"` (acepta punto y coma)
- `guardarConteo()` actualiza `articulo.inventario_fisico` ANTES del await fetch
- Fotos se guardan en `inventario/fotos/` con UUID, referencia en inv_conteos.foto
- Frontend build va a `inventario/static/` (FastAPI lo sirve)

## Contexto detallado
`.agent/contextos/inventario_fisico.md`
