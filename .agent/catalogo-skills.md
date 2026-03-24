# Catálogo de Skills y Manuales — Integraciones_OS

> **Índice de TODO el conocimiento institucionalizado del proyecto.**
> Antes de implementar cualquier cosa, revisar este catálogo. Si ya existe una skill o manual relevante → usarlo. Si se aprende algo nuevo → registrarlo aquí antes de terminar la tarea.

---

## 🧠 Skills Generales (`.agent/skills/`)
Patrones técnicos reutilizables y reglas de negocio obligatorias. Aplican a cualquier agente o sesión.

| Nombre | Archivo | Descripción | Regla Crítica |
|--------|---------|-------------|---------------|
| **Servicio Central de IA** | `.agent/skills/manejo_ia.md` | Arquitectura ia_service_os: agentes, enrutamiento, RAG, multi-empresa. Sirve a todos los proyectos OS. | Regla 3 Pasos: Generar SQL → Ejecutar SQL → Responder con datos reales. NUNCA inventar cifras. |
| **Integridad de Datos** | `.agent/skills/integridad_datos.md` | 8 checks universales para verificar cualquier tabla/vista resumen: muestreo manual, suma total vs fuente, unicidad PK, porcentajes, comparativos year_ant/mes_ant, NULLs. | **Obligatorio** antes de dar por terminado cualquier script de agregación o resumen. |
| **Desarrollo Python** | `.agent/skills/desarrollo_python.md` | Límites de líneas (400/archivo, 80/función), regla de 1 responsabilidad, estructura estándar de módulos, prevención de duplicados, checklist pre-commit. Inventario actual de tamaños. | **Obligatorio** antes de escribir o modificar cualquier código Python. Nació del refactor de servicio.py (1,756→1,028 líneas). |

---

## 🤖 Skills Interactivas para Claude Code (`.claude/commands/`)
Skills en formato slash-command (`/nombre`). Claude Code las carga con la herramienta Skill.

| Comando | Archivo | Enfoque |
|---------|---------|---------|
| `/effi-database` | `.claude/commands/effi-database.md` | Estructura y gotchas de las 41 tablas `zeffi_*`. JOINs, campos de texto numérico, duplicados en `zeffi_clientes`, fechas. |
| `/effi-negocio` | `.claude/commands/effi-negocio.md` | Reglas de negocio: vigencia de facturas, mapeo de canales, atribución de consignaciones OV. |
| `/erp-frontend` | `.claude/commands/erp-frontend.md` | Stack Vue+Quasar, OsDataTable (tooltips automáticos, formateo, filtros), patrón de páginas, endpoints API. |
| `/ia-service` | `.claude/commands/ia-service.md` | Operar el Servicio Central de IA: consultar, configurar agentes, monitorear consumo, agregar API keys. |
| `/playwright-effi` | `.claude/commands/playwright-effi.md` | Selectores y trucos para scraping de exports de Effi con Playwright. |
| `/telegram-pipeline` | `.claude/commands/telegram-pipeline.md` | Variables asíncronas para alertas del orquestador Python vía Telegram. |
| `/espocrm-integracion` | `.claude/commands/espocrm-integracion.md` | Flujo de sincronía bidireccional Effi ↔ EspoCRM: campos custom, normalización de ciudades, mapeos. |
| `/tabla-vista` | `.claude/commands/tabla-vista.md` | Diseño de vistas de tablas en el ERP. |
| `/menu-erp` | `.claude/commands/menu-erp.md` | Diseño y estructura del menú del ERP. |

---

## 📖 Manuales (archivos de referencia detallada)
Guías de referencia para humanos y agentes. Más extensos que las skills — contienen estándares, políticas y ejemplos completos.

| Manual | Archivo | Contenido |
|--------|---------|-----------|
| **Estilos Frontend** | `frontend/design-system/MANUAL_ESTILOS.md` | Fuente de verdad única del diseño visual: colores, tipografía, espaciado, componentes, CSS variables. **Leer obligatoriamente antes de cualquier tarea de UI.** |
| **Testing y QA** | `.agent/INSTRUCCIONES_TESTING.md` | Política completa de QA: roles, herramientas, protocolo de screenshots, ciclo de vida de bugs, checklist por módulo. **Leer antes de cualquier sesión de QA.** |
| **Servicio IA — Manual completo** | `.agent/manuales/ia_service_manual.md` | 24 secciones: arquitectura, 8 capas de contexto, tipos, agentes, RAG, roles, gestor admin. v2.8. |
| **Comparación de Agentes IA** | `.agent/docs/COMPARACION_AGENTES_IA.md` | Benchmark 3 rondas (105 llamadas) comparando 5 agentes en rol SQL y respuesta. Incluye decisión aplicada y cómo re-ejecutar. |

---

## ⚠️ REGLA DE ACTUALIZACIÓN

**Obligatorio para Claude Code y Antigravity:**
- Al resolver un bug no trivial → documentar el gotcha en la skill del dominio + MANIFESTO sección 9
- Al crear un patrón técnico nuevo → crear/actualizar skill + agregar entrada aquí
- Al crear un manual nuevo → agregar entrada en la sección Manuales
- Al crear o modificar un script → actualizar `.agent/CATALOGO_SCRIPTS.md`

**Esta regla aplica ANTES de dar la tarea por terminada, no después.**
