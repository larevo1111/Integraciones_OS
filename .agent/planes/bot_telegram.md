# Plan de Construcción: Asistente IA en Telegram

**Objetivo:** Crear un bot de Telegram operado por un script en Python que sirva como interfaz de lenguaje natural para la base de datos `u768061575_os_integracion` (Hostinger) y locales, permitiendo a usuarios no técnicos obtener métricas, KPIs y resúmenes mediante IA.

---

## 1. Flujo de Interacción Principal

El bot funcionará como un orquestador entre el usuario, la base de datos y un LLM (modelo de lenguaje).

1. **Entrada (Telegram):** El usuario envía un mensaje (comando o pregunta en lenguaje natural) o toca un botón.
2. **Recepción (Python):** El script de Python recibe el mensaje vía Webhook o Polling de la API de Telegram.
3. **Recuperación de Contexto:** Python consulta la tabla `bot_contexto` (en MariaDB local) para obtener la última pregunta, respuesta, conversación actual y el LLM seleccionado por el usuario.
4. **Análisis (IA - Generación SQL):** Python envía el mensaje + contexto de la conversación + estructura de la base de datos (esquema) al LLM seleccionado. El LLM devuelve una consulta de SQL válida.
5. **Ejecución de Datos (Python):** Python ejecuta la consulta SQL en la base de datos de Hostinger (`u768061575_os_integracion`) o local y obtiene los datos brutos.
6. **Interpretación (IA - Redacción de Respuesta):** Python envía los datos brutos + la pregunta original de vuelta al LLM para que redacte una respuesta humana, amigable y estructurada.
7. **Respuesta (Telegram):** Python formatea el texto en MarkdownV2 (negritas, listas, bloque de código para tablas) y lo envía al usuario en Telegram.

---

## 2. Estructura de Base de Datos de Contexto

Se debe crear una tabla dedicada en la base de datos local (ej. `nocodb_meta` o `effi_data`) para manejar el estado del bot.

**Tabla: `bot_contexto`**
- `id` (INT, PK, Auto-increment)
- `telegram_user_id` (BIGINT, UNIQUE) - ID del usuario de Telegram.
- `username` (VARCHAR) - Nombre del usuario para personalización.
- `agente_ia` (VARCHAR) - Agente actual seleccionado (ej. "claude-sonnet").
- `ultima_pregunta` (TEXT) - Última entrada del usuario.
- `ultima_respuesta` (TEXT) - Última respuesta generada por la IA ANTES de enviarla a Telegram.
- `conversacion_actual` (JSON) - Historial de los últimos 14 mensajes (7 preguntas, 7 respuestas) para mantener el hilo corto.
- `resumen_contexto` (TEXT) - Un resumen comprimido generado por el propio agente en cada turno, que consolida la información importante discutida mucho antes de los últimos 14 mensajes. Efecto de "memoria a largo plazo".
- `fecha_inicio_conversacion` (TIMESTAMP) - Cuándo inició el hilo actual de contexto.
- `updated_at` (TIMESTAMP)

> 💡 **Nota sobre el flujo de respuesta:** El orquestador de Python guarda la `ultima_respuesta`, actualiza el JSON de `conversacion_actual`, y pide al Agente que genere el `resumen_contexto` actualizado. Al guardar, se asegura la persistencia del turno.

---

## 3. Configuración de Agentes Disponibles

**¿Dónde guardar los Agentes y sus API Keys?**
Las claves (API Keys) **NUNCA** deben ir en la base de datos. Se almacenan en el `.env` del orquestador Python (`scripts/.env`).

La configuración de qué agentes están "activos" se define en un diccionario estático en Python o un `config_ia.json`.

**Lista de Agentes Oficiales (Modelos):**
**Agentes de Pago (Premium):**
1. **Claude Sonnet 3.5 (Anthropic):** El modelo por defecto y más capaz en código/SQL.
2. **GPT-4o (OpenAI):** Alternativa fuerte y rápida.
3. **DeepSeek-V3 / R1 (DeepSeek):** Modelos premium muy eficientes en razonamiento lógico y código.

**Agentes Gratuitos (Free Tier):**
4. **Gemini Free (Google):** Excelente para ventanas de contexto masivas.
5. **DeepSeek Chat (Free):** Motor potente y económico para consultas regulares.
6. **Groq (Llama / Mixtral):** Insuperables en velocidad; ideales para enrutamiento ("¿Esto es un saludo o pide datos?").

---

## 4. ⚠️ PREMISA CRÍTICA: REGLA DE LOS 3 PASOS (Cero Alucinación)

Para garantizar que el Agente IA **jamás invente** (alucine) datos sobre facturación o KPIs, TODO el flujo del Bot y el **System Prompt** deben enforzar obligatoriamente este ciclo:

1. **Generar código:** El Agente recibe la pregunta en lenguaje natural y la estructura de la base de datos. **Debe generar SÓLO la consulta SQL exacta**, nada más.
2. **Ejecutar código:** El script de Python toma ese SQL, lo corre contra MariaDB (Hostinger o Local), y atrapa el diccionario de datos (JSON/filas).
3. **Responder usando ese resultado:** Python le envía esos datos **crudos y reales** de vuelta al Agente IA, quien ahora sí, redacta el texto amigable formateado en Telegram basado estrictamente en el paso 2.

---

## 3. Comandos e Interfaz de Botones

La idea es minimizar la escritura. El bot tendrá un menú persistente y botones en línea (InlineKeyboardMarkup).

### Lista de Comandos Principales

- `/start` o `/ayuda`: Muestra el mensaje de bienvenida y el menú principal de botones.
- `/agente`: Despliega botones para cambiar el modelo de IA base (Claude, GPT, Gemini).
- `/ventas`: Atajo para mostrar un resumen del mes actual (VentasNetasSinIva, Ticket Promedio).
- `/pipeline`: Resumen de las Remisiones (facturadas vs pendientes) del mes.
- `/kpis`: Muestra los 3 KPIs más importantes del último cierre de caja.

### Solicitudes en Lenguaje Natural (Ejemplos que la IA debe entender)
- *"¿Cuánto vendimos ayer en Mercado Saludable?"*
- *"Dame el top 3 de los productos más vendidos este mes."*
- *"¿Cuántos clientes nuevos tuvimos la semana pasada comparado con la anterior?"*

---

## 4. Alertas Proactivas (Cron Jobs)

El bot no solo responde, también empuja información. Python ejecutará rutinas automáticas (`schedule` o `cron`).

1. **Cierre de Día (20:00 hrs):** Envía un resumen diario (Ventas, Devoluciones, Productos Top).
2. **Alerta de Anomalías:** Si las ventas caen > 30% comparado con el mismo día de la semana pasada, envía un aviso.
3. **Pipeline Estancado:** Envía reporte los Viernes: "Tienes 15 remisiones de más de 10 días sin facturar".

---

## 5. Formato de Mensajes

- **Lenguaje:** Claro, directo y profesional ("Claridad Quirúrgica").
- **Marcado:** Markdown puro.
- **Visualización de Datos:** Cuando las filas excedan 4, el bot no usará texto plano. En su lugar, el bot enviará un archivo CSV para abrir en Excel, o un enlace a NocoDB/Vista web embebida.

---

## 6. Sugerencia de Vistas Embebidas (Para Tablas Complejas)

Como Telegram no renderiza bien tablas grandes en texto, la mejor solución es **Telegram Web Apps (Mini Apps)** o **Páginas Embebidas**.

**Implementación Sugerida:**
1. Crear una ruta en tu actual frontend Quasar/Vue: `menu.oscomunidad.com/bot/tabla-dinamica`.
2. Esta página cargará el componente `OsDataTable` (que ya está construido e incluye estilo Linear.app).
3. El bot de Python pasará los datos codificados por URL o mediante un hash temporal (ej. `?token=XYZ`).
4. Cuando el bot de Telegram responde a algo de más de 5 filas, en lugar de texto dice: *"Aquí tienes el reporte detallado:"* y un botón Inline de Telegram que diga **"Abrir Tabla"**.
5. Al hacer clic, se abre una ventana modal nativa en Telegram que carga tu página web Vue de Quasar con los filtros de Linear.app (con tu tema dark mode/vibrante, cristalino y elegante).

Esto mantiene la estética premium sin obligar al usuario a salir de Telegram.

---

## Instrucciones para Claude Code (Fase de Construcción):
1. **Paso 1:** Crear tabla `bot_contexto` en MariaDB local (`nocodb_meta`).
2. **Paso 2:** Crear la estructura base en Python `scripts/telegram_bot/` (usar `python-telegram-bot` v20+ async).
3. **Paso 3:** Implementar modulo de LLMs (LangChain o llamadas directas a APIs). Inyectar DDL de vistas analíticas (`resumen_ventas_*`) en el system prompt.
4. **Paso 4:** Implementar el orquestador de las querys y el formateador de Markdown.
