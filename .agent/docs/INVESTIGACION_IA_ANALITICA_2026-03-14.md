# Investigación: IA Analítica de Datos — Hallazgos 2026-03-14

Resultado de investigación profunda sobre mejores prácticas para sistemas text-to-SQL conversacionales.

## Fuentes consultadas
- Anthropic Prompting Best Practices (oficial)
- DAIL-SQL paper (arxiv 2308.15363) — 86.6% accuracy en Spider benchmark
- Defog SQL-Eval framework
- Google Vertex AI — System Instructions
- Prompting Guide — Few-Shot + Workplace Case Study

---

## Hallazgo 1 — XML en system prompt (impacto alto)

Anthropic recomienda envolver secciones del system prompt en tags XML nombrados.
El modelo las parsea de forma más precisa que texto plano.

Estructura óptima:
```xml
<rol>Quién es el agente, personalidad, tono</rol>
<restriccion_absoluta>Anti-alucinación — el modelo entiende el "por qué"</restriccion_absoluta>
<formato_respuesta>Qué hacer, nunca qué NO hacer</formato_respuesta>
<ejemplos><example>...</example></ejemplos>
```

**Regla crítica de Anthropic:** decir QUÉ HACER en lugar de QUÉ NO HACER.
- Inefectivo: "NUNCA inventes datos"
- Efectivo: "Tu respuesta será validada contra los datos reales. Solo cita cifras de esa sección."

**Pendiente:** restructurar system_prompt de analisis_datos con XML (revisar con Santi antes de implementar).

---

## Hallazgo 2 — Self-check antes de devolver SQL (impacto alto)

Añadir al prompt de generación SQL una verificación explícita:
```
Antes de devolver el SQL, verifica:
1. ¿Todas las columnas usadas existen en el DDL?
2. ¿El campo 'mes' se trata como VARCHAR 'YYYY-MM'?
3. ¿Es MariaDB-compatible (sin funciones de PostgreSQL)?
Si algo falla, corrígelo antes de devolver.
```

**Estado:** Implementado en servicio.py (sesión 2026-03-14)

---

## Hallazgo 3 — Few-shot dinámico (impacto muy alto)

En lugar de ejemplos estáticos en el prompt, guardar cada Q→SQL exitoso en tabla
y recuperar los 3 más similares antes de cada llamada. DAIL-SQL paper
identificó esto como su técnica de mayor impacto (+20% accuracy vs ejemplos fijos).

El agente aprende progresivamente del uso real — a más consultas, mejor.

**Estado:** Implementado (sesión 2026-03-14):
- Tabla `ia_ejemplos_sql` en ia_service_os
- Logging automático de cada SQL exitoso con palabras clave extraídas
- Recuperación dinámica de los 3 ejemplos más relevantes antes de generar SQL

---

## Hallazgo 4 — Orden del mensaje: pregunta al final (+30%)

Anthropic documenta: poner datos/contexto ARRIBA y la pregunta del usuario AL FINAL
mejora calidad hasta 30% en contexto largo.

Estructura óptima del mensaje a LLM:
1. DDL schema (arriba — en system)
2. Few-shot examples (arriba en system)
3. Historial de conversación (medio)
4. Datos crudos de BD (medio)
5. Pregunta del usuario (AL FINAL — siempre)

**Estado:** Arquitectura actual ya sigue este orden en servicio.py

---

## Referencias completas

| Fuente | URL |
|---|---|
| Anthropic Prompting Best Practices | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices |
| Anthropic Building Effective Agents | https://www.anthropic.com/research/building-effective-agents |
| DAIL-SQL Paper | https://arxiv.org/abs/2308.15363 |
| Defog SQL-Eval | https://github.com/defog-ai/sql-eval |
| Google System Instructions | https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions |
| Prompting Guide Few-Shot | https://www.promptingguide.ai/techniques/fewshot |
