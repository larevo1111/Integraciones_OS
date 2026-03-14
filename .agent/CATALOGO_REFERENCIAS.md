# Catálogo de Referencias — Integraciones_OS

Registro de todas las fuentes externas, guías técnicas y documentación que informan las decisiones de arquitectura, prompting e IA del proyecto.

---

## 1. ARQUITECTURA DE AGENTES IA

### Anthropic — Building Effective Agents
- **URL**: https://www.anthropic.com/research/building-effective-agents
- **Relevancia**: Guía oficial de Anthropic sobre cómo estructurar agentes. Principios clave aplicados: pipelines multi-paso, verificación de resultados, retry loops.
- **Aplicado en**: `scripts/ia_service/servicio.py` — estructura generar_sql → ejecutar → retry → redactar

### Anthropic — Prompt Engineering Guide
- **URL**: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- **Relevancia**: Técnicas oficiales de prompting: dar identidad clara al modelo, usar ejemplos concretos (few-shot), separar instrucciones de datos.
- **Aplicado en**: `ia_tipos_consulta.system_prompt` para `analisis_datos`

### Google — Gemini Prompting Guide
- **URL**: https://ai.google.dev/gemini-api/docs/prompting-intro
- **Relevancia**: Buenas prácticas para Gemini: contexto estructurado, temperatura por tarea, instrucciones de rol explícitas.
- **Aplicado en**: Configuración de `ia_agentes` para modelos Google

### Google — Gemini System Instructions
- **URL**: https://ai.google.dev/gemini-api/docs/system-instructions
- **Relevancia**: Cómo las system instructions moldean el comportamiento del modelo de forma persistente. La identidad del agente va aquí, no en el user prompt.
- **Aplicado en**: Diseño del campo `system_prompt` en `ia_tipos_consulta`

---

## 2. TEXT-TO-SQL Y ANÁLISIS DE DATOS

### Vanna.ai — Agentic RAG for SQL
- **URL**: https://github.com/vanna-ai/vanna
- **Relevancia**: Librería open-source para text-to-SQL. Técnicas clave adoptadas: temperatura 0.0–0.1 para SQL, RAG con DDL + few-shot examples, feedback loop.
- **Aplicado en**: Temperatura hardcodeada 0.1 para `generar_sql`, diccionario de campos en system prompt, ejemplos Q→SQL

### LangChain — Text-to-SQL Best Practices
- **URL**: https://blog.langchain.com/llms-and-sql/
- **Relevancia**: Pipeline recomendado: DDL injection → SQL generation → validation → execution → response. Importancia de few-shot examples para precisión.
- **Aplicado en**: Estructura de pasos en `servicio.py`

### Amazon Nova — Text-to-SQL Architecture
- **URL**: https://aws.amazon.com/blogs/machine-learning/build-a-text-to-sql-solution-for-data-consistency-in-generative-ai-using-amazon-nova/
- **Relevancia**: Uso de modelos distintos por tarea (pequeño+rápido para SQL, mediano+fluido para narrativa). Validación de SQL antes de ejecutar. Temperatura diferenciada.
- **Aplicado en**: Decisión de temperatura 0.1 SQL / 0.5 respuesta en `ia_tipos_consulta`

### Alation — Por qué abandonaron multi-agente
- **URL**: https://www.alation.com/blog/delete-all-the-code-why-we-ditched-our-multi-agent-architecture-for-a-leaner/
- **Relevancia**: Justificación técnica para usar 1 agente principal + herramientas en lugar de orquestadores multi-agente. Menos es más en producción.
- **Aplicado en**: Decisión arquitectural de ia_service — un orquestador central, no múltiples agentes autónomos

### Prompting Guide — Few-Shot para SQL
- **URL**: https://www.promptingguide.ai/techniques/fewshot
- **Relevancia**: Los few-shot examples (pregunta → SQL correcto) mejoran precisión 15–30% en text-to-SQL. Patrón: incluir 5–10 ejemplos representativos en el system prompt.
- **Aplicado en**: Sección "EJEMPLOS DE REFERENCIA" en `analisis_datos.system_prompt` (10 ejemplos Q→SQL de Origen Silvestre)

---

## 3. PERSONALIDAD Y COMUNICACIÓN DE AGENTES IA

### Anthropic — Character and Persona in Claude
- **URL**: https://www.anthropic.com/news/claude-character
- **Relevancia**: Cómo definir una identidad coherente para un agente IA. La identidad no es una máscara — molde genuinamente el comportamiento. Dar nombre, historia, perspectiva.
- **Aplicado en**: Persona "Lara" en `analisis_datos.system_prompt` — nombre, rol, conocimiento del negocio, tono

### OpenAI — Best Practices for GPT Personas
- **URL**: https://platform.openai.com/docs/guides/prompt-engineering
- **Relevancia**: Técnicas de persona: definir quién es el modelo ANTES de decirle qué hacer. El rol moldea el tono, la profundidad y la forma de razonar.
- **Aplicado en**: Estructura del system prompt — persona primero, reglas después, ejemplos al final

---

## 4. AUTO-MEJORA Y APRENDIZAJE CONTINUO

### Self-Improving Text-to-SQL — DAIL-SQL Paper
- **URL**: https://arxiv.org/abs/2308.15363
- **Relevancia**: Sistema que selecciona dinámicamente los few-shot examples más relevantes para cada pregunta. Accuracy mejora 20%+ vs ejemplos fijos. Base para implementar RAG de ejemplos.
- **Pendiente de implementar**: RAG sobre historial de Q→SQL exitosos — cuando el sistema resuelve bien una consulta, guardarla como ejemplo para consultas similares futuras

### Vanna.ai — Training Pipeline
- **URL**: https://vanna.ai/docs/training
- **Relevancia**: Flujo de auto-mejora: usuario valida respuesta → par Q→SQL se guarda → se usa en próximas consultas similares. El agente aprende del uso real.
- **Pendiente de implementar**: Tabla `ia_ejemplos_sql` + endpoint de feedback + RAG sobre ejemplos validados

---

## 5. INSTRUCCIONES Y CONFIGURACIONES PROPIAS DEL PROYECTO

### Instrucciones de Gemini (Google Labs / Antigravity)
- **Ubicación**: `.agent/docs/ANTIGRAVITY_GOOGLE_LABS.md`
- **Relevancia**: Perfil completo de Antigravity — capacidades, limitaciones, cómo colaborar, qué tareas delegar

### Manual de Estilos ERP
- **Ubicación**: `frontend/design-system/MANUAL_ESTILOS.md`
- **Relevancia**: Sistema de diseño propio inspirado en Linear.app — colores, tipografía, componentes Vue

### Manifesto del Proyecto
- **Ubicación**: `.agent/MANIFESTO.md`
- **Relevancia**: Reglas de trabajo, roles, arquitectura general, gotchas técnicos aprendidos

### Contexto Activo
- **Ubicación**: `.agent/CONTEXTO_ACTIVO.md`
- **Relevancia**: Estado actual del sistema, próximos pasos, qué funciona

---

## 6. PENDIENTES DE INVESTIGAR / IMPLEMENTAR

| Tema | Por qué importa | Fuente de referencia |
|---|---|---|
| RAG sobre ejemplos Q→SQL propios | Auto-mejora: el bot aprende de sus propias consultas exitosas | DAIL-SQL Paper + Vanna Training |
| Feedback loop del bot | Usuario puede marcar respuesta como correcta/incorrecta → alimenta ejemplos | Vanna.ai docs |
| Modelos distintos por paso | Flash para SQL (más rápido/barato), Pro para interpretación | Amazon Nova Architecture |
| Evaluación automática de SQL | Antes de ejecutar, LLM valida sintaxis y semántica | LangChain SQL Validation |
| Alertas proactivas | Bot envía resumen a las 20:00 y detecta anomalías | Pendiente diseñar |

---

*Última actualización: 2026-03-14*
*Responsable: Claude Code*
