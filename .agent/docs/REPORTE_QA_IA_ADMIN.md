# Reporte de QA - IA Admin (ia.oscomunidad.com)
**Fecha:** 2026-03-13
**Testeado por:** Antigravity

## Pruebas Exitosas
- **Dashboard:** KPIs cargan correctamente (llamadas, tokens, costo) y la pantalla es estable. El nombre "Santiago" está bien posicionado.
- **Chat Conversacional y Contexto:** El modelo responde de forma natura a "Hola" y consultas RAG ("¿Cuánto vendimos este mes?"), manteniendo el contexto al seguir con repreguntas ("¿Y en febrero?").
- **Conexiones BD:** Verificación de la conexión "Ventas Hostinger" es exitosa. Al probar, informa correctamente "52 tablas disponibles".
- **Logs:** Los registros guardan en la tabla "Agent" y "Tokens" correctamente bajo el historial de consultas del usuario.

## Bugs Encontrados y Soluciones Sugeridas

### BUG-001 — [IA Chat] Generación de Imagen falla (No devuelve imagen)
**Estado:** 🔴 Abierto
**Descripción:** Al solicitar "Genera una imagen de un árbol de ceiba", el router identifica el tipo de consulta como imagen y el LLM responde textualmente que la ha generado, pero se muestra un recuadro de error en la UI: *"Error: El modelo no devolvió una imagen. Intenta con una descripción más específica."*
**Pistas de Solución (Para Claude Code):**
1. Revisar si la instancia del agente configurado (`gemini-pro` o `gemini-flash`) posee acceso a herramientas externas de generación de red neuronal o si se está perdiendo la URL de la imagen en la respuesta del backend a la interfaz.
2. Asegurar en `ia-service` que la respuesta en formato JSON tenga la propiedad de imagen (`imageUrl` o similar) esperada por el bloque de UI de mensaje en Vue.

### BUG-002 — [IA Chat] Error en parser SQL con UNION
**Estado:** 🔴 Abierto
**Descripción:** Al preguntar *"¿Cuál fue el mes con más ventas y cuál con menos ventas?"*, el sistema intenta ejecutar un query con la estructura `UNION` u `ORDER BY`/`LIMIT` anidados, retornando el error: `Error ejecutando SQL: SQL inválido: Invalid expression / Unexpected token. Line 4, Col: 8.` La consulta llega al backend pero falla antes de su ejecución o directamente en la validación local de AST.
**Pistas de Solución (Para Claude Code):**
1. Verificar si el backend está utilizando un parser como `sqlparse` (Python) o equivalente en JS que sea muy estricto con la sintaxis de `UNION ALL` o la ubicación de los paréntesis para las subconsultas con ordenamientos.
2. Alternativa: En el system prompt del agente, agregar una regla restrictiva: *"No utilices UNION ni subconsultas con ORDER BY anidados. Para buscar máximos y mínimos, provee la tendencia o solicita los datos globales filtrados y luego extrae el máximo y mínimo de las filas devueltas"*.

### BUG-003 — [IA Logs] Falta columna de Costo en la grilla principal
**Estado:** 🟡 Abierto
**Descripción:** A diferencia del historial en tiempo real dentro del Playground que incluye el costo, la vista central de 'Logs' no muestra la columna de Costo (solo Agente y Tokens).
**Pistas de Solución (Para Claude Code):**
1. En el frontend de `ia-admin`, editar la configuración de la tabla Quasar en la página de Logs.
2. Agregar la nueva columna mapeando la llave `costo` (ej. `row.costo_usd`) y asegurar que el endpoint backend entregue dicha propiedad redondeada a 4-5 decimales para visualización.

---
*Nota: Capturas de evidencia respaldadas en `/screenshots_temporales`.*
