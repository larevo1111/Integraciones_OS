# MANIFESTO — Integraciones_OS

---

## ⚠️ REGLAS CRÍTICAS DE FRONTEND (leer antes de cualquier tarea de UI)

**ANTES de crear cualquier componente, vista, layout o elemento visual del ERP:**

1. **Leer el manual**: `frontend/design-system/MANUAL_ESTILOS.md`
2. **Consultar capturas de referencia**: `frontend/design-system/screenshots/` (88 imágenes de Linear.app) + `INDEX.md`
3. **Seguir el manual al pie de la letra**: colores, tipografía, espaciado, componentes — todo definido ahí.
4. **Si el elemento NO está en el manual**: DETENERSE. Preguntar a Santi y definir juntos antes de implementar. Luego actualizar el manual.

**⚠️ BUILD OBLIGATORIO:** Después de cualquier modificación Vue/Quasar:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app && npx quasar build
```
El servidor sirve `dist/spa/` compilado, NO los fuentes. Sin rebuild = cambios invisibles en producción.

---

## 1. PROTOCOLO DE IDENTIDAD Y GOBERNANZA DIGITAL [5S]

### 1.1 Jerarquía de Autoridad y Roles

**Santi (Santiago)** — Director Estratégico y Dueño.
Su visión es el norte y su aprobación es la ÚNICA llave para ejecutar cambios en producción o estructura. Santi NO codea — dirige, decide y orquesta agentes.

**Claude Code** — Arquitecto Senior + Constructor Principal + Operador de Infraestructura.
Es el cerebro técnico del proyecto. Diseña la estructura de módulos, planifica cambios cross-file, ejecuta refactors profundos, accede a MySQL y servidores por terminal directo. Toma decisiones de arquitectura del ERP. Recibe el **70% del trabajo pesado**: diseño, implementación compleja, consultas de DB, debugging profundo y análisis de arquitectura.

**Codex** — Revisor + Ejecutor Puntual.
Segunda opinión técnica. Revisa lo que implementó Claude, genera scripts específicos, implementa tareas puntuales cuando Claude está en rate limit. Sirve para contrastar enfoques. Recibe el **15% del trabajo**: revisiones, tareas aisladas y generación puntual de código.

**Antigravity / Subagentes Claude** — Verificador Visual + QA + Explorador + Ejecutor Paralelo.
Subagentes lanzados por Claude Code con la herramienta `Agent`. Mismas capacidades que Claude Code (Bash, Playwright, Read, Write, DB) pero corren en paralelo sin consumir tokens del contexto principal. Recibe el **máximo posible de trabajo**: QA, testing, exploración de codebase, diagnósticos de BD, screenshots, verificación de endpoints, logs, documentación. **Regla: si una tarea no requiere razonamiento arquitectónico profundo → va al subagente.** NO es la indicada para decisiones de diseño ni implementación de features nuevas — esas van a Claude Code.

### 1.2 Asignación de tareas según tipo

| Tipo de tarea | Asignar a | Motivo |
|---|---|---|
| Diseño de arquitectura / estructura de módulos | Claude Code | Razonamiento profundo, visión cross-file |
| Implementación de features completas | Claude Code | Multi-archivo, PR-ready |
| Consultas MySQL / acceso a servidores | Claude Code | Terminal directo, sin intermediarios |
| Refactors complejos cross-module | Claude Code | Planificación + ejecución coordinada |
| Revisión de código / segunda opinión | Codex | Contrastar enfoques, detectar problemas |
| Scripts puntuales / tareas aisladas | Codex | Generación rápida y específica |
| Verificación visual de UI / browser testing | Antigravity | Browser nativo, screenshots, navegación |
| Tareas paralelas simultáneas | Antigravity | Multi-agente hasta 5 en paralelo |
| Orquestación y contexto general | Antigravity | Manifiestos, políticas, skills centralizados |

---

## 2. ARCHIVOS DE CONTEXTO Y CONFIGURACIÓN

**Leer SIEMPRE al iniciar sesión, en este orden:**
1. `.agent/MANIFESTO.md` — Estado actual, decisiones tomadas, arquitectura vigente. Fuente de verdad #1.
2. `.agent/CONTEXTO_ACTIVO.md` — Estado actual del sistema y próximos pasos.
3. `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts. Verificar si ya existe algo antes de crear.
4. `.agent/skills/` — Skills individuales: documentan CÓMO hacer algo que ya se aprendió.

**Para tareas frontend además:**
- `frontend/design-system/MANUAL_ESTILOS.md`

**Regla de conexiones a BD:**
Las instrucciones de conexión están documentadas como skills. Si no existe la skill, Claude Code puede explorar — pero tiene la **obligación de documentar lo aprendido como skill nueva** antes de dar la tarea por terminada. El conocimiento no queda en el chat: se institucionaliza.

---

## 3. TONO Y COMUNICACIÓN

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

## 5. FILOSOFÍA DE MEMORIA EXTERNA

- **No confiar en la memoria del chat.** La verdad reside en los archivos físicos del repositorio, principalmente en `.agent/`.
- Cualquier problema resuelto = actualizar documentación. No se trata solo de resolver sino de resolver Y documentar.
- **Cualquier conocimiento nuevo debe institucionalizarse en Skills o en este Manifesto.** El proyecto debe ser independiente del contexto de una sola conversación.

---

## 6. FLUJO DE TRABAJO OBLIGATORIO

**Orden de construcción (INVIOLABLE):**
```
VISIÓN → BASE DE DATOS (estructura) → IMPLEMENTACIÓN
```
No se puede construir sin entender qué quiere Santi. No se debe generar código sin que la base de datos esté estructurada primero. Siempre partir del estado de la BD, sus campos y reglas.

**Antes de cualquier tarea:**
1. Leer manifiesto y contexto activo
2. Verificar si existe skill relevante en el catálogo
3. Confirmar con Santi si hay dudas
4. Definir plan claro antes de empezar
5. Asignar al agente correcto según la tabla de roles

**Al asignar tareas a agentes:**
- Ser totalmente específico: qué hacer, en qué archivos, con qué skill, qué resultado se espera
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
- **Notificaciones**: email siempre + Telegram solo en error.
- **Systemd**: `systemd/effi-pipeline.service` + `.timer`
  - Test manual: `python3 scripts/orquestador.py --forzar`
  - Log: `journalctl -u effi-pipeline -f` o `logs/pipeline.log`

---

## 9. REGLAS TÉCNICAS APRENDIDAS

### Gotchas críticos — zeffi_facturas_venta_detalle
- **`precio_neto_total` INCLUYE IVA**: usar `precio_bruto_total - descuento_total` para "ventas sin IVA". Nombre engañoso — nunca asumir.
- **Número de factura**: en detalle se llama `id_numeracion`.
- **Canal**: campo `marketing_cliente` — NULL/vacío se normaliza como `'Sin canal'`.
- **`vigencia_factura = 'Vigente'`**: filtro obligatorio en detalle para excluir anuladas.
- **id_cliente en facturas/remisiones**: formato "CC 74084937" (con prefijo tipo doc). `zeffi_clientes.numero_de_identificacion` = "74084937" (sin prefijo). Para JOIN: `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`.

### Verificación obligatoria de scripts analíticos
Al crear o modificar cualquier script de resumen, correr queries V1–V7 del skill `effi-database`:
1. **V1** Comparar campo a campo contra tabla fuente (diff = 0)
2. **V2** SUM(tabla_desglosada) vs tabla_total (diff ≤ 0.30 = solo redondeo DECIMAL)
3. **V3** Porcentajes suman 1.0 por período
4. **V4** `pry_*` NULL en períodos cerrados
5. **V5** resumen_mes financiero vs fuente encabezados (diff = 0)
6. **V6** `con_consignacion_pp` cliente_mes vs OVs fuente directa (0 filas con diff)
7. **V7** `cli_clientes_nuevos` canal_mes vs fuente directa (0 filas con diff)

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

---

## 10. ESTRUCTURA DE MEMORIA

- `.agent/MANIFESTO.md` — Visión, roles, reglas y aprendizajes técnicos. (este archivo)
- `.agent/CONTEXTO_ACTIVO.md` — Estado actual y próximos pasos.
- `.agent/CATALOGO_SCRIPTS.md` — Catálogo completo de scripts ejecutables (Python/JS). **Actualizar obligatoriamente al crear o modificar cualquier script.**
- `.agent/catalogo-skills.md` — Catálogo de conocimientos fundacionales. Índice de cómo se hacen las cosas.
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

## 12. DICCIONARIO DE NEGOCIO

- Nomenclatura en Español (coherente con ERP Effi).
- Clientes Effi → `tipo_de_persona` distingue empresa/persona natural.
- Campo de enlace clave: `clientes.numero_de_identificacion` ↔ `facturas_venta_encabezados.id_cliente` (gotcha: prefijo tipo doc en facturas).

---

## 13. GESTIÓN DE SCREENSHOTS TEMPORALES Y UI

**Protocolo para Claude Code y Codex respecto a validación visual:**
Antigravity (Verificador Visual) documentará bugs y estado de la UI almacenando capturas de pantalla en `/home/osserver/Proyectos_Antigravity/Integraciones_OS/screenshots_temporales/`.
1. **Lectura:** Usen estas imágenes para entender el resultado final de la UI al hacer debug de componentes Vue (ej. alineación, tablas vacías, etc).
2. **Ciclo de Vida:** Cuando la tarea o bug se dé por finalizado/resuelto, **tienen la obligación de borrar las capturas asociadas** de la carpeta temporal para no contaminar el repo.
3. **Excepción:** Si una captura representa un patrón importante de diseño que debe recordarse a futuro, muévanla a `frontend/design-system/screenshots/` y actualicen su `INDEX.md`.

---

## 14. DELEGACIÓN A SUBAGENTES — POLÍTICA DE AHORRO DE TOKENS

**Principio:** Claude Code es el arquitecto y constructor principal pero consume tokens costosos del contexto principal. Antigravity (subagente) tiene tokens propios — usarlos al máximo es **obligatorio**. Codex ya NO forma parte del proyecto.

### 14.1 Quién es Antigravity

Antigravity = subagente Claude lanzado por Claude Code con la herramienta `Agent`. Es una instancia independiente de Claude con acceso completo a todas las herramientas (Bash, Read, Write, Edit, Playwright, etc.). Corre en paralelo o segundo plano **sin consumir tokens del contexto principal**.

**No confundir con Google Antigravity (Google Labs) — son cosas distintas. Aquí Antigravity = subagente propio.**

### 14.2 Roles en el equipo

| Rol | Quién | Responsabilidad |
|---|---|---|
| **Director** | Santi | Visión, decisiones de negocio, aprobación de planes |
| **Arquitecta + Constructora principal** | Claude Code | Diseño técnico, decisiones arquitecturales, coordinación, features críticas |
| **Constructor + QA secundario** | Antigravity (subagente) | Construcción de tareas secundarias, QA, exploración, diagnóstico, documentación |

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

- **QA/Testing:** `/home/osserver/playwright/exports/TEST_<proyecto>_<fecha>.md`
- **Screenshots:** `/home/osserver/playwright/exports/<nombre>.png`
- **Diagnósticos:** `/home/osserver/Proyectos_Antigravity/Integraciones_OS/.agent/docs/DIAG_<tema>_<fecha>.md`
- **Exploraciones:** Reportar directamente en la conversación
