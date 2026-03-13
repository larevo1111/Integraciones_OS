# Antigravity de Google Labs — Perfil del Agente

> **Documento de referencia para el equipo OS.**
> Anticipa confusión: en este proyecto hay DOS conceptos con nombre parecido:
> - **Antigravity Google Labs** = plataforma externa de Google (este documento)
> - **Subagentes Claude** = instancias de Claude lanzadas desde Claude Code con la herramienta `Agent`
> Son completamente distintos. Este documento trata solo del primero.

---

## ¿Qué es Antigravity de Google Labs?

Es una **plataforma de desarrollo agentic** lanzada por Google Labs el 18 de noviembre de 2025, junto con Gemini 3. Se describe como un IDE "agent-first" — en lugar de ser un IDE tradicional con IA integrada, es un agente IA que tiene integradas las superficies de desarrollo (editor, terminal, browser).

Disponible en preview público, gratuito para individuos. Es un fork pesado de Visual Studio Code.

**Sitio oficial:** [Google Developers Blog — Build with Google Antigravity](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)

---

## Capacidades principales

### Modelos que usa
- **Primario**: Gemini 3.1 Pro + Gemini 3 Flash (Google)
- **Soporta también**: Claude Sonnet 4.6, Claude Opus 4.6 (Anthropic), GPT-OSS-120B

### Ventana de contexto
- Gemini 3.1 Pro soporta **hasta 1 millón de tokens** de contexto
- Esto le permite ingerir codebases completos, múltiples archivos de documentación, historiales largos de conversación
- **Gran ventaja sobre Claude Code** para tareas que requieren ver mucho código a la vez

### Dos vistas de trabajo

| Vista | Descripción |
|---|---|
| **Editor View** | IDE clásico (VSCode fork) con sidebar del agente. Flujo sincrónico. |
| **Manager View** | Centro de orquestación de múltiples agentes en paralelo. Flujo asincrónico. |

### Autonomía multiherramienta
Puede ejecutar tareas que cruzan editor + terminal + browser en un solo flujo:
- Implementa una feature
- Corre tests
- Abre el browser
- Verifica el resultado con screenshot o grabación
- Reporta con artefactos documentados

### Capacidades visuales y multimodal
- Navegación real de browser (no solo HTML — renderiza JS)
- Screenshots y grabaciones de pantalla como evidencia
- Puede leer mocks de diseño, imágenes, diagramas
- Sistema de "Artifacts": resúmenes por tarea con screenshots + comentarios estilo Google Docs

### Sistema de Skills
Similar a Claude Code — paquetes de conocimiento que se cargan solo cuando son relevantes (progressive disclosure). Evita "tool bloat".

### Multi-agente
Manager View permite orquestar varios agentes trabajando en paralelo en distintos workspaces.

---

## Fortalezas de Antigravity vs Claude Code

| Área | Antigravity | Claude Code |
|---|---|---|
| Ventana de contexto | ✅ 1M tokens (Gemini 3.1 Pro) | ⚠️ Menor (200k) |
| Navegación browser real | ✅ Nativo | ⚠️ Solo vía Playwright externo |
| Verificación visual con evidencia | ✅ Screenshots + grabaciones + Artifacts | ⚠️ Manual |
| Multi-agente paralelo | ✅ Manager View | ✅ Agent tool |
| Multimodal (imágenes, diseños) | ✅ | ✅ |
| Calidad de código | ⚠️ Aún mejorando | ✅ Superior |
| Control developer | ⚠️ Más autónomo, menos control | ✅ Mayor control |
| Análisis de contexto masivo | ✅ Ideal para codebases grandes | ⚠️ Puede perder hilo |

---

## Debilidades conocidas

- **Producto nuevo** (Nov 2025) — poco historial de producción
- **Seguridad**: configuraciones default demasiado permisivas — agentes con demasiado control pueden ejecutar comandos no deseados o acceder a archivos sensibles
- **Rate limits** en preview público
- **Calidad de código** aún por debajo de Claude en iteraciones complejas

---

## Rol de Antigravity en el equipo OS

Según la visión de Santi, Antigravity no es un sustituto de Claude Code — es un **consultor y asesor complementario**:

| Agente | Rol | Ventaja clave |
|---|---|---|
| **Claude Code** | Arquitecto + Constructor Principal | Calidad de código, razonamiento técnico profundo, base de datos, coordinación |
| **Antigravity (Google Labs)** | Consultor Secundario + Asesor de Arquitectura | Contexto de 1M tokens, navegación browser, verificación visual autónoma |
| **Subagentes Claude** (via Agent tool) | Ejecutores paralelos de Claude Code | Paralelismo sin consumir contexto principal |

### Tareas ideales para Antigravity

- **Revisión de codebase completo**: cuando hay que revisar decenas de archivos simultáneamente para dar recomendaciones de arquitectura — su ventana de 1M tokens es ideal
- **QA visual autónomo**: navegar la app en browser, tomar screenshots, validar UI sin Playwright manual
- **Segunda opinión arquitectural**: cuando Claude Code presenta un plan, Antigravity puede revisar con todo el contexto del codebase y señalar inconsistencias
- **Análisis de sistemas legacy o muy grandes**: proyectos donde el contexto es demasiado para Claude Code
- **Exploración de repositorios externos**: leer documentación masiva de APIs, librerías, frameworks

### Tareas que siguen siendo de Claude Code

- Decisiones de arquitectura definitivas (Claude Code coordina, Antigravity puede asesorar)
- Implementación de features críticas
- Consultas y operaciones en base de datos
- Coordinación del flujo de trabajo
- Todo lo que requiera historial acumulado de la conversación con Santi

---

## Cómo trabajan juntos

```
Santi define el objetivo
  → Claude Code diseña el plan + identifica tareas para Antigravity
    → Antigravity: revisa el plan con contexto completo del codebase
    → Antigravity: ejecuta tareas de alta superficie (QA, exploración, verificación)
    → Subagentes Claude: ejecutan tareas en paralelo (construcción secundaria)
  → Claude Code integra resultados + toma decisiones finales
  → Santi aprueba
```

---

## Fuentes consultadas

- [Google Developers Blog — Build with Google Antigravity](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- [VentureBeat — Antigravity agent-first architecture](https://venturebeat.com/orchestration/google-antigravity-introduces-agent-first-architecture-for-asynchronous)
- [Augment Code — Antigravity vs Claude Code](https://www.augmentcode.com/tools/google-antigravity-vs-claude-code)
- [The New Stack — Hands-On With Antigravity](https://thenewstack.io/hands-on-with-antigravity-googles-newest-ai-coding-experiment/)
- [Alex Merced — Context Management in Antigravity](https://iceberglakehouse.com/posts/2026-03-context-google-antigravity/)

*Documento creado: 2026-03-13. Actualizar si las capacidades evolucionan.*
