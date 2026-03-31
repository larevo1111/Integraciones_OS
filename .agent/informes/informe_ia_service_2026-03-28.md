# Informe Detallado — IA Service Origen Silvestre
**Fecha**: 2026-03-28 | **Período analizado**: 12 mar – 28 mar 2026 (17 días)

---

## 1. Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Total consultas | 1,983 |
| Gasto total | $12.31 USD |
| Promedio diario | 132 consultas/día |
| Costo promedio por consulta | $0.0062 USD (~$25 COP) |
| Usuarios activos | 2 (Santiago nivel 7, Jen nivel 5) |
| Tasa de éxito SQL | 87% (767 de 880 consultas analíticas) |
| Tasa de error general | 2.6% |

**Conclusión rápida**: el sistema funciona. $12 USD en 17 días para 1,983 consultas. El 69% del gasto se fue en gemini-pro (177 consultas) — agente premium que ya casi no se usa.

---

## 2. Desglose de consultas por tipo

| Tipo | Consultas | % | Costo | Latencia avg | Para qué sirve |
|---|---|---|---|---|---|
| analisis_datos | 861 | 43% | $11.74 | 17.7s | Preguntas sobre ventas, inventario, cartera → genera SQL |
| router | 556 | 28% | $0.11 | <1s | Clasificar la pregunta (tipo + tema). Groq gratis |
| resumen | 244 | 12% | $0.03 | <1s | Comprimir historial de conversación. Cerebras gratis |
| conversacion | 215 | 11% | $0.36 | 9.9s | Chat normal (no requiere BD) |
| aprendizaje | 46 | 2% | $0.01 | 5.6s | Protocolo Sócrates — IA aprende reglas nuevas |
| redaccion | 30 | 2% | $0.05 | 7.9s | Generar textos, emails, etc |
| busqueda_web | 11 | <1% | $0.00 | 10.1s | Buscar info en internet |
| otros | 20 | 1% | $0.01 | — | Imagen, clasificación, depurador |

**Lo importante**: análisis de datos = 43% de las consultas pero 95% del costo ($11.74 de $12.31). Es el tipo que más importa optimizar.

---

## 3. Agentes — quién hace qué y cuánto cuesta

### 3.1 Uso y costo por agente

| Agente | Consultas | Avg input | Avg output | Costo total | % del gasto* | Rol principal |
|---|---|---|---|---|---|---|
| gemini-pro | 177 | 33,214 | 579 | **$8.37** | **69%** | Analítico premium (nivel 6+) |
| gemini-flash | 750 | 49,785 | 463 | $2.57 | 21% | Analítico default actual |
| claude-sonnet | 5 | 33,771 | 822 | $0.57 | 5% | Documentos premium |
| gpt-oss-120b | 34 | 45,942 | 312 | $0.24 | 2% | Alternativa (poco usado) |
| gemini-flash-lite | 223 | 33,231 | 193 | $0.22 | 2% | Router fallback + analítico ligero |
| cerebras-llama | 517 | 4,690 | 200 | $0.13 | 1% | Resúmenes (gratis en la práctica) |
| deepseek-chat | 22 | 25,240 | 881 | $0.08 | <1% | Respaldo (lento: 45s avg) |
| groq-llama | 252 | 2,000 | 256 | $0.00 | 0% | Router principal (gratis) |

*% del gasto excluye canal "interno" (router + resúmenes)

### 3.2 Hallazgos clave

1. **gemini-pro se comió el 69% del presupuesto** ($8.37 de $12.17). Son 177 consultas × $0.047/consulta. Esto fue principalmente durante benchmarks y pruebas iniciales — ya está restringido a nivel 6+.

2. **gemini-flash es 9x más barato que pro** para el mismo trabajo ($0.0034/consulta vs $0.047/consulta). Es el default actual para análisis de datos y funciona bien.

3. **gpt-oss-120b no aporta valor**: más caro que flash ($0.007/consulta), más lento (15s vs 14s), y solo 34 consultas históricas. Candidato a desactivar.

4. **deepseek-chat es muy lento**: 45s promedio de latencia. Solo 22 consultas. Funciona como respaldo pero no es práctico.

5. **groq + cerebras = infraestructura gratis**: 769 consultas combinadas, $0.13 total. Manejan routing y resúmenes perfectamente.

---

## 4. Rendimiento y latencia

### 4.1 Distribución de tiempos (consultas analíticas)

| Rango | Consultas | % |
|---|---|---|
| < 5 segundos | 23 | 3% |
| 5 – 10 segundos | 162 | 18% |
| **10 – 20 segundos** | **441** | **50%** |
| 20 – 30 segundos | 165 | 19% |
| > 30 segundos | 89 | 10% |

**La mitad de las consultas analíticas tardan 10-20 segundos.** Esto incluye: routing (~0.1s) + generación SQL (~5-10s) + ejecución SQL en Hostinger (~1-3s) + generación respuesta (~5-10s).

El 10% que supera 30s son consultas complejas (JOINs múltiples, subqueries) o retries por SQL fallido.

### 4.2 Latencia por agente (analíticas)

| Agente | Avg | Min | Max |
|---|---|---|---|
| groq-llama | 0.1s | 0s | 3.8s |
| cerebras-llama | 0.7s | 0s | 38.7s |
| gemini-flash-lite | 7.4s | 0s | 45.3s |
| gemini-flash | 13.8s | 2.2s | 59.1s |
| gpt-oss-120b | 15.2s | 2.9s | 26.5s |
| claude-sonnet | 20.3s | 3.7s | 50.4s |
| gemini-pro | 23.3s | 4.3s | 63.7s |
| deepseek-chat | 45.1s | 8.4s | 98.1s |

---

## 5. Errores

### 5.1 Tasa de error: 2.6% (52 de 1,983)

| Error | Veces | Causa |
|---|---|---|
| HTTP 429 — Groq rate limit | 726* | Groq agotaba tokens diarios (100K). Ya corregido: resúmenes pasados a cerebras |
| HTTP 429 — tokens/día exceeded | 63* | Mismo problema con Groq |
| SQL inválido generado | 12 | LLM genera SQL con errores de sintaxis |
| Modelo no generó imagen | 7 | gemini-image no siempre responde con imagen |
| Timeout >30s | 4 | Consultas muy pesadas |
| Auth error (401) | 3 | API key incorrecta (ya corregido) |

*Los 429 de Groq son registros del circuit breaker — el usuario NO vio error porque el sistema hizo fallback automático a otro agente.

### 5.2 Tasa de éxito SQL

| Métrica | Valor |
|---|---|
| Total consultas analíticas | 880 |
| SQL generado exitosamente | 767 (87%) |
| SQL con error | 47 (5%) |
| Sin SQL (usó caché o sin_sql) | 66 (8%) |

**87% de éxito en primera generación SQL es bueno.** Los fallos se manejan con retry automático (con columnas reales del DESCRIBE).

---

## 6. Canales de uso

| Canal | Consultas | Costo | Qué es |
|---|---|---|---|
| interno | 798 | $0.13 | Llamadas automáticas del pipeline (router, resúmenes, depurador) |
| api | 650 | $7.56 | Llamadas desde el ERP web (ia.oscomunidad.com) |
| test | 303 | $2.12 | Benchmarks y pruebas durante desarrollo |
| **telegram** | **203** | **$2.06** | **Uso real del bot por usuarios** |
| script | 15 | $0.06 | Mejora continua automatizada |
| playground | 10 | $0.18 | Pruebas desde el admin panel |
| whatsapp | 4 | $0.19 | Pruebas WA Bridge |

**Uso real (telegram)**: 203 consultas, $2.06 USD → $0.01/consulta. Es lo que Santi y Jen usan día a día.

---

## 7. Consumo diario (últimos 14 días)

| Día | Consultas | Costo | Notas |
|---|---|---|---|
| Mar 14 | 41 | $0.57 | |
| Mar 15 | 77 | $1.51 | Benchmarks gemini-pro |
| Mar 16 | 146 | $3.79 | Benchmarks intensivos |
| Mar 17 | 49 | $0.13 | |
| Mar 18 | 139 | $0.44 | Flash ya era default |
| Mar 19 | 61 | $0.62 | |
| Mar 20 | 764 | $1.75 | Pico de uso: mejora continua + benchmarks |
| Mar 22 | 224 | $0.42 | Config definitiva de agentes |
| Mar 23 | 84 | $0.12 | |
| Mar 24 | 32 | $0.04 | |
| Mar 26 | 5 | $0.01 | Día tranquilo |
| Mar 27 | 15 | $0.01 | |
| **Mar 28** | **177** | **$0.16** | Hoy (incluye depuración de lógica de negocio) |

**Tendencia**: el gasto se redujo drásticamente después de sacar gemini-pro del default. Semana 11 ($4.80) → Semana 12 ($7.16, pico de benchmarks) → **Semana 13 ($0.35)** ← esto es el costo real operativo.

**Proyección mensual actual: ~$1.50 USD/mes** (basado en semana 13).

---

## 8. Base de conocimiento — estado actual

| Componente | Cantidad | Estado |
|---|---|---|
| Reglas de negocio activas | 16 (1,059 palabras) | Depuradas hoy — sin duplicados, keywords correctos |
| Reglas siempre_presente | 3 (#1 auto-conocimiento, #32 formato, #38 SQL gotchas) | |
| Ejemplos SQL | 435 | Limpios — 0 duplicados, 0 con CURDATE() |
| Fragmentos RAG | 39 | |
| Temas | 7 (comercial, finanzas, producción, admin, marketing, estrategia, general) | |
| Esquema BD (DDL) | 1 activo (Comercial, 12KB) | Los otros 6 temas no tienen DDL — solo el comercial |
| Conversaciones | 275 total, 45 activas esta semana | |

### Protecciones activas
- `guardar_ejemplo_sql()` rechaza SQL con CURDATE/NOW/CURRENT_DATE antes de guardar
- Depurador automático comprime cuando reglas >1,000 palabras
- Git hook pre-commit bloquea patrones timezone prohibidos en código

---

## 9. Arquitectura de procesamiento (cómo fluye una consulta)

```
Usuario pregunta por Telegram
        │
        ▼
   [ROUTING] groq-llama (gratis, <1s)
   Clasifica: tipo + tema + requiere_sql + requiere_nuevo_sql
        │
        ▼
   [CONTEXTO] 8 capas se arman en paralelo:
   0. Fecha/hora Colombia
   1. Reglas negocio (SP + keywords match)
   2. System prompt del tipo
   3. RAG (FULLTEXT search)
   4. DDL tablas Hostinger (caché 1h)
   5. Resumen conversación comprimido
   6. Últimos 5 mensajes verbatim
   7. Caché SQL (último resultado)
   8. Ejemplos SQL (embeddings similarity)
        │
        ▼
   [GENERACIÓN SQL] gemini-flash (~10s)
   → Si falla: retry con DESCRIBE columnas reales
        │
        ▼
   [EJECUCIÓN] Query a Hostinger vía SSH
        │
        ▼
   [RESPUESTA] gemini-flash genera texto con los datos
        │
        ▼
   [BOT] Viñetas en chat + botón "Ver tabla" si >2 filas
        │
        ▼
   [APRENDIZAJE] Guarda ejemplo Q→SQL (si pasa validación)
   [RESUMEN] Comprime historial con cerebras (gratis)
```

---

## 10. Preguntas más frecuentes (uso real)

1. ¿Cuánto vendimos en total este mes?
2. ¿Cuántas órdenes de producción están vigentes?
3. ¿Cuál fue el top 3 de canales de venta?
4. ¿Cuál fue el producto más vendido?
5. ¿Cuánto hay en cartera vencida?
6. ¿Cuánto stock tenemos de productos terminados?
7. ¿Cuánto hay en remisiones pendientes?
8. ¿Cuánto valor hay en consignación activa?
9. Ventas 2026 vs 2025
10. Margen promedio por canal

---

## 11. Usuarios registrados

| Usuario | Email principal | Nivel | Rol | Uso |
|---|---|---|---|---|
| Santiago | santiago@origensilvestre.com | 7 (admin) | admin | Usa todos los agentes, incluyendo SA |
| Jen | jen@origensilvestre.com | 5 | viewer | Solo agentes nivel 1-5 |

Hay 4 registros extra de Santiago (emails alternativos) y 1 de Jennifer duplicado inactivo.

---

## 12. Oportunidades y recomendaciones

### Ahorro inmediato
- **Desactivar gpt-oss-120b**: más caro que flash, no aporta valor, solo 34 usos históricos. Ahorro: evitar uso accidental.
- **deepseek-chat**: considerar desactivar. 45s de latencia no es práctico. Solo mantener si se necesita como respaldo de emergencia.

### Rendimiento
- **Latencia de 10-20s es aceptable** para consultas analíticas complejas (53 tablas DDL). Difícil reducir sin sacrificar calidad.
- **Los 6 esquemas vacíos** (Admin, Estrategia, Finanzas, Marketing, Producción, General) podrían activarse gradualmente para reducir el DDL enviado (hoy se mandan las 53 tablas siempre).

### Conocimiento
- **El sistema de aprendizaje funciona** pero necesita supervisión periódica para evitar acumulación de duplicados (ya hay protección para CURDATE, falta para otros patrones).
- **Los 39 fragmentos RAG** no se están usando mucho — evaluar si vale la pena alimentarlos o si las reglas de negocio cubren todo.

---

*Informe generado por Claude Code — datos de ia_service_os (MariaDB local)*
