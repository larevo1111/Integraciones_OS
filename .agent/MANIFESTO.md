# MANIFESTO — Integraciones_OS

---

## ⚠️ REGLAS CRÍTICAS DE FRONTEND (leer antes de cualquier tarea de UI)

**ANTES de crear cualquier componente, vista, layout o elemento visual del ERP:**

1. **Leer el manual**: `frontend/design-system/MANUAL_ESTILOS.md`
2. **Consultar capturas de referencia**: `frontend/design-system/screenshots/` (88 imágenes de Linear.app) + `INDEX.md`
3. **Seguir el manual al pie de la letra**: colores, tipografía, espaciado, componentes — todo definido ahí.
4. **Si el elemento NO está en el manual**: DETENERSE. Preguntar a Santi y definir juntos antes de implementar. Luego actualizar el manual.

**⚠️ VERIFICACIÓN OBLIGATORIA ANTES DE MARCAR CUALQUIER TAREA FRONTEND COMO LISTA:**
1. Verificar que TODAS las variables CSS usadas existen en `frontend/app/src/css/app.scss` — si no existen, agregarlas o usar variable equivalente
2. Verificar que el endpoint API devuelve los datos correctos con `curl` o query directa
3. Hacer el build y confirmar que compila sin errores
4. NO declarar una tarea como completada sin haber verificado los puntos anteriores

**⚠️ BUILD OBLIGATORIO:** Después de cualquier modificación Vue/Quasar, los fuentes NO se sirven directamente. El servidor sirve `dist/spa/` compilado. Sin rebuild = cambios invisibles en producción.

### Cómo hacer el build correctamente

**IMPORTANTE: El build corre en el HOST, NO en Docker. Nunca usar `docker exec`.**

**App ERP (`menu.oscomunidad.com`):**
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app
npx quasar build
# Output: frontend/app/dist/spa/
```

**App IA Admin (`ia.oscomunidad.com`):**
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/ia-admin/app
npx quasar build
# Output: ia-admin/app/dist/spa/
```

**Reglas del build:**
1. Esperar a que termine completamente — puede tardar 30–60 segundos. No interrumpir.
2. El build es exitoso cuando aparece `Output folder...` al final, sin errores en rojo.
3. Si hay errores de TypeScript/lint, corregirlos antes de continuar — un build con errores NO actualiza `dist/`.
4. No es necesario reiniciar ningún servidor después del build (Node/Express sirve los archivos estáticos directamente desde `dist/spa/`).
5. No usar `npm run build` — usar siempre `npx quasar build` (es la forma correcta para Quasar).
6. Si el build se cuelga sin output por más de 2 minutos: `Ctrl+C`, luego `rm -rf node_modules/.vite` y volver a intentar.

**Verificar que el build aplicó:**
- Abrir la URL en el browser
- Hard refresh: `Ctrl+Shift+R` (o `Cmd+Shift+R` en Mac) para limpiar caché
- Revisar DevTools → Console para errores JS

---

## 1. PROTOCOLO DE IDENTIDAD Y GOBERNANZA DIGITAL [5S]

### 1.1 Jerarquía de Autoridad y Roles

**Santi (Santiago)** — Director Estratégico y Dueño.
Su visión es el norte y su aprobación es la ÚNICA llave para ejecutar cambios en producción o estructura. Santi NO codea — dirige, decide y orquesta agentes.

**Claude Code** — Arquitecto Senior + Constructor Principal + Operador de Infraestructura.
Es el cerebro técnico del proyecto. Diseña la estructura de módulos, planifica cambios cross-file, ejecuta refactors profundos, accede a MySQL y servidores por terminal directo. Toma decisiones de arquitectura del ERP. Recibe el **70% del trabajo pesado**: diseño, implementación compleja, consultas de DB, debugging profundo y análisis de arquitectura.

**Antigravity (Google Labs)** — Consultor Secundario + Asesor de Arquitectura.
Plataforma agentic de Google Labs (lanzada Nov 2025). IDE agent-first basado en Gemini 3.1 Pro con **contexto de 1 millón de tokens**. Puede navegar browsers de forma autónoma, tomar screenshots/grabaciones, y revisar codebases completos en una sola pasada. **Su rol principal en OS**: segunda opinión arquitectural cuando hay que revisar mucho contexto a la vez, QA visual autónomo, exploración de repositorios grandes. **NO reemplaza a Claude Code** — complementa. Ver perfil completo: `.agent/docs/ANTIGRAVITY_GOOGLE_LABS.md`.

**Subagentes Claude** — Ejecutores Paralelos de Claude Code.
Instancias de Claude lanzadas por Claude Code con la herramienta `Agent`. Mismas capacidades que Claude Code (Bash, Playwright, Read, Write, DB) pero corren en paralelo sin consumir tokens del contexto principal. Recibe el **máximo posible de trabajo secundario**: construcción de módulos, QA, exploración de codebase, diagnósticos de BD, documentación. **Regla: si una tarea no requiere razonamiento arquitectónico profundo → va al subagente.** NO confundir con Antigravity Google Labs — son conceptos distintos.

### 1.2 Asignación de tareas según tipo

| Tipo de tarea | Asignar a | Motivo |
|---|---|---|
| Diseño de arquitectura / estructura de módulos | Claude Code | Razonamiento profundo, visión cross-file |
| Implementación de features completas | Claude Code | Multi-archivo, PR-ready |
| Consultas MySQL / acceso a servidores | Claude Code | Terminal directo, sin intermediarios |
| Refactors complejos cross-module | Claude Code | Planificación + ejecución coordinada |
| Revisión de arquitectura con contexto masivo | Antigravity Google Labs | 1M tokens — puede leer el codebase completo |
| Segunda opinión arquitectural | Antigravity Google Labs | Contexto enorme + navegación browser autónoma |
| QA visual / browser testing autónomo | Antigravity Google Labs | Screenshots, grabaciones, navegación real |
| Exploración de repos o docs grandes | Antigravity Google Labs | Ideal cuando el contexto supera Claude Code |
| Construcción secundaria (módulos, CRUD) | Subagente Claude | Paralelo, sin consumir contexto principal |
| Tareas paralelas simultáneas | Subagente Claude | Multi-agente sin bloquear la conversación |
| QA funcional (endpoints, BD, logs) | Subagente Claude | Ejecución autónoma de checks |

---

## 2. FILOSOFÍA DEL SISTEMA IA — PRINCIPIO FUNDAMENTAL

> **Aplicable a ia_service_os, al bot de Telegram y a cualquier componente de IA del proyecto.**

### Enseñar a razonar, no a memorizar

**El objetivo es construir una IA que encuentre las respuestas de forma autónoma.**

Esto significa que NO hay que llenar el sistema de reglas específicas para cada pregunta posible. Si la IA falla en una consulta concreta y se le inyecta la respuesta correcta directamente en el prompt, la próxima vez la responderá bien — pero eso no es inteligencia: es memorización. El próximo usuario que haga la misma pregunta de otra forma volverá a fallar.

**No nos ganamos nada afinando el prompt para responder una pregunta específica que falló.** Lo que nos ganamos es mejorar el contexto general para que la IA razone mejor en todos los casos similares.

### Cuándo sí agregar reglas

Solo cuando representan información que el modelo NO puede inferir con el contexto disponible:
- Gotchas técnicos de la BD (ej: `id_cliente` en facturas tiene prefijo `'CC '`)
- Semántica no obvia de campos (ej: `precio_neto_total` INCLUYE IVA)
- Comportamientos contraintuitivos del negocio (ej: `vigencia='Vigente'` para consignación activa)

Estas cosas el modelo no puede deducirlas. Pero cómo calcular "ventas del lunes" sí puede razonarlo desde los patrones de fecha que ya tiene en el prompt.

### Cómo refinar correctamente

Cuando la IA falla en una consulta:
1. **Diagnosticar**: ¿Le falta contexto general? ¿O es un gotcha técnico que no puede inferir?
2. **Falta contexto general** → mejorar el system prompt con el principio, no el caso puntual
3. **Gotcha técnico** → sí agregar la regla, es legítimo
4. **Error de razonamiento** → agregar un ejemplo representativo en `ia_ejemplos_sql` que demuestre el patrón (no hardcodear la respuesta, sino el razonamiento)

### En la práctica

```
❌ MAL: La IA falló con "ventas del miércoles" → agregar en el prompt:
   "Si el usuario pregunta por el miércoles, usa DATE_SUB(CURDATE(), INTERVAL (WEEKDAY(CURDATE())-2) DAY)"

✅ BIEN: La IA falló con "ventas del miércoles" → revisar si los patrones de WEEKDAY
   ya están en <reglas_sql>. Si no están → agregar la REGLA GENERAL de días de la semana.
   No el caso del miércoles. Todos los días.

❌ MAL: La IA no supo qué tabla usar para consignación → agregar:
   "Cuando pregunten por consignación, usar zeffi_ordenes_venta_encabezados"

✅ BIEN: → verificar que la descripción de esa tabla en <tablas_disponibles> dice
   claramente "Usar para: consignación activa (filtrar vigencia='Vigente')". Si no lo dice → corregirlo.
```

---

## 4. ARCHIVOS DE CONTEXTO Y CONFIGURACIÓN

**Leer SIEMPRE al iniciar sesión, en este orden:**
1. `.agent/MANIFESTO.md` — Estado actual, decisiones tomadas, arquitectura vigente. Fuente de verdad #1.
2. `.agent/CONTEXTO_ACTIVO.md` — Estado actual del sistema y próximos pasos.
3. `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts. Verificar si ya existe algo antes de crear.
4. `.agent/skills/` — Skills individuales: documentan CÓMO hacer algo que ya se aprendió.

**Para tareas frontend además:**
- `frontend/design-system/MANUAL_ESTILOS.md`

**Para tareas del Servicio IA (`scripts/ia_service/` o `scripts/telegram_bot/`):**
- Cargar skill `/ia-service` — contexto completo con BD, agentes, flujos, latencias, troubleshooting
- Manual detallado: `.agent/manuales/ia_service_manual.md` (22 secciones)

**Regla de conexiones a BD:**
Las instrucciones de conexión están documentadas como skills. Si no existe la skill, Claude Code puede explorar — pero tiene la **obligación de documentar lo aprendido como skill nueva** antes de dar la tarea por terminada. El conocimiento no queda en el chat: se institucionaliza.

---

## 5. TONO Y COMUNICACIÓN

- **Claridad Quirúrgica**: Profesional, directa y empática.
- **NUNCA suponer, SIEMPRE preguntar.** Admitir ignorancia es una virtud; suponer es un error crítico.
- **Un paso a la vez**: Divide, planifica y conquista.
- **100% en Español** — toda comunicación visible para Santi.
- **Comunicar cambios**: Antes de hacer cambios importantes, comunicarlos. Si surge un cambio durante una tarea grande, explicar a Santi de manera clara y simple (sin tecnicismos innecesarios) qué cambió.
- **Resumen obligatorio al finalizar**: Al terminar cualquier tarea significativa, entregar un resumen claro de qué se hizo, qué cambió y qué hay que saber. Santi dirige — necesita entender el resultado, no la implementación técnica.

---

## 4. AUTONOMÍA DE EJECUCIÓN — DOS FASES

**Esta distinción es fundamental para trabajar eficientemente.**

**Fase de planificación** → NUNCA suponer, SIEMPRE preguntar.
Antes de ejecutar, confirmar el enfoque, aclarar dudas y obtener la aprobación de Santi. No se empieza sin un plan claro y acordado.

**Fase de ejecución** (plan acordado) → Ejecutar sin pedir aprobación por cada sub-paso.
Una vez que Santi dio la orden, no interrumpir para pedir permiso en cada comando, consulta SQL, lectura de archivo o commit de git. Esas aprobaciones intermedias generan fricción innecesaria. Solo detener si surge algo inesperado que cambia el alcance.

"Listo, adelante" o "Ejecutá el plan" = señal de arranque para ejecución autónoma.

---

## 5. FILOSOFÍA DE MEMORIA EXTERNA Y PROTOCOLO DE REGISTRO

**Principio:** No confiar en la memoria del chat. La verdad reside en los archivos del repositorio. Resolver sin documentar es resolver a medias.

### 5.1 Jerarquía de dónde registrar

| Dónde | Qué va ahí |
|---|---|
| **MANIFESTO.md** | Reglas generales, gotchas críticos de BD, decisiones arquitecturales permanentes |
| **Skills** (`.agent/skills/` o `.claude/commands/`) | Patrones técnicos específicos reutilizables, procedimientos por dominio |
| **Manuales** (`MANUAL_*.md`, `INSTRUCCIONES_*.md`) | Guías de referencia detalladas para humanos y agentes |
| **CONTEXTO_ACTIVO.md** | Estado actual del sistema, qué funciona, próximos pasos |
| **CATALOGO_SCRIPTS.md** | Scripts ejecutables con comando exacto y parámetros |

### 5.2 Protocolo de registro — OBLIGATORIO al terminar cualquier tarea

Antes de dar una tarea por terminada, responder estas preguntas:

1. ¿Corregí un bug o encontré un comportamiento inesperado de la BD/Effi/API? → **MANIFESTO sección 9 + skill del dominio**
2. ¿Cambié arquitectura o estructura de datos? → **CONTEXTO_ACTIVO**
3. ¿Creé o modifiqué un script? → **CATALOGO_SCRIPTS**
4. ¿Aprendí algo sobre Effi, la BD o el frontend que no estaba documentado? → **Skill del dominio correspondiente**
5. ¿Definí un patrón nuevo reutilizable? → **Crear/actualizar skill + entrada en catálogo**
6. ¿Adopté una técnica de una fuente externa (paper, guía, librería)? → **CATALOGO_REFERENCIAS** con URL, relevancia y dónde se aplicó

**Regla absoluta: ningún problema resuelto queda sin registrar. Si se descubrió en esta sesión, se documenta en esta sesión.**

### 5.3 El catálogo es el índice de TODO el conocimiento

`.agent/catalogo-skills.md` lista **todas** las skills Y manuales disponibles.
Toda skill o manual nuevo → entrada en el catálogo antes de terminar.

---

## 6. FLUJO DE TRABAJO OBLIGATORIO

**Orden de construcción (INVIOLABLE):**
```
VISIÓN → BASE DE DATOS (estructura) → IMPLEMENTACIÓN
```
No se puede construir sin entender qué quiere Santi. No se debe generar código sin que la base de datos esté estructurada primero. Siempre partir del estado de la BD, sus campos y reglas.

### ⚠️ REGLA ABSOLUTA: NINGUNA TAREA SIN PLAN

**Por qué existe esta regla:** El contexto del chat se pierde. Si no hay un plan escrito en el repo, cuando el contexto se llena la tarea queda a medias — nadie puede saber qué faltó. Un plan en MD es la garantía de continuidad entre sesiones.

**Antes de iniciar CUALQUIER tarea no trivial (más de 1 archivo o 1 endpoint):**

1. Crear un archivo de plan en `.agent/planes/actuales/<NOMBRE_PLAN>.md` con:
   - Objetivo y decisiones de diseño
   - Checklist numerado de pasos (`- [ ] 1. ...`)
   - Schema SQL si aplica
   - Sección "Tareas para Antigravity" (QA visual)
2. Mostrar el plan a Santi y esperar confirmación
3. Solo entonces ejecutar — ir tildando `[x]` a medida que se completa cada paso
4. Al terminar: mover el archivo a `.agent/planes/` (fuera de `actuales/`) y actualizar `CONTEXTO_ACTIVO.md`

**Consecuencias si no se cumple:**
- Tareas quedan a medias sin registro de qué faltó
- En la siguiente sesión no hay forma de saber el estado real
- Santi debe repetir el contexto completo desde cero (pérdida de tiempo)

**Esta regla aplica a todos los agentes**: Claude Code, subagentes Claude, y cualquier otro. Ningún agente puede iniciar implementación sin que exista un plan aprobado en `.agent/planes/actuales/`.

**Al iniciar sesión:** leer `.agent/planes/actuales/` — si existe un plan, continuar desde donde quedó antes de hacer cualquier otra cosa.

**Antes de cualquier tarea:**
1. Leer manifiesto y contexto activo
2. Verificar si existe plan activo en `.agent/planes/actuales/`
3. Verificar si existe skill relevante en el catálogo
4. Confirmar con Santi si hay dudas
5. Crear plan → aprobación → ejecutar

**Al asignar tareas a agentes:**
- Siempre referenciar el archivo de plan activo
- Ser totalmente específico: qué hacer, en qué archivos, qué pasos del plan
- Referenciar archivos de contexto relevantes
- Indicar explícitamente cuándo el plan está aprobado para ejecución autónoma

---

## 7. REGLA TRANSVERSAL DE ENTORNOS

**NUNCA conectarse ni alterar las bases de datos o servidores de Producción de manera directa para desarrollo.**

Todo trabajo, pruebas y cambios estructurales de BD se hacen en entorno local/staging. Para llevar cambios a producción se usa el pipeline de despliegue aprobado.

Un agente que toque Producción manualmente comete una falta crítica.

### BDs en Hostinger — reglas específicas

| BD | Propósito | Acceso permitido |
|---|---|---|
| `u768061575_os_comunidad` | ERP en producción (`menu.oscomunidad.com`)| **NUNCA tocar — PROHIBICIÓN ABSOLUTA** |
| `u768061575_os_integracion` | Datos Effi + analíticas | Lectura/escritura solo por el pipeline |

**`u768061575_os_comunidad`**: ni lectura masiva, ni escritura, ni DROP, ni ALTER sin autorización explícita de Santi. Falta crítica.

### Tablas analíticas — viven SOLO en Hostinger
Las tablas `resumen_ventas_*` tienen como única fuente de verdad `u768061575_os_integracion`.
El pipeline las calcula en local (staging temporal), las copia a Hostinger, y luego las borra de local.
**NO existen en `effi_data` local entre corridas. No leer ni escribir la versión local.**

---

## 8. CONTEXTO DEL PROYECTO: Integraciones_OS

- **Propósito**: Centralizar y automatizar datos de Effi, EspoCRM y otras fuentes en MariaDB para análisis y gestión operativa.
- **Persistencia**: MariaDB local — BD `effi_data` (Effi), `espocrm` (CRM), `nocodb_meta` (NocoDB).
- **Visualización operativa**: NocoDB (tablas externas + vistas SQL de MariaDB).
- **Fuentes**: Effi (vía Playwright) y EspoCRM.
- **Infraestructura**: Docker — NocoDB, n8n, EspoCRM, Nextcloud, Gitea, MinIO, Grafana, Portainer, phpMyAdmin.
- **Acceso público**: Cloudflare Tunnel → dominios `*.oscomunidad.com`.

### Orquestador Python (effi-pipeline)
- **Script**: `scripts/orquestador.py` — corre export + import cada 2h (Lun–Sab, 06:00–20:00).
- **Credenciales**: `scripts/.env` — **NUNCA subir a Git.**
- **Notificaciones**: email siempre + Telegram solo en error → usa `@os_notificaciones_sys_bot` (`TELEGRAM_NOTIF_BOT_TOKEN`). Bot de IA (`TELEGRAM_BOT_TOKEN`) es solo para conversaciones.
- **Systemd**: `systemd/effi-pipeline.service` + `.timer`
  - Test manual: `python3 scripts/orquestador.py --forzar`
  - Log: `journalctl -u effi-pipeline -f` o `logs/pipeline.log`

---

## 9. REGLAS TÉCNICAS APRENDIDAS

### ⚠️ REGLA ARQUITECTURAL: EMPRESA Y AUDITORÍA EN TODA TABLA

**Patrón multi-tenant** (igual que SOS_ERP — ver `.agent/docs/MANUAL_EMPRESAS_USUARIOS.md`):

**TODA tabla de datos (no solo config global) DEBE tener:**
```sql
empresa               VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2'  -- filtro principal
usuario_creacion      VARCHAR(150)  -- email del creador (inyectado del JWT)
usuario_ult_mod       VARCHAR(150)  -- email del último modificador (inyectado del JWT)
created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

**Excepción**: Tablas de configuración global que apliquen a todo el sistema (ej: `ia_agentes`).

**Reglas de seguridad — no negociables:**
1. `empresa` NUNCA viene del body del request → siempre se inyecta del JWT en el backend
2. Todo SELECT/UPDATE/DELETE en tablas por-empresa → `WHERE empresa = :empresa`
3. INSERT → inyectar empresa + usuario_creacion + usuario_ult_mod desde JWT
4. Si `empresa_activa` falta en JWT → rechazar con 403

**Tablas de empresa y acceso:**
- `ia_empresas` — catálogo de empresas del sistema
- `ia_usuarios_empresas` — qué empresas puede ver cada usuario y con qué rol
- Plan de migración: `.agent/planes/actuales/PLAN_MULTITENANT_IA.md`



### ⚠️ REGLA ABSOLUTA: VERIFICAR CREDENCIALES Y COLUMNAS ANTES DE IMPLEMENTAR

**Esta regla nació de 4+ errores consecutivos en la misma sesión (2026-03-16).**

**Para credenciales MySQL en Hostinger:**
1. **NUNCA asumir usuario MySQL** — Hostinger NO permite compartir el mismo usuario entre 2 BDs distintas.
2. Verificar en cPanel (Hostinger) → MySQL Databases → Database Users qué usuario tiene acceso a cada BD.
3. Credenciales verificadas (fuente de verdad en MEMORY.md):
   - `u768061575_os_comunidad` → user: `u768061575_ssierra047`, pass: `Epist2487.`
   - `u768061575_os_integracion` → user: `u768061575_osserver`, pass: `Epist2487.`
   - `u768061575_os_gestion` → user: `u768061575_os_gestion`, pass: `Epist2487.`

**Para columnas SQL:**
1. **NUNCA inventar nombres de columnas** — siempre verificar con `DESCRIBE <tabla>` antes de escribir el query.
2. `sys_usuarios`: columnas reales son `Nombre_Usuario`, `Nivel_Acceso`, `estado` (minúsculas en nombre), `Email` (mayúscula).
3. `sys_empresa`: `nombre_empresa` (no `nombre`), `estado='Activa'` (femenino, no 'Activo').
4. `sys_usuarios_empresas`: relación usa `rol` (no `perfil`).
5. Las tablas del ERP SOS tienen convenciones distintas al estándar snake_case — siempre verificar.

**Para JOINs cross-database en Hostinger:**
- Cada usuario MySQL solo tiene acceso a su propia BD. JOIN entre BDs distintas = Access Denied.
- Si necesitas datos de 2 BDs en un query → hacer 2 queries separados en Node y combinar en JS.
- Alternativa: subquery dentro de la misma BD (no funciona cross-DB de todas formas).

---

### Gotchas críticos — zeffi_facturas_venta_detalle
- **`precio_neto_total` INCLUYE IVA**: usar `precio_bruto_total - descuento_total` para "ventas sin IVA". Nombre engañoso — nunca asumir.
- **Número de factura**: en detalle se llama `id_numeracion`.
- **Canal**: campo `marketing_cliente` — NULL/vacío se normaliza como `'Sin canal'`.
- **`vigencia_factura = 'Vigente'`**: filtro obligatorio en detalle para excluir anuladas.
- **id_cliente en facturas/remisiones**: formato "CC 74084937" (con prefijo tipo doc). `zeffi_clientes.numero_de_identificacion` = "74084937" (sin prefijo). Para JOIN: `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`.

### Gotchas críticos — zeffi_clientes
- **Duplicados por `numero_de_identificacion`**: la tabla puede tener múltiples filas con el mismo NIT/CC (al menos 3 casos confirmados: `39440347`, `90173460334`, `9999999`). Un JOIN directo multiplica las filas de la tabla que se une, inflando sumas y conteos.
- **Regla obligatoria**: SIEMPRE deduplicar `zeffi_clientes` antes de hacer JOIN:
  ```sql
  LEFT JOIN (
    SELECT numero_de_identificacion, MAX(forma_de_pago) AS forma_de_pago
    FROM zeffi_clientes GROUP BY numero_de_identificacion
  ) c ON c.numero_de_identificacion = SUBSTRING_INDEX(f.id_cliente, ' ', -1)
  ```
- **Campos numéricos como texto**: `pdte_de_cobro`, `total_neto`, `cupo_de_credito_cxc` usan coma decimal → castear siempre: `CAST(REPLACE(COALESCE(campo,'0'),',','.') AS DECIMAL(15,2))`

### Verificación obligatoria de scripts analíticos
Al crear o modificar cualquier script de resumen, ejecutar los checks de integridad documentados en **`.agent/skills/integridad_datos.md`** antes de dar la tarea por terminada. Ningún script analítico se considera completo sin haber pasado esas verificaciones.

### NocoDB
- Tablas externas son solo lectura — relaciones entre tablas externas NO funcionan. Usar vistas SQL en MariaDB para JOINs.
- Conexión a MariaDB: usar IP `172.18.0.1` (gateway Docker), NO `host.docker.internal`.
- `osadmin@%` no funciona desde Docker — crear grants para `osadmin@172.18.0.%`.

### Cloudflare Tunnel
- Configuración en `/etc/cloudflared/config.yml`. Agregar hostname + reiniciar servicio + CNAME en Cloudflare DNS.

### 9.1 PREMISA CRÍTICA DE IA (Cero Alucinaciones)
**Regla absoluta para cualquier Bot o Agente IA que consuma datos del ERP:**
Para que la IA no invente respuestas o datos financieros, el flujo técnico obligado y el System Prompt de TODO agente debe seguir siempre estos 3 pasos (nunca intentar saltárselos):
1. **Generar código:** El Agente lee la pregunta + esquema y devuelve SÓLO una consulta SQL válida (o script equivalente).
2. **Ejecutar código:** El sistema/orquestador ejecuta el query ciegamente contra la BD MariaDB real y captura las filas retornadas.
3. **Responder usando ese resultado:** El sistema entrega los datos crudos de vuelta al Agente IA, quien redacta la respuesta usando única y exclusivamente la información del paso 2.

### 9.2 FLUJO CON IMÁGENES (Visión Multimodal)
Cuando el usuario envía una foto (desde Telegram u otro canal), el flujo tiene un paso previo:
```
Foto + texto (opcional)
      ↓
[Visión — agente con capacidad 'vision'] extrae texto estructurado de la imagen
      ↓
Texto extraído se inyecta como contexto en la pregunta
      ↓
[Flujo normal: Enrutador → SQL → Ejecutar → Redactar]
```
- El agente de visión se selecciona dinámicamente desde `ia_agentes.capacidades` (JSON `{"vision": true}`)
- Hoy es `gemini-flash` — puede cambiar sin tocar código, solo actualizar BD
- Si la imagen está en blanco o sin contenido, responde directo sin pasar por el enrutador
- Funciona con: capturas de pantalla, remisiones en papel, facturas físicas, etiquetas, conteos escritos

### 9.3 CAPACIDADES POR AGENTE
Cada agente declara sus capacidades en `ia_agentes.capacidades` (JSON). Capacidades definidas:
`vision` | `sql` | `codigo` | `razonamiento` | `documentos` | `contexto_largo` | `enrutamiento` | `imagen_generacion`
El servicio consulta esto para elegir el agente correcto por capacidad, sin hardcoding.

---

### 9.4 ESTRUCTURA DEL REPO — REGLA DE MÓDULOS

Cada módulo o herramienta independiente **debe tener su propio directorio en la raíz del repo**.

**Estructura actual (referencia):**
```
Integraciones_OS/
├── scripts/          ← pipeline Effi (exports, imports, sync, orquestador, ia_service, telegram_bot)
├── frontend/         ← ERP web (menu.oscomunidad.com) — Quasar + Node API
├── ia-admin/         ← Panel admin del servicio IA (ia.oscomunidad.com) — Quasar + Node API
├── espocrm-custom/   ← Customizaciones EspoCRM (PHP + JS)
├── docs/             ← Documentos de negocio (PDFs, DOCX, PPTX, XLSXs)
├── logs/             ← Logs de todos los servicios
├── systemd/          ← Unit files de systemd
└── .agent/           ← Contexto y documentación interna para Claude
```

**Regla para módulos nuevos:**
- Cualquier módulo nuevo (gestión de tareas, CRM propio, reportes, etc.) → **directorio propio en raíz**, NO dentro de `scripts/`
- `scripts/` es exclusivo del pipeline Effi y sus servicios asociados (ia_service, telegram_bot)
- Cada módulo debe tener su propio `README.md` o entrada en `.agent/`

**Nota:** `ia_service/` y `telegram_bot/` viven dentro de `scripts/` por razones históricas. En el futuro, si crecen mucho, se pueden migrar a raíz — no es urgente.

---

## 10. ESTRUCTURA DE MEMORIA

- `.agent/MANIFESTO.md` — Visión, roles, reglas y aprendizajes técnicos. (este archivo)
- `.agent/CONTEXTO_ACTIVO.md` — Estado actual y próximos pasos.
- `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts ejecutables (Python/JS). **Actualizar obligatoriamente al crear o modificar cualquier script.**
- `.agent/catalogo-skills.md` — Catálogo de conocimientos fundacionales. Índice de cómo se hacen las cosas.
- `.agent/CATALOGO_REFERENCIAS.md` — **Fuentes externas e internas que informan decisiones técnicas y de IA.** Incluye: guías de Anthropic/Google, papers de text-to-SQL, referencias de Antigravity, patrones de prompting, pendientes de investigar. **Actualizar al adoptar cualquier técnica externa o al encontrar una referencia relevante.**
- `.agent/skills/` — Skills individuales con conocimiento especializado (Ej. `.agent/skills/manejo_ia.md`).
- `.agent/planes/` — Especificaciones de construcción técnica para las features (Ej. `.agent/planes/bot_telegram.md`).
- `.agent/docs/` — Informes y documentación externa.

### Protocolo de documentación de scripts
Al crear un script nuevo, agregar entrada en `CATALOGO_SCRIPTS.md` con:
- Propósito (1 línea)
- Comando de ejecución manual exacto
- Archivos que genera / tablas que modifica
- Dependencias (otros scripts, credenciales, servicios)
- Comportamientos especiales o errores conocidos

---

## 11. MANUAL DE ESTILOS — Frontend ERP

| Archivo | Contenido |
|---|---|
| `frontend/design-system/MANUAL_ESTILOS.md` | Manual completo — CSS, variables, reglas, componentes |
| `frontend/design-system/screenshots/INDEX.md` | Índice de las 88 capturas de referencia (Linear.app) |
| `frontend/design-system/screenshots/*.png` | 88 capturas reales organizadas por elemento |

- El manual define: colores exactos, tipografía, espaciado, todos los componentes.
- Elemento no documentado = **preguntar a Santi** antes de inventar.
- Al definir un elemento nuevo con Santi, actualizar el manual inmediatamente.

---

## 12. ESTÁNDAR DE NAVEGACIÓN DRILL-DOWN — ERP

### Regla universal: toda tabla tiene drill-down

**En este ERP, CUALQUIER fila de CUALQUIER tabla es clickeable y navega al siguiente nivel.**
No existe tabla decorativa. Si hay filas, hay drill-down.

### Patrón obligatorio de 3 niveles

```
Nivel 1 — Resumen agrupado        (1 fila = 1 cliente / 1 mes / 1 canal)
  └─ click → Nivel 2 — Lista de documentos    (facturas, órdenes, remisiones del agrupador)
                └─ click → Nivel 3 — Detalle del documento   (ítems, campos completos)
```

**Regla crítica:** el Nivel 3 siempre reutiliza la vista de detalle canónica del tipo de documento.
- Factura → siempre `/ventas/detalle-factura/:id_interno/:id_numeracion` (DetalleFacturaPage)
- Orden de venta → siempre `/ventas/consignacion-orden/:id_orden` (DetalleConsignacionPage)
- Remisión → (pendiente) cuando se construya, su propia vista canónica

**NUNCA crear una vista de detalle ad-hoc para el mismo tipo de documento.** Reutilizar la existente.

### Catálogo de vistas — referencia obligatoria

Ver `.agent/CATALOGO_VISTAS.md` — **leer antes de crear cualquier página nueva**.
Contiene todas las vistas existentes, sus rutas, propósito y jerarquía de navegación.

### Nomenclatura de rutas drill-down

```
/ventas/{modulo}                          → Nivel 1: resumen
/ventas/{modulo}-cliente/:id_cliente      → Nivel 2: documentos del cliente
/ventas/{modulo}-orden/:id_orden          → Nivel 3: detalle documento (si aplica)
```
O para módulos con mes:
```
/ventas/{modulo}/:mes                     → Nivel 1: por mes
/ventas/{modulo}/:mes/:id_cliente         → Nivel 2: por cliente en ese mes
```

---

## 13. DICCIONARIO DE NEGOCIO

- Nomenclatura en Español (coherente con ERP Effi).
- Clientes Effi → `tipo_de_persona` distingue empresa/persona natural.
- Campo de enlace clave: `clientes.numero_de_identificacion` ↔ `facturas_venta_encabezados.id_cliente` (gotcha: prefijo tipo doc en facturas).

---

## 14. GESTIÓN DE SCREENSHOTS TEMPORALES Y UI

**Protocolo para Claude Code y Codex respecto a validación visual:**
Antigravity (Verificador Visual) documentará bugs y estado de la UI almacenando capturas de pantalla en `/home/osserver/Proyectos_Antigravity/Integraciones_OS/screenshots_temporales/`.
1. **Lectura:** Usen estas imágenes para entender el resultado final de la UI al hacer debug de componentes Vue (ej. alineación, tablas vacías, etc).
2. **Ciclo de Vida:** Cuando la tarea o bug se dé por finalizado/resuelto, **tienen la obligación de borrar las capturas asociadas** de la carpeta temporal para no contaminar el repo.
3. **Excepción:** Si una captura representa un patrón importante de diseño que debe recordarse a futuro, muévanla a `frontend/design-system/screenshots/` y actualicen su `INDEX.md`.

---

## 14. DELEGACIÓN — POLÍTICA DE EQUIPO Y AHORRO DE TOKENS

**Principio:** Claude Code es el arquitecto y constructor principal. Para trabajo secundario y paralelo existen DOS recursos distintos — aprender a distinguirlos es crítico.

### 14.1 Los dos tipos de agentes colaboradores

#### Subagentes Claude (vía herramienta `Agent`)
Claude Code puede lanzar subinstancias de sí mismo con la herramienta `Agent`. Son instancias independientes de Claude con acceso a todas las herramientas (Bash, Read, Write, Edit, Playwright, etc.). Corren en paralelo o en segundo plano **sin consumir tokens del contexto principal**. Úselos para construcción secundaria, QA funcional, exploración, documentación.

#### Antigravity de Google Labs (agente externo)
Plataforma agentic independiente de Google Labs. **NO es un subagente de Claude** — es una herramienta separada que Santi usa directamente. Tiene ventana de contexto de 1 millón de tokens, navegación browser nativa y verificación visual autónoma. Ver perfil completo en `.agent/docs/ANTIGRAVITY_GOOGLE_LABS.md`.

> ⚠️ **REGLA ANTI-CONFUSIÓN**: Cuando este documento (o cualquier conversación) mencione "Antigravity" sin calificador, se refiere a **Antigravity de Google Labs** (el agente externo). Los subagentes de Claude se llaman "subagentes Claude" o "subagente".

### 14.2 Roles en el equipo

| Rol | Quién | Responsabilidad |
|---|---|---|
| **Director** | Santi | Visión, decisiones de negocio, aprobación de planes |
| **Arquitecto + Constructor principal** | Claude Code | Diseño técnico, decisiones arquitecturales, coordinación, features críticas, BD |
| **Consultor + Asesor de arquitectura** | Antigravity Google Labs | Segunda opinión con contexto masivo (1M tokens), QA visual autónomo, exploración de repos grandes |
| **Ejecutores paralelos** | Subagentes Claude | Construcción secundaria, QA funcional, tareas paralelas sin bloquear la conversación |

### 14.3 Regla de los planes — OBLIGATORIO

**Con CADA PLAN que Claude Code presente a Santi, debe incluir una sección explícita:**

```
## Tareas para Antigravity
- [ ] Tarea 1 — descripción
- [ ] Tarea 2 — descripción
```

Si no hay tareas delegables, justificarlo. Santi necesita saber siempre qué puede hacer Antigravity.

### 14.4 Qué puede hacer Antigravity

**Construcción secundaria (Antigravity construye, Claude Code revisa):**
- Páginas/vistas nuevas de estructura estándar (CRUD, listados, formularios)
- Endpoints REST simples (GET/POST/PUT/DELETE de tablas)
- Migraciones de BD simples (CREATE TABLE, ALTER TABLE)
- Componentes Vue reutilizables siguiendo el design system
- Scripts Python/Node de utilidad (exports, imports, sync)
- Refactoring y limpieza de código

**QA y verificación (Antigravity verifica de forma autónoma):**
- Probar endpoints con curl, verificar respuestas
- Verificar UI con Playwright: navegar, tomar screenshots, reportar bugs
- Comparar schema real de BD vs código
- Verificar integridad de datos tras cambios

**Exploración y diagnóstico:**
- Leer múltiples archivos, mapear estructura de código
- Diagnosticar bugs: leer logs, trazar causa raíz
- Investigar APIs externas (docs, ejemplos)
- Validar configuraciones del sistema

**Documentación:**
- Actualizar archivos `.agent/`
- Generar reportes de QA
- Escribir comentarios en código

### 14.5 Qué retiene Claude Code (nunca delegar)

- Diseño arquitectural y decisiones técnicas críticas
- Features con lógica de negocio compleja
- Coordinación entre múltiples partes del sistema
- Decisiones que necesitan aprobación de Santi
- Tareas que requieren contexto acumulado de la conversación

### 14.6 Protocolo de ejecución

Antes de hacer cualquier exploración, búsqueda o tarea secundaria directamente:
1. **¿Puedo delegarlo?** → Si toma >3 lecturas de archivo o >3 comandos bash → **delegarlo**.
2. **Lanzar con prompt detallado** — incluir todo el contexto: rutas, schemas, objetivo, formato de resultado esperado.
3. **En segundo plano si es posible** → `run_in_background: true` para no bloquear la conversación.
4. **Informar a Santi** qué se delegó y en qué directorio quedará el resultado.

### 14.7 Archivos de resultados de Antigravity

- **QA/Testing:** `.agent/QA_REGISTRO.md` — registro vivo de bugs y checklists
- **Screenshots temporales:** `screenshots_temporales/<modulo>_<desc>_<timestamp>.png`
- **Diagnósticos:** `.agent/docs/DIAG_<tema>_<fecha>.md`
- **Exploraciones:** Reportar directamente en la conversación

---

## 16. PROTOCOLO DE QA Y TESTING

### Archivos clave
- `.agent/INSTRUCCIONES_TESTING.md` — **política y protocolo completo de QA** (leer antes de cualquier sesión de testing)
- `.agent/QA_REGISTRO.md` — **registro vivo de bugs** — se actualiza en cada sesión de QA

### Reglas fundamentales
1. **Antigravity** es el responsable exclusivo de QA visual y funcional.
2. Cada feature nueva terminada por Claude Code **debe pasar por QA de Antigravity** antes de considerarse cerrada.
3. Los bugs se documentan en `QA_REGISTRO.md` con estado 🔴/🟡/🟢.
4. Los screenshots de bugs abiertos viven en `screenshots_temporales/`. **Al cerrarse, se borran.**
5. Claude Code no puede marcar una tarea como terminada si hay bugs 🔴 abiertos relacionados.
6. Santi da el visto bueno final — Antigravity solo verifica, no aprueba.

### Flujo mínimo de QA por feature
```
Claude Code implementa + build + restart
  → Antigravity: curl endpoints → verificar datos
  → Antigravity: Playwright → navegar UI → screenshots
  → Antigravity: documenta en QA_REGISTRO.md
  → Claude Code: corrige bugs reportados
  → Antigravity: re-verifica → cierra bugs
  → Screenshots de bugs resueltos → borrar
```
