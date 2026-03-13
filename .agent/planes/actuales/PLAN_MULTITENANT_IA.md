# PLAN: Arquitectura Multi-Empresa en ia_service_os + ia-admin

**Creado**: 2026-03-13
**Estado**: 🟢 Completado (Fases 1-4) — pendientes menores: 2.7, 3.3, 4.5
**Objetivo**: Implementar empresa como eje de seguridad y organización en todo el sistema IA, siguiendo el patrón de SOS_ERP.

---

## CONTEXTO Y DECISIONES DE DISEÑO

### Tablas GLOBALES (sin campo empresa — aplican a todo el sistema)
- `ia_agentes` — Configuración de LLMs (API keys, endpoints, precios). Son infraestructura compartida.

### Tablas POR EMPRESA (todas las demás)
- `ia_tipos_consulta` — empresa nullable: NULL = tipo global, valor = tipo custom de esa empresa
- `ia_conversaciones` — cada conversación pertenece a una empresa
- `ia_logs` — auditoría por empresa
- `ia_consumo_diario` — facturación por empresa
- `ia_temas` ✅ ya tiene empresa
- `ia_rag_documentos` ✅ ya tiene empresa
- `ia_rag_fragmentos` ✅ ya tiene empresa

### Campos de auditoría OBLIGATORIOS en toda tabla
```
empresa               VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2'
usuario_creacion      VARCHAR(150)   -- email del creador
usuario_ult_mod       VARCHAR(150)   -- email del último que modificó
created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

### Patrón de empresa (igual que SOS_ERP)
- `ia_empresas.uid` = identificador funcional (ej: `ori_sil_2`)
- JWT contiene `empresa_activa` — backend lo inyecta en todas las queries
- Cliente NUNCA envía empresa — siempre viene del JWT
- Filtro SQL obligatorio: `WHERE empresa = :empresa` en todo SELECT/UPDATE/DELETE

---

## CHECKLIST DE EJECUCIÓN

### FASE 1 — Base de Datos ✅/🔲

- [x] **1.1** Analizar schema actual — identificar tablas sin empresa y sin auditoría
- [x] **1.2** Crear tabla `ia_empresas` en `ia_service_os`
- [x] **1.3** Crear tabla `ia_usuarios_empresas` en `ia_service_os`
- [x] **1.4** Modificar `ia_usuarios` — agregar `ultima_empresa`, `updated_at`, `usuario_creacion`, `usuario_ult_mod`
- [x] **1.5** Modificar `ia_agentes` — agregar `updated_at`, `usuario_creacion`, `usuario_ult_mod` (sin empresa — es global)
- [x] **1.6** Modificar `ia_tipos_consulta` — agregar `empresa` (nullable), `created_at`, `updated_at`, `usuario_creacion`, `usuario_ult_mod`
- [x] **1.7** Modificar `ia_conversaciones` — agregar `empresa`, `usuario_creacion`, `usuario_ult_mod`
- [x] **1.8** Modificar `ia_logs` — agregar `empresa`, `usuario_id`
- [x] **1.9** Modificar `ia_consumo_diario` — agregar `empresa`, `created_at`, `usuario_creacion`, `usuario_ult_mod`
- [x] **1.10** Seed: insertar empresa ori_sil_2 en `ia_empresas`
- [x] **1.11** Seed: asignar Santiago y Jennifer a `ia_usuarios_empresas` con roles
- [x] **1.12** Migrar datos existentes — poner empresa='ori_sil_2' en todos los registros existentes

### FASE 2 — Backend (ia-admin API) ✅

- [x] **2.1** Actualizar endpoint `/api/ia/auth/google`:
  - Paso 1: validar Google token → buscar usuario en ia_usuarios → obtener lista de empresas de ia_usuarios_empresas → emitir token TEMPORAL (15 min) con lista de empresas
  - Si solo 1 empresa → auto-seleccionar y emitir token final directo
- [x] **2.2** Crear endpoint `/api/ia/auth/seleccionar_empresa`:
  - Valida token temporal + empresa elegida → verifica en ia_usuarios_empresas → emitir JWT final 7 días con `empresa_activa`
- [x] **2.3** Actualizar middleware `requireAuth` — extraer `empresa_activa` del JWT y agregar a `req.empresa`
- [x] **2.4** Actualizar todos los endpoints GET de ia-admin para filtrar por `req.empresa`:
  - `/api/ia/rag/temas` → `WHERE empresa = req.empresa`
  - `/api/ia/rag/temas/:id/documentos` → verificar que tema pertenece a empresa
  - `/api/ia/consumo` → proxy a ia-service con empresa
  - `/api/ia/consumo/historico` → filtrar por empresa
  - `/api/ia/logs` → filtrar por empresa
  - `/api/ia/agentes-admin` → global (sin filtro empresa)
  - `/api/ia/tipos` → filtrar por empresa (mostrar globales + de empresa)
- [x] **2.5** Actualizar endpoints POST/PUT/DELETE para inyectar empresa desde JWT (nunca del body)
- [x] **2.6** Agregar endpoint `GET /api/ia/mis-empresas` — lista empresas del usuario autenticado
- [ ] **2.7** Agregar endpoint `GET /api/ia/empresa-activa` — datos de la empresa actual del JWT

### FASE 3 — ia-service (Flask) ✅

- [x] **3.1** Endpoint `/ia/consumo` — aceptar parámetro `empresa` en query string → filtrar ia_consumo_diario
- [x] **3.2** Endpoint `/ia/consumo/historico` — igual, filtrar por empresa
- [ ] **3.3** Endpoint `/ia/logs` (si existe) — filtrar por empresa
- [x] **3.4** Guardar `empresa` en ia_logs al registrar cada llamada (ya lo hace via consultar())
- [x] **3.5** Guardar `empresa` en ia_consumo_diario al agregar consumo diario

### FASE 4 — Frontend Vue (ia-admin) ✅

- [x] **4.1** Crear componente `AppHeader.vue` — header superior con:
  - Nombre del usuario (con foto/inicial)
  - Empresa activa (nombre + siglas)
  - Botón para cambiar empresa (si tiene más de 1)
- [x] **4.2** Actualizar `MainLayout.vue` — agregar header superior
- [x] **4.3** Actualizar `LoginPage.vue` — agregar paso 2 de selección de empresa:
  - Si usuario tiene 1 empresa → auto-selecciona y va al dashboard
  - Si tiene múltiples → muestra grid de empresas para elegir
- [x] **4.4** Actualizar `authStore.js` — agregar `empresa_activa`, `empresa_nombre`, `empresa_siglas`, `empresas_disponibles`
- [ ] **4.5** Actualizar todas las páginas Vue para que el empresa switcher refresque los datos
- [x] **4.6** Actualizar `DashboardPage.vue` — mostrar empresa activa en el encabezado

### FASE 5 — Documentación ✅/🔲

- [x] **5.1** Crear `MANUAL_EMPRESAS_USUARIOS.md` en `.agent/docs/`:
  - Qué es una empresa en el sistema
  - Cómo crear una empresa nueva
  - Cómo agregar un usuario a una empresa
  - Roles disponibles y qué puede hacer cada uno
  - Cómo cambiar de empresa en la UI
  - Reglas de seguridad
- [x] **5.2** Actualizar `MANIFESTO.md` — agregar regla de empresas y campos auditoría
- [x] **5.3** Actualizar `CONTEXTO_ACTIVO.md` con el nuevo estado
- [x] **5.4** Commit + push final

---

## ESQUEMA SQL — NUEVAS TABLAS

### ia_empresas
```sql
CREATE TABLE ia_empresas (
  uid          VARCHAR(50)  NOT NULL,
  nombre       VARCHAR(200) NOT NULL,
  siglas       VARCHAR(20)  NOT NULL,
  estado       ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  logo_url     VARCHAR(500),
  notas        TEXT,
  usuario_creacion    VARCHAR(150),
  usuario_ult_mod     VARCHAR(150),
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (uid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### ia_usuarios_empresas
```sql
CREATE TABLE ia_usuarios_empresas (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  usuario_email VARCHAR(150) NOT NULL,
  empresa_uid  VARCHAR(50)  NOT NULL,
  rol          ENUM('admin','editor','viewer') NOT NULL DEFAULT 'viewer',
  activo       TINYINT(1) NOT NULL DEFAULT 1,
  usuario_creacion    VARCHAR(150),
  usuario_ult_mod     VARCHAR(150),
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_usuario_empresa (usuario_email, empresa_uid),
  FOREIGN KEY (usuario_email) REFERENCES ia_usuarios(email) ON DELETE CASCADE,
  FOREIGN KEY (empresa_uid)   REFERENCES ia_empresas(uid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## PATRÓN JWT — ANTES vs DESPUÉS

### JWT actual
```json
{ "email": "...", "nombre": "...", "rol": "admin" }
```

### JWT fase 1 (token temporal tras Google auth)
```json
{
  "email": "...", "nombre": "...", "foto": "...",
  "tipo": "temporal",
  "empresas": [
    { "uid": "ori_sil_2", "nombre": "Origen Silvestre", "siglas": "OS", "rol": "admin" }
  ]
}
```

### JWT fase 2 (token final tras seleccionar empresa)
```json
{
  "email": "...", "nombre": "...", "foto": "...",
  "tipo": "final",
  "empresa_activa": "ori_sil_2",
  "empresa_nombre": "Origen Silvestre",
  "empresa_siglas": "OS",
  "rol_empresa": "admin"
}
```

---

## REGLAS DE SEGURIDAD (no negociables)

1. `empresa` en el body del request → **IGNORAR siempre**. Siempre viene del JWT.
2. Toda query SELECT/UPDATE/DELETE de tabla por-empresa → `AND empresa = :empresa`
3. INSERT → inyectar empresa + usuario_creacion + usuario_ult_mod desde JWT
4. Si `empresa_activa` falta en JWT → rechazar con 403
5. `ia_agentes` es la ÚNICA tabla sin filtro empresa (es config global)

---

## NOTAS Y CONSIDERACIONES

- **Datos existentes**: todos los registros actuales se migran con empresa='ori_sil_2'
- **Backward compatibility**: ia-service ya acepta `empresa` en consultar() — no rompe nada
- **Logs de ia-service**: ya guardan empresa cuando se llama consultar() — verificar
- **ia_consumo_diario**: la vista `v_consumo_hoy` también necesita actualizarse
