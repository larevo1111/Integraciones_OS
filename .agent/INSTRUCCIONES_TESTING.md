# Instrucciones de Testing — ERP Origen Silvestre

## Roles y división de responsabilidades

| Rol | Hace |
|---|---|
| **Claude Code** | Implementa la feature, hace build, reinicia el servicio, y **asigna la tarea de QA a Antigravity** con contexto claro: qué se construyó, qué endpoints existen, qué tablas se modificaron, qué debe verificarse. **No dicta cómo usar las herramientas.** |
| **Antigravity** | Recibe la tarea y decide autónomamente cómo verificarla — qué herramientas usar, en qué orden, qué queries correr. Reporta hallazgos y documenta bugs. |
| **Santi** | Aprueba o rechaza el resultado final. |

**Principio clave: Claude Code asigna la tarea con contexto. Antigravity decide cómo ejecutarla.**

---

## Herramientas disponibles para Antigravity

Antigravity tiene acceso completo a Bash, mysql, curl, Read, Write, y Playwright. Decide cuál usar según la tarea:

- **curl / mysql** — para la mayoría de verificaciones: endpoints, integridad de datos, sumas, comparativos
- **Playwright** — solo cuando sea estrictamente necesario ver el browser (hover de tooltips, layout visual)
- **Bash / Read** — logs, servicios, archivos

**Regla de oro:** si se puede verificar sin abrir un browser → no abrir el browser.

**App en producción:** `http://menu.oscomunidad.com` (Cloudflare tunnel → puerto 9100 local)
**API local:** `http://localhost:9100/api/...`

---

## Protocolo de screenshots

### Dónde guardar
- **Screenshots de QA activo** (bugs sin resolver):
  `/home/osserver/Proyectos_Antigravity/Integraciones_OS/screenshots_temporales/`
- **Screenshots de referencia de diseño** (patrones correctos para recordar):
  `frontend/design-system/screenshots/` (actualizar `INDEX.md`)

### Nomenclatura obligatoria
```
<modulo>_<descripcion_breve>_<timestamp>.png
```
Ejemplos:
- `cartera_kpis_correctos_1773280375377.png`
- `cartera_tabla_vacia_bug_1773280482441.png`
- `tooltips_año_anterior_ok_1773280513712.png`

### Ciclo de vida de screenshots temporales
1. Bug encontrado → screenshot guardado en `screenshots_temporales/`
2. Bug reportado en `QA_REGISTRO.md`
3. Claude Code corrige el bug
4. Antigravity verifica la corrección → nuevo screenshot si aplica
5. **Bug resuelto → borrar screenshots asociados** de `screenshots_temporales/`
6. Si el screenshot muestra un patrón de diseño importante → mover a `design-system/screenshots/` y actualizar `INDEX.md`

---

## Protocolo de reporte

### Archivo de registro: `.agent/QA_REGISTRO.md`
Cada sesión de testing genera entradas en este archivo.
**Nunca sobreescribir entradas anteriores** — agregar siempre al final o actualizar el estado de bugs existentes.

### Estructura de un reporte de bug
```markdown
### BUG-XXX — [Módulo] Descripción breve
**Fecha:** YYYY-MM-DD
**Estado:** 🔴 Abierto | 🟡 En revisión | 🟢 Resuelto
**URL:** /ruta/donde/ocurre
**Descripción:** Qué está mal exactamente
**Screenshot:** `screenshots_temporales/nombre.png`
**Causa probable:** (si se identifica)
**Fix:** (cuando se resuelva — quién lo arregló y qué cambió)
```

### Estados de bugs
- 🔴 **Abierto** — detectado, sin fix
- 🟡 **En revisión** — Claude Code trabajando en ello
- 🟢 **Resuelto** — verificado y cerrado

---

## Qué verificar en cada módulo

### Checklist general (aplica a TODA página nueva)
- [ ] La página carga sin errores en consola del browser
- [ ] El título y breadcrumb son correctos
- [ ] La tabla muestra datos (no está vacía si hay datos en BD)
- [ ] Los números tienen formato correcto (miles con punto, decimales con coma)
- [ ] Los KPIs (si existen) muestran valores coherentes
- [ ] El loading skeleton aparece y desaparece correctamente
- [ ] El selector de columnas funciona
- [ ] El export CSV/XLSX/PDF genera archivo correcto
- [ ] Los filtros por columna funcionan
- [ ] Los tooltips en headers de columna aparecen al hacer hover
- [ ] El click en fila navega al lugar correcto (si aplica)

### Checklist específico por módulo — ver `QA_REGISTRO.md`

---

## Flujo de testing para features nuevas

```
1. Claude Code completa la feature + build + restart
2. Antigravity recibe prompt con contexto detallado
3. Antigravity navega la app con Playwright
4. Por cada pantalla: screenshot + verificación de datos
5. Antigravity documenta hallazgos en QA_REGISTRO.md
6. Antigravity reporta bugs en la conversación principal con Santi
7. Claude Code corrige bugs reportados
8. Antigravity verifica correcciones (ciclo se repite hasta ✅)
9. Screenshots de bugs resueltos → borrar de screenshots_temporales/
```

---

## Comandos Playwright útiles

```javascript
// Iniciar browser
const { chromium } = require('playwright');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.setViewportSize({ width: 1440, height: 900 });

// Navegar y capturar
await page.goto('http://menu.oscomunidad.com/ventas/cartera');
await page.waitForTimeout(3000); // esperar carga inicial
await page.screenshot({ path: '/ruta/screenshot.png', fullPage: true });

// Hover para tooltip
await page.hover('th:has-text("Saldo pendiente")');
await page.waitForTimeout(600); // esperar tooltip
await page.screenshot({ path: '/ruta/tooltip.png' });

// Verificar texto en página
const texto = await page.textContent('.kpi-value');
```

---

## Conexión a API para verificación

```bash
# Endpoints ERP — desde el host (sin SSH)
curl -s http://localhost:9100/api/ventas/cartera | jq 'length'
curl -s http://localhost:9100/api/ventas/cartera-cliente | jq 'length'
curl -s http://localhost:9100/api/tooltips | jq 'keys | length'

# Datos en Hostinger
mysql -u u768061575_osserver -pEpist2487. -h 127.0.0.1 -P 3316 u768061575_os_integracion \
  -e "SELECT mes, year_ant_ventas_netas, mes_ant_ventas_netas FROM resumen_ventas_facturas_mes ORDER BY mes DESC LIMIT 5;" 2>/dev/null
# Nota: el tunnel SSH debe estar activo o usar el script de conexión del pipeline
```

---

## Prioridad de testing

Al recibir un lote de features nuevas, testear en este orden:
1. **Endpoints API** — curl primero, verificar datos reales
2. **Carga de páginas** — sin errores, con datos
3. **Datos y cálculos** — coherencia numérica
4. **Interacciones** — clicks, filtros, exports
5. **Tooltips y detalles visuales** — último
