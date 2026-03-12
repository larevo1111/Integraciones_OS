---
description: Regla de los 3 Pasos (Anti-Alucinaciones) para Bots de IA y NLP a SQL
---

# Skill: Manejo de Agentes de Inteligencia Artificial

Este skill define la **arquitectura obligatoria** y las reglas de sistema (System Prompts) para cualquier integración de IA conversacional (ej. Bot de Telegram, Chatbots internos) que consulte datos del ERP (MariaDB).

## Problema a Evitar: La Alucinación
Los LLMs (Modelos de Lenguaje Grande) tienen la tendencia a intentar adivinar los saldos, ventas o nombres de clientes si se les pide directamente mediante un prompt ingenuo. **NUNCA debes permitir que la IA responda directamente con información de negocio basándose solo en su lógica interna**.

## LA REGLA DE LOS 3 PASOS (Premisa Inviolable)

Todo pipeline de IA en este proyecto debe operar como una **máquina de estados dividida**:

### PASO 1: Generar Código (IA)
- **Actores:** Usuario -> Orquestador de Python -> Agente IA (Claude/GPT/DeepSeek)
- **Contexto Injectado:** Pregunta del usuario + **DDL (Esquema SQL)** de las tablas analíticas (`resumen_ventas_*`) + Regiones/Gotchas.
- **Acción:** La IA **DEBE** limitarse exclusivamente a devolver String de código (una consulta SQL válida).
- **Control:** La respuesta de la IA en este paso NO se muestra al usuario.

### PASO 2: Ejecutar Código (Sistema)
- **Actores:** Orquestador de Python -> Base de Datos MariaDB -> Orquestador de Python.
- **Acción:** El script de Python intercepta el SQL de la IA, lo sanitiza (ej. comprobar que usa tablas de solo lectura o NUNCA modifica producción), se conecta a MariaDB (vía PyMySQL/SQLAlchemy) y ejecuta.
- **Salida:** Obtiene una lista de diccionarios (JSON) con los resultados reales de la base de datos (Ej. `[{"VentasNetasSinIva": 2993795, "Canal": "1.5. Mercados"}]`).

### PASO 3: Responder Usando el Resultado (IA)
- **Actores:** Orquestador (Data) -> Agente IA -> Usuario (Telegram)
- **Acción:** Python llama *otra vez* a la IA enviándole: `Mensaje Original` + `[DATOS DE BASE DE DATOS]`. 
- **System Prompt:** *"Redacta una respuesta concisa a la pregunta del usuario usando ESTRICTAMENTE los datos proporcionados. Si los datos están vacíos, indica que no hay registros. NO inventes cifras."*
- **Salida Final:** La IA formatea el markdown y Python lo empuja al Telegram.

---

## Estructura de Memoria Requerida

Cualquier motor de chat continuado (Telegram) debe almacenar su contexto en MariaDB (`bot_contexto`) con los siguientes campos clave para mantener coherencia en las conversaciones de los usuarios:

1. **`agente_ia`**: Modelo seleccionado actualmente en uso (ej. `claude-sonnet`, `gemini-free`, `deepseek-chat`). Permite switch dinámico.
2. **`conversacion_actual` (JSON)**: Ventana deslizante con los últimos **14 mensajes** estrictos (7 request del User, 7 respuestas validadas del Assistant) para dar memoria a corto plazo táctica.
3. **`resumen_contexto`**: Generado por el Agente cada par de interacciones. Comprime el contexto antiguo que "sale" de la ventana de 14 mensajes para formar la memoria semántica a largo plazo de la conversación.
4. **`fecha_inicio_conversacion`**: Timestamp para calcular edad de la sesión lógica y forzar reseteos semanales/mensuales o por comando `/reiniciar`.

---

## Arquitectura de Orquestación

- Los flujos deben construirse en Python (Scripts asíncronos).
- Al elegir APIs:
  - **Uso Estándar/Análisis Profundo:** Modelos premium (`Claude Sonnet 3.5`, `DeepSeek-V3`).
  - **Uso Masivo/Routing rápido:** Modelos free/ultra-fast (`Groq Llama 3`, `Gemini Free`).
- **Dónde Guardar Keys:** `.env` encriptado. NUNCA en la base de datos de NocoDB o tablas.
