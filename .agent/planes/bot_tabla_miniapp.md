# Plan: Mini App de Tabla — Bot Telegram
**Fecha:** 2026-03-17
**Estado:** PENDIENTE DE EJECUCIÓN

---

## Objetivo

Cuando el bot de Telegram responde con una tabla de más de 2 filas, muestra un botón
"📋 Ver tabla" que abre una **Telegram Web App** (panel embebido dentro de Telegram)
con una tabla interactiva idéntica a OsDataTable + función nueva de **Agrupar por columna**.

---

## Arquitectura

```
Bot responde consulta con tabla >2 filas
        ↓
Genera token → guarda en bot_tablas_temp (ya existe)
        ↓
Botón tipo web_app → menu.oscomunidad.com/bot/tabla?token=TOKEN
        ↓
BotTablaPage.vue (standalone, sin sidebar, sin auth)
        ↓
GET /api/bot/tabla?token=TOKEN → {pregunta, columnas, filas}
        ↓
Tabla interactiva con filtros + agrupar + exportar
```

---

## Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `frontend/app/src/pages/BotTablaPage.vue` | CREAR | Página standalone mini app |
| `frontend/app/src/router/routes.js` | MODIFICAR | Agregar ruta `/bot/tabla` sin layout |
| `frontend/api/server.js` | MODIFICAR | Agregar `GET /api/bot/tabla?token=` |
| `scripts/telegram_bot/bot.py` | MODIFICAR | Cambiar botón url → web_app, umbral >5 → >2 |
| `scripts/telegram_bot/tabla.py` | MODIFICAR | Umbral MAX_FILAS_INLINE: 5 → 2 |

---

## Paso 1 — API endpoint

```javascript
// GET /api/bot/tabla?token=TOKEN
// Lee bot_tablas_temp de ia_service_os (MySQL local)
// Devuelve: { ok, pregunta, columnas: ['col1','col2',...], filas: [[val,val,...]] }
// Error 404 si token no existe o expiró (>24h)
```

**Nota:** La BD `ia_service_os` es local (MariaDB), distinta de `u768061575_os_integracion` (Hostinger).
Necesita conexión separada: `mysql2.createConnection({ host:'localhost', user:'osadmin', password:'Epist2487.', database:'ia_service_os' })`

---

## Paso 2 — Ruta sin layout

```javascript
// routes.js — agregar ANTES de las rutas con MainLayout
{
  path: '/bot/tabla',
  component: () => import('pages/BotTablaPage.vue')
  // Sin layout — página standalone
}
```

---

## Paso 3 — BotTablaPage.vue

### Estructura
```
<div class="bot-tabla-page">
  <!-- Header -->
  <div class="bt-header">
    <span class="bt-pregunta">{{ pregunta }}</span>
    <span class="bt-count">{{ filas visibles }}</span>
  </div>

  <!-- Toolbar (igual a OsDataTable) -->
  [Campos] [Agrupar] [Exportar]   ← Agrupar es nuevo

  <!-- Tabla (idéntica a OsDataTable) -->
  <table>
    <thead> ... </thead>
    <tbody>
      <!-- Si agrupado: filas de grupo con agregados -->
      <!-- Si no: filas normales -->
    </tbody>
  </table>

  <!-- Footer: N filas -->
</div>
```

### Lógica de columnas
Las columnas llegan como array de strings `['col1','col2',...]`.
Se convierten a `{key, label, visible, type}` donde:
- `label` = col.replace(/_/g, ' ') capitalizado
- `type` = 'number' si todos los valores son numéricos, sino 'text'
- `visible` = true por defecto

### Funcionalidades a incluir (todas de OsDataTable)
- ✅ Popup por columna (clic en header)
- ✅ Filtrar: igual/contiene/mayor/menor/entre
- ✅ Ordenar: ASC / DESC
- ✅ Subtotales: suma/promedio/máx/mín (solo numéricas)
- ✅ Campos: mostrar/ocultar columnas
- ✅ Exportar: CSV y XLSX (sin PDF — móvil no lo necesita)
- 🆕 **Agrupar por columna** (nuevo)

### Lógica de Agrupar (nueva)
```
En popup de columna → sección "Agrupar"
  [Agrupar por esta columna]  ← botón toggle

Al activar:
  - Solo 1 columna agrupada a la vez (toggle exclusivo)
  - groupByKey = 'nombre_columna'
  - La tabla muestra 1 fila por valor único del campo agrupado
  - Columnas con subtotal configurado → se calculan para ese grupo
  - Columnas sin subtotal → muestran '—' (excepto la columna agrupada)
  - Fila de totales arriba = total general de todas las filas filtradas

En el popup de la columna agrupada:
  - Botón "Agrupar" aparece activo/marcado
  - Click de nuevo = desagrupar

Badge en toolbar: cuando hay agrupación activa mostrar "G nombre_col"
```

### Exportar desde mini app
No usa `/api/export/:recurso` (eso es para datos de Hostinger).
La exportación se hace **client-side** con los datos ya cargados:
- CSV: generar blob con JS y `URL.createObjectURL`
- XLSX: usar SheetJS (`xlsx` npm package — ya está en package.json? verificar)

Si SheetJS no está → agregar. Es pequeño y corre en browser.

---

## Paso 4 — Telegram Web App

### Cambio en bot.py
```python
# Antes (url normal):
InlineKeyboardButton('📋 Ver tabla', url=f'https://menu.oscomunidad.com/bot/tabla?token={token}')

# Después (web_app):
from telegram import WebAppInfo
InlineKeyboardButton('📋 Ver tabla', web_app=WebAppInfo(url=f'https://menu.oscomunidad.com/bot/tabla?token={token}'))
```

### Cambio de umbral
```python
# tabla.py
MAX_FILAS_INLINE = 2  # era 5 — ahora mostrar tabla desde 3 filas
```

### Integración Telegram Web App en la página
```javascript
// Al montar BotTablaPage.vue:
const tg = window.Telegram?.WebApp
if (tg) {
  tg.ready()
  tg.expand()  // pantalla completa
  // Usar colores del tema de Telegram:
  // tg.themeParams.bg_color, tg.themeParams.text_color, etc.
}
```

---

## Paso 5 — Deploy

```bash
cd frontend && bash deploy.sh
sudo systemctl restart os-telegram-bot.service
```

---

## Diseño visual

- **Mobile-first**: padding generoso, fuente 14px mínimo, touch targets 44px
- **Mismas variables CSS** que menu.oscomunidad.com (var(--bg-card), var(--accent), etc.)
- **Sin sidebar, sin header de navegación** — solo la tabla
- **Popup de columna**: igual que OsDataTable, adaptado para touch (opciones más grandes)
- **Toolbar sticky**: se queda arriba al hacer scroll

---

## Orden de ejecución

1. API endpoint `GET /api/bot/tabla` (5 min)
2. Ruta en router.js (2 min)
3. BotTablaPage.vue — estructura + datos + tabla básica (30 min)
4. Popup de columna con filtros + ordenar + subtotales (20 min)
5. **Agrupar** (20 min)
6. Exportar client-side CSV + XLSX (15 min)
7. Telegram Web App integration (5 min)
8. Cambio bot.py: web_app button + umbral (5 min)
9. Deploy + prueba real desde Telegram (10 min)

**Total estimado: ~2 horas de implementación**

---

## Verificación final

- [ ] Abrir bot → hacer pregunta que devuelva tabla >2 filas
- [ ] Aparece botón "📋 Ver tabla"
- [ ] Al tocar → se abre panel dentro de Telegram (no browser externo)
- [ ] La tabla carga con los datos correctos
- [ ] Filtros funcionan
- [ ] Agrupar funciona con agregados por grupo
- [ ] Exportar CSV descarga el archivo
- [ ] Exportar XLSX descarga el archivo
