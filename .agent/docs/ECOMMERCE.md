# Ecommerce / Marketplace OS — Plan Maestro

**Creado**: 2026-04-19
**Estado**: Planeación (antes de arrancar repo)
**Decisión arquitectónica tomada**: WordPress/WooCommerce **headless** + Frontend Vue/Quasar custom + Admin de integración propio

---

## 1. Visión

Marketplace completo de Origen Silvestre conectado al ecosistema existente.

**Características clave:**
- Catálogo multi-categoría: chocolate, miel, propóleo, abonos, esencias naturales, snacks saludables, etc.
- Productores como entidad de primer nivel (página propia, bio, proceso, certificaciones)
- Trazabilidad visible por producto (lote, OP, fecha, origen, ingredientes)
- Integración bidireccional con el ERP de OS (`sistema_gestion`, `effi_data`, `catalogo_articulos`)
- UX top, diseñado a medida — no plantilla
- Admin propio para productores y staff (construido por nosotros, NO wp-admin)

**NO es:**
- Una tienda simple de chocolate
- Una réplica de WooCommerce estándar
- Una app que use wp-admin como panel operativo

---

## 2. Decisión arquitectónica

**WooCommerce headless + Frontend Vue/Quasar + Admin custom**

### Qué hace cada capa

| Capa | Tecnología | Responsabilidad |
|---|---|---|
| **Frontend público** | Quasar + Vue 3 (SSR/SSG) | UX de la tienda, catálogo, carrito, checkout |
| **Admin de integración** | Quasar + Vue 3 (panel custom) | Gestión de productos/productores/órdenes sin wp-admin |
| **Backend ecommerce** | WordPress + WooCommerce (Docker) | Solo BE + API REST — sin temas, sin Elementor, sin frontend público |
| **API de integración** | Node.js (Express) | Puente entre nuestro ERP, el admin custom y WooCommerce |
| **Sync ERP ↔ WC** | Node.js worker | Catálogo, inventario, trazabilidad, órdenes bidireccionales |

### Por qué esta decisión

| Objeción | Respuesta |
|---|---|
| "PHP contamina el stack" | Está aislado en Docker, solo lo toca la API de WC. No lo editamos |
| "wp-admin es feo" | No lo usamos. Construimos admin propio que consume WC API |
| "Elementor es basura" | No se usa. Frontend 100% Vue |
| "Temas de WP son pesados" | No hay tema. Es headless puro |
| "Plugins rompen updates" | Solo plugins backend esenciales (CoCart, ACF, pasarela, facturación) |
| "Dependencia de WP" | Aceptada como trade-off: nos ahorra 3-4 meses vs construir BE propio |

### Por qué NO las otras opciones

- **WordPress tradicional con Elementor**: UX mediocre, no escala para marketplace real
- **Medusa.js**: Mejor stack técnico, pero pasarelas Colombia verdes, obligaría a construir plugins propios (+2-3 sem cada pasarela). Comunidad menos madura
- **Custom 100%**: 4-6 meses solo para MVP del BE (checkout, pagos, envíos, facturación, emails, etc.). No es razonable para la etapa actual

---

## 3. Stack técnico detallado

### Frontend público (oscomunidad.com)
- **Framework**: Quasar (modo SSR para SEO, SSG para páginas estáticas)
- **Runtime**: Vue 3 + Composition API + `<script setup>`
- **Estado**: Pinia (incluye carrito local sincronizado con CoCart)
- **HTTP**: Fetch nativo o Axios
- **Estilos**: Quasar utilities + CSS custom (NUNCA Tailwind ni Bootstrap per reglas del proyecto)
- **SEO**: SSR para páginas de producto/categoría, sitemap dinámico, schema.org

### Admin custom (admin.oscomunidad.com)
- **Framework**: Quasar + Vue (compartiendo design system del ERP)
- **Autenticación**: Google OAuth + JWT propio (igual que `sistema_gestion`)
- **Componentes**: reutilizar `OsDataTable` y design system existente
- **Backend**: API Node que llama a WooCommerce API + a `sistema_gestion` API

### Backend WooCommerce (shop-api.oscomunidad.com)
- **Entorno**: Docker (aislado — no afecta otros servicios)
- **Server**: Nginx + PHP-FPM
- **BD**: MariaDB (schema propio `wordpress`, ya creado en VPS)
- **Plugins esenciales** (solo backend):
  - **CoCart** — carrito vía REST API
  - **Advanced Custom Fields Pro** — campos custom (Productor CPT, trazabilidad)
  - **JWT Authentication** — auth para frontend
  - **WooCommerce Wompi** (o dev custom) — pasarela Colombia
  - **Siigo/Alegra/Factus** — facturación electrónica DIAN
  - **Custom Post Type UI** — crear CPT "Productor"
- **Plugins PROHIBIDOS**: Elementor, Yoast SEO frontend, cualquier page builder, cualquier tema con frontend público

### API de integración (Node.js)
- **Puerto**: 9600 (siguiendo convención 9xxx)
- **Responsabilidad**:
  - Sync de catálogo OS → WooCommerce (productos, stock, precios)
  - Sync de órdenes WC → ERP OS (facturas, inventario)
  - Autenticación admin custom
  - Gestión de productores (CRUD via WC API)
  - Trazabilidad (conecta `effi_data` lotes/OPs con productos WC)

### Infraestructura
- **Servidor**: VPS Contabo (donde ya está WordPress instalado)
- **Tunnel**: Cloudflare (`oscomunidad.com`, `admin.oscomunidad.com`, `shop-api.oscomunidad.com`)
- **SSL**: Cloudflare Universal
- **Storage**: NVMe del VPS para imágenes de productos (con posible migración a R2/S3 si crece)

---

## 4. Modelo de datos

### Entidades principales

**Producto (WooCommerce + ACF)**
- Título, descripción, precio, stock, imágenes (nativo WC)
- Productor (relación ACF → Productor CPT)
- Lote (campo ACF, conectado a `effi_data.zeffi_produccion_encabezados`)
- Fecha producción, fecha vencimiento (campos ACF)
- Proceso (campo ACF repetidor: paso, descripción, foto)
- Certificaciones (campo ACF multi-select)
- Ingredientes (campo ACF texto/tabla)
- Categoría (taxonomía WC)
- SKU (match con `catalogo_articulos.codigo`)

**Productor (CPT custom)**
- Nombre, slug, bio, foto, ubicación
- Historia, proceso, filosofía
- Certificaciones, productos relacionados
- Link a redes sociales, video
- Usuario WP asociado (para que vea sus productos vía API)

**Orden (WooCommerce nativo)**
- Estados custom añadidos si hace falta (despachado, entregado, devuelto)
- Webhook al crearse → nuestra API de integración → factura electrónica + descuento de stock en ERP

**Categorías**
- Chocolate, Miel, Propóleo, Abonos, Esencias, Snacks, etc.
- Taxonomía nativa WC + metadatos ACF

### Fuente de verdad

- **Productos (catálogo base)**: `effi_data.catalogo_articulos` → sync a WC vía API
- **Inventario físico**: `os_inventario` → sync a WC vía API (trigger en cambios)
- **Productores**: WooCommerce (CPT + ACF) — no hay contraparte en ERP
- **Órdenes/clientes/pagos**: WooCommerce — sync a ERP vía webhook
- **Trazabilidad (lotes, OPs)**: `effi_data.zeffi_produccion_*` → visible en producto WC

---

## 5. Integración con ecosistema OS existente

| Sistema existente | Cómo se integra |
|---|---|
| `sistema_gestion` | Panel admin comparte design system, gestión de tareas/proyectos/etiquetas de ecommerce |
| `ia_service` | Descripciones IA, recomendaciones personalizadas, búsqueda semántica, clasificación automática |
| `effi_data` | Fuente de verdad de catálogo, trazabilidad, OPs, lotes |
| `catalogo_articulos` | Sync base del catálogo OS → WC |
| `os_inventario` | Stock físico sincronizado con stock WC |
| `wa_bridge` | Notificaciones de pedidos por WhatsApp (confirmación, envío, etc.) |
| `bot_telegram` | Alertas a admin de pedidos grandes, stock bajo, etc. |
| `effi-webhook` | Captura eventos de Effi → propaga a WC si aplica |
| `pipeline_effi` | Mantiene catálogo y producción actualizados |

---

## 6. Dominios y subdominios

| Dominio | Rol |
|---|---|
| `oscomunidad.com` | Frontend público del marketplace |
| `admin.oscomunidad.com` | Panel admin custom (productores + staff) |
| `shop-api.oscomunidad.com` | WooCommerce headless (acceso API solo) |
| `cdn.oscomunidad.com` | (futuro) Imágenes de productos |

---

## 7. Plan de implementación por fases

### Fase 0 — Decisión y setup (esta semana)
- [x] Definir arquitectura (este documento)
- [ ] Crear repo propio `OSMarketplace` (o nombre a definir)
- [ ] Estructurar repo: `frontend/`, `admin/`, `api-integracion/`, `docs/`
- [ ] Documentar convenciones iniciales

### Fase 1 — Backend WooCommerce + infra (1 semana)
- [ ] Completar instalación WP en VPS (wizard)
- [ ] Instalar plugins esenciales
- [ ] Crear CPT "Productor" con ACF
- [ ] Habilitar REST API + JWT
- [ ] Crear subdominios y routes del tunnel

### Fase 2 — API de integración (2 semanas)
- [ ] Crear servicio Node `api-integracion` (puerto 9600)
- [ ] Endpoints: `/sync/productos`, `/sync/stock`, `/webhooks/orden`, `/productores`
- [ ] Sync inicial desde `catalogo_articulos` → WC
- [ ] Webhook de órdenes WC → ERP
- [ ] Tests con productos reales

### Fase 3 — Admin custom (3 semanas)
- [ ] Login con Google OAuth (reutilizar flow de `sistema_gestion`)
- [ ] Módulo productores: CRUD (crea en WC vía API)
- [ ] Módulo productos: listar, editar, relacionar con productores, trazabilidad
- [ ] Módulo órdenes: listar, cambiar estado, despachar
- [ ] Módulo reportes: ventas, top productos, top productores
- [ ] Permisos: admin OS ve todo, productores ven solo lo suyo

### Fase 4 — Frontend público (4-6 semanas)
- [ ] Setup Quasar SSR/SSG
- [ ] Páginas: home, categorías, producto, productor, carrito, checkout, cuenta
- [ ] Diseño completo (tú + Claude Code, inspiración Aesop/Goldune/estética natural)
- [ ] Integración WC API vía CoCart
- [ ] Checkout: redirect a WC inicialmente, luego migración a custom
- [ ] SEO: sitemaps, schema, OG tags, meta dinámicas

### Fase 5 — Integraciones Colombia (2-3 semanas)
- [ ] Pasarela: Wompi (plugin WC + custom si hace falta)
- [ ] Facturación electrónica: Siigo/Alegra/Factus
- [ ] Envíos: cálculo por zona, integración Servientrega/Interrapidisimo
- [ ] Emails transaccionales con templates propios

### Fase 6 — Lanzamiento soft (1-2 semanas)
- [ ] Pruebas con productores reales
- [ ] Productos de prueba con trazabilidad completa
- [ ] Feedback y ajustes
- [ ] Lanzamiento público

**Timeline total realista: 14-18 semanas al MVP funcional completo**

---

## 8. Repo futuro

**Nombre propuesto**: `OSMarketplace` o `oscomunidad-shop` (a decidir)

**Estructura**:
```
OSMarketplace/
├── README.md
├── CLAUDE.md                    — Instrucciones para Claude Code
├── .agent/
│   ├── CONTEXTO_ACTIVO.md
│   ├── MANIFESTO.md
│   ├── CATALOGO_APIS.md
│   └── ...
├── frontend/                    — Quasar SSR (tienda pública)
│   ├── app/
│   ├── api/
│   └── package.json
├── admin/                       — Quasar SPA (panel custom)
│   ├── app/
│   ├── api/
│   └── package.json
├── api-integracion/             — Node.js Express (puente WC ↔ ERP)
│   ├── server.js
│   ├── sync/
│   ├── webhooks/
│   └── package.json
├── wp-docker/                   — Configuración Docker de WordPress
│   ├── docker-compose.yml
│   ├── wp-config-template.php
│   └── README.md
└── scripts/                     — Scripts de deploy, sync inicial, etc.
```

**Separado de `Integraciones_OS`** porque:
- Es un proyecto con identidad propia y timeline distinto
- Stack parcialmente diferente (WP/PHP aparece aquí)
- Permite releases y deployments independientes
- Pero integrado a través de APIs con `Integraciones_OS`

---

## 9. Reglas técnicas del proyecto

**Aplicables al frontend y admin (heredan de `Integraciones_OS`):**
- JavaScript puro (NO TypeScript)
- Vue 3 Composition API + `<script setup>`
- Quasar components para UI — NO Tailwind, NO Bootstrap
- `<form @submit.prevent>` en lugar de `@keydown.enter` (bug IME móvil)
- Timezone Colombia (`APP_TIMEZONE=-05:00`)
- Colores hardcodeados prohibidos — usar variables CSS y tema Quasar

**Aplicables a WordPress/WC:**
- Sin Elementor, sin ningún page builder visual
- Sin tema público — solo plugins backend
- Actualizaciones programadas, nunca automáticas (evitar breakages)
- Backup diario de BD `wordpress`
- Acceso wp-admin solo interno (IP whitelist o VPN)

---

## 10. Próximos pasos inmediatos

1. [ ] Santi valida este plan (este documento)
2. [ ] Decidir nombre final del repo
3. [ ] Crear repo en GitHub
4. [ ] Clonar estructura inicial en VPS
5. [ ] Completar instalación de WordPress pendiente
6. [ ] Arrancar Fase 1

---

## 11. Preguntas abiertas (para resolver antes de Fase 2)

1. **Pasarela de pago**: ¿Wompi, PayU, ePayco? Probablemente Wompi por UX y tarifas
2. **Facturación electrónica**: ¿Siigo (ya usamos?), Alegra, Factus? Verificar costo y API
3. **Envíos**: ¿quién hace la logística? ¿Servientrega/Interrapidisimo directo o tercero?
4. **Modelo de comisiones** (si productores son terceros): ¿% fijo, por categoría, escalonado?
5. **Facturación por productor**: ¿OS emite factura global o cada productor emite la suya?
6. **Inventario**: ¿stock centralizado en OS o cada productor maneja el suyo?
7. **Devoluciones**: política y flujo
8. **Branding**: ¿"Origen Silvestre Tienda", "Comunidad OS", marca nueva?

---

## Referencias

- [Documentación WooCommerce REST API](https://woocommerce.github.io/woocommerce-rest-api-docs/)
- [CoCart](https://cocart.xyz/)
- [Advanced Custom Fields](https://www.advancedcustomfields.com/)
- [Quasar SSR](https://quasar.dev/quasar-cli-vite/developing-ssr/introduction/)
- Estado actual del VPS: `.agent/docs/VPS_CONTABO.md`
- Arquitectura OS: `.agent/MANIFESTO.md`
