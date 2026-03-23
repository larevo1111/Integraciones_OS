# Plan de Mejora — Servicio IA Origen Silvestre

**Fecha**: 2026-03-23
**Estado**: Propuesto — pendiente aprobación de Santi
**Elaborado por**: Claude Code (Arquitecto)

---

## Resumen ejecutivo

El servicio de IA funciona. Enruta, genera SQL, responde, aprende. Pero tiene dos problemas estructurales que frenan su crecimiento:

1. **Todo vive en un solo archivo** (servicio.py = 1,756 líneas con 5 responsabilidades mezcladas)
2. **El aprendizaje es pasivo y frágil** — depende de que el LLM escriba una etiqueta exacta, los 658 ejemplos SQL guardados no se aprovechan (0 tienen embedding), y no hay forma de corregir errores automáticamente

El plan propone resolver estos dos problemas sin parches, sin aumentar tokens, y dejando la estructura preparada para que un script CLI con Claude Code pueda mejorar el sistema automáticamente con cada consulta.

---

## Diagnóstico con datos reales (no opiniones)

### Lo que dice la BD (ia_logs, últimos 3 días)

| Métrica | Valor | Problema |
|---|---|---|
| Total consultas | 1,730 | — |
| Tasa error router (groq) | 51% (435/858) | Groq agota rate limit → cae a cerebras |
| Tasa error resumen | 71% (305/429) | Mismo: groq agotado (ya corregido → cerebras) |
| Tokens promedio analisis_datos | **70,054** | DDL completo se envía SIEMPRE, incluso si el tema tiene tablas específicas |
| Ejemplos SQL guardados | 658 | Bien |
| Ejemplos con embedding | **0** | Búsqueda semántica muerta. `migrar_embeddings_faltantes()` nunca se ejecutó |
| `veces_usado` de ejemplos | Casi todos = 1 | Nunca se incrementa → no se sabe cuáles son valiosos |
| Errores analisis_datos | 8 (2.2%) | Aceptable, pero todos son SQLs mal generados (columnas inexistentes) |

### Los dos puntos más débiles

**1. Limpieza de código: 5.5/10**
`servicio.py` mezcla:
- Orquestación (punto de entrada, flujo de pasos)
- Seguridad (rate limit, circuit breaker, verificar_limites)
- Alertas (Telegram, gasto)
- Aprendizaje (guardar reglas, guardar SQL, depurar lógica)
- Utilidades (obtener fecha máxima, columnas reales, cobertura)

Esto significa que para cambiar algo del depurador, hay que navegar entre rate limits y alertas de gasto. Un cambio en aprendizaje puede romper seguridad.

**2. Capacidad de aprendizaje: 7.5/10**
- El aprendizaje depende de regex: `[GUARDAR_NEGOCIO]...[/GUARDAR_NEGOCIO]`. Si el LLM escribe `[GUARDAR NEGOCIO]` (sin guion bajo), no detecta nada.
- Los 658 ejemplos SQL están guardados pero son inútiles: 0 embeddings generados, la búsqueda semántica retorna vacío.
- No existe retroalimentación: si un SQL falla, se reintenta, pero el error no se registra para evitarlo en el futuro.
- No existe un proceso automático que revise consultas fallidas y mejore los prompts.
- No existe una manera de que el usuario marque una respuesta como "mala" para que el sistema aprenda.

---

## Referentes de sistemas bien hechos

Antes de proponer mejoras, estudié cómo resuelven esto los frameworks más maduros:

| Framework | Qué hace bien | Qué aplicamos |
|---|---|---|
| **DSPy** (Stanford) | "Programming, not prompting" — optimiza prompts automáticamente usando ejemplos etiquetados | La idea del evaluador CLI: cada consulta fallida genera un caso de prueba, y un optimizador ajusta las instrucciones del system prompt |
| **Instructor** (Jason Liu) | Salidas tipadas con validación y retry automático | Reemplazar regex por validación estructurada de la respuesta del LLM |
| **Braintrust/Promptfoo** | Evaluación continua de calidad de prompts | Script CLI que corre una suite de tests contra el servicio y califica |
| **LangGraph** | Pipeline como grafo con nodos especializados | Separar pasos en módulos independientes con interfaz estándar |
| **Semantic Kernel** | Plugins con descripción semántica para que el orquestador elija | El sistema de temas + tipos ya lo hace parcialmente |

---

## Plan detallado

### Fase 1: Separar servicio.py en módulos (Limpieza — nota 5.5 → 8.5)

**Objetivo**: Que cada responsabilidad viva en su propio archivo, con interfaz clara.

**Regla clave**: No cambiar NINGÚN comportamiento. Solo mover código. El servicio debe funcionar exactamente igual antes y después.

#### Módulos propuestos

```
scripts/ia_service/
├── servicio.py          ← Orquestador (~400 líneas). Solo el flujo: enrutar → resolver agente → ejecutar pasos → devolver
├── seguridad.py         ← Rate limit, circuit breaker, verificar_limites (~180 líneas)
├── alertas.py           ← Notificaciones Telegram, verificar gasto (~80 líneas)
├── aprendizaje.py       ← Guardar reglas, guardar SQL, procesar bloque, depurador (~250 líneas)
├── utilidades_sql.py    ← Obtener columnas reales, fecha máxima, cobertura de tablas (~150 líneas)
├── contexto.py          ← (ya existe — sin cambios)
├── ejecutor_sql.py      ← (ya existe — sin cambios)
├── formateador.py       ← (ya existe — sin cambios)
├── esquema.py           ← (ya existe — sin cambios)
├── embeddings.py        ← (ya existe — mejoras en Fase 2)
├── rag.py               ← (ya existe — sin cambios)
└── config.py            ← (ya existe — sin cambios)
```

#### Qué va en cada archivo

| Archivo nuevo | Funciones que se mueven desde servicio.py |
|---|---|
| `seguridad.py` | `verificar_rate_usuario()`, `verificar_limites()`, `_resolver_agente_disponible()`, `_get_config()`, `_get_config_simple()`, `_slugs_router()`, `_nivel_usuario()`, `_mejor_agente_para_nivel()` |
| `alertas.py` | `_notificar()`, `_verificar_gasto_y_notificar()`, `_alertas_enviadas` dict |
| `aprendizaje.py` | `_procesar_bloque_aprendizaje()`, `_guardar_ejemplo_sql()`, `_obtener_ejemplos_dinamicos()`, `_extraer_palabras_clave()`, `_depurar_logica_negocio()`, `_generar_resumen_groq()`, `_obtener_logica_negocio()` |
| `utilidades_sql.py` | `_obtener_columnas_reales()`, `_obtener_fecha_maxima()`, `_obtener_cobertura_tablas()` |

#### Lo que queda en servicio.py

```python
# servicio.py — solo el orquestador
from .seguridad import verificar_rate_usuario, verificar_limites, ...
from .alertas import notificar, verificar_gasto
from .aprendizaje import guardar_ejemplo_sql, obtener_ejemplos, ...
from .utilidades_sql import obtener_columnas_reales, ...

def consultar(...) -> dict:     # punto de entrada — flujo de pasos
def _enrutar(...) -> tuple:     # clasificación de intención
def _cargar_agente(...):        # lectura de BD
def _cargar_tipo(...):          # lectura de BD
def _llamar_agente(...):        # despacho a proveedor
def _construir_prompt_respuesta(...):  # prompt builder
def _calcular_costo(...):       # cálculo simple
def _guardar_log(...):          # inserción de log
def _log_aux(...):              # log auxiliar
```

**Riesgo**: Bajo. Es solo mover funciones y actualizar imports. Tests de verificación: llamar a `/ia/consultar` con los mismos 10 tipos de consulta antes y después.

**Esfuerzo**: ~2 horas.

**Tareas para Antigravity (Google Labs)**: Revisar que no se pierda ninguna importación cruzada. Verificar que las funciones "privadas" (con `_`) que se usan desde servicio.py se expongan correctamente.

**Tareas para Subagentes Claude**: Un subagente puede hacer el refactor mecánico (mover funciones, actualizar imports) en un worktree aislado.

---

### Fase 2: Activar el aprendizaje real (nota 7.5 → 9.0)

**Objetivo**: Que el sistema aprenda de cada consulta — exitosa o fallida — sin depender de etiquetas frágiles.

#### 2.1 — Activar embeddings (lo más urgente — cero riesgo)

**Problema**: Hay 658 ejemplos Q→SQL guardados. Ninguno tiene embedding. La función `migrar_embeddings_faltantes()` existe pero nadie la llama.

**Solución**:
1. Correr `migrar_embeddings_faltantes('ori_sil_2')` una vez para generar los 658 embeddings
2. Agregar un cron o llamada en el pipeline para que los nuevos ejemplos se verifiquen periódicamente
3. Verificar que `buscar_ejemplos_semanticos()` ahora retorna resultados

**Impacto**: La generación de SQL pasa de "cero contexto de ejemplos previos" a "3 ejemplos semánticamente relevantes". Esto reduce errores SQL porque el LLM ve cómo se resolvieron preguntas similares antes. Sin tokens adicionales significativos (los ejemplos son ~200 tokens, no 28K).

**Esfuerzo**: 15 minutos.

#### 2.2 — Registrar feedback negativo (consultas fallidas)

**Problema actual**: Cuando un SQL falla, se reintenta y se olvida. El mismo error puede repetirse 100 veces.

**Solución**: Nueva tabla `ia_feedback`
```sql
CREATE TABLE ia_feedback (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2',
  log_id INT,                          -- referencia a ia_logs
  tipo ENUM('sql_error','respuesta_mala','sql_bueno','correccion') NOT NULL,
  pregunta TEXT,                        -- pregunta original
  sql_fallido TEXT,                     -- SQL que falló
  sql_correcto TEXT,                    -- SQL corregido (por Claude CLI o usuario)
  error_original TEXT,                  -- mensaje de error
  notas TEXT,                           -- explicación de la corrección
  procesado TINYINT DEFAULT 0,         -- 0=pendiente, 1=incorporado al prompt
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Flujo**:
1. Cuando un SQL falla (incluso si el retry lo corrige): insertar en `ia_feedback` con tipo='sql_error'
2. Cuando el retry exitoso produce un SQL correcto: insertar con tipo='correccion', `sql_fallido` + `sql_correcto`
3. Estas correcciones se pueden usar como few-shot examples para consultas similares futuras

**Impacto**: El sistema acumula un registro de "errores → correcciones" que es exactamente lo que necesita un script CLI para mejorar los prompts.

**Esfuerzo**: ~1 hora.

#### 2.3 — Reemplazar regex frágil por validación robusta

**Problema**: `_procesar_bloque_aprendizaje()` usa regex para detectar `[GUARDAR_NEGOCIO]...[/GUARDAR_NEGOCIO]`. Si el LLM escribe mal la etiqueta, se pierde el aprendizaje silenciosamente.

**Solución**: Dos cambios independientes:

**A) Agregar variantes tolerantes en el regex** (inmediato, 5 min):
```python
# En vez de solo [GUARDAR_NEGOCIO], aceptar variantes comunes
patron = r'\[GUARDAR[_ ]NEGOCIO\](.*?)\[/GUARDAR[_ ]NEGOCIO\]'
```

**B) Migrar a JSON estructurado (Fase 2b)**: Cambiar la instrucción del system prompt de aprendizaje para que el LLM devuelva un JSON en vez de etiquetas:
```json
{"guardar": {"concepto": "...", "keywords": "...", "explicacion": "..."}}
```
Detectar JSON es 100x más robusto que detectar una etiqueta inventada. Ya existe `formateador.extraer_json()` que hace esto.

**Impacto**: Se pierde 0% de aprendizaje por formato incorrecto.

**Esfuerzo**: Opción A = 5 min. Opción B = 30 min.

#### 2.4 — Incrementar `veces_usado` para aprendizaje acumulativo

**Problema**: `ia_ejemplos_sql.veces_usado` siempre es 1. Nunca se incrementa. No sabemos cuáles ejemplos son valiosos.

**Solución**: En `_obtener_ejemplos_dinamicos()`, cuando se recuperan ejemplos para inyectar:
```python
# Después de seleccionar los N ejemplos
ids = [f['id'] for f in filas_seleccionadas]
cur.execute(f"UPDATE ia_ejemplos_sql SET veces_usado = veces_usado + 1, ultima_vez = NOW() WHERE id IN ({','.join(['%s']*len(ids))})", ids)
```

**Impacto**: Con el tiempo, los ejemplos más reutilizados suben de ranking. Los que nunca se usan pueden limpiarse automáticamente. Esto es **auto-optimización**: el sistema se vuelve más eficiente solo con usarlo.

**Esfuerzo**: 10 minutos.

---

### Fase 3: Reducción de tokens — DDL por tema (nota eficiencia 6 → 9)

**Objetivo**: Bajar el consumo de 70K tokens promedio a ~15K sin perder capacidad.

**Problema actual**: Cada consulta de `analisis_datos` envía el DDL de **todas** las tablas (~28K tokens), aunque el enrutador ya clasificó el tema y cada tema tiene su `schema_tablas` definido.

**Cómo funciona hoy** (el bug está en la prioridad):
```python
# servicio.py línea 1086-1097
if tipo_cfg.get('requiere_estructura'):
    if tema_cfg and tema_cfg.get('schema_tablas'):
        tablas_tema = json.loads(tema_cfg['schema_tablas'])
        if tablas_tema:
            ddl = esquema.obtener_ddl(tablas=tablas_tema)  # ← SÍ filtra por tema
        else:
            ddl = esquema.obtener_ddl()  # ← DDL completo
    else:
        ddl = esquema.obtener_ddl()  # ← DDL completo (cae aquí si tema_cfg=None)
```

El código **ya soporta** DDL filtrado por tema. Pero cuando `tema_cfg` no existe (tema=None o tema='general' sin schema), cae al DDL completo.

**Solución (3 partes)**:

**A) Verificar que todos los temas tengan `schema_tablas` bien configurado** (ya lo están — verificado arriba).

**B) Asegurar que el tema 'general' también filtre** — actualmente tiene 6 tablas definidas, pero la ruta legacy en `esquema.py` ignora esto y carga las 28 tablas completas.

**C) Ruta futura: DDL dinámico por pregunta** — en vez de enviar todas las tablas del tema, usar la pregunta para seleccionar solo las tablas relevantes (similar a cómo DSPy selecciona herramientas). Esto requiere un índice semántico de tablas. **Diferir para Fase 4**.

**Impacto esperado**:
- Tema "comercial" (21 tablas) → reducción ~25%
- Tema "producción" (5 tablas) → reducción ~80%
- Tema "finanzas" (8 tablas) → reducción ~70%
- Promedio estimado: 70K → ~20K tokens

**Esfuerzo**: Parte A+B = 30 min. Parte C = Fase futura.

---

### Fase 4: Script CLI de mejora continua (el objetivo final)

**Objetivo**: Un script que corra periódicamente (manual o cron), analice consultas fallidas, y mejore el sistema usando Claude Code como verificador.

#### Diseño del script: `scripts/ia_mejora_continua.py`

```
┌─────────────────────────────────────────────────────┐
│          FLUJO DE MEJORA CONTINUA                   │
│                                                     │
│  1. Leer ia_feedback WHERE procesado=0              │
│     (errores SQL, respuestas malas)                 │
│                                                     │
│  2. Para cada error:                                │
│     a. Analizar la pregunta + SQL fallido            │
│     b. Generar SQL corregido (Claude CLI)            │
│     c. Verificar contra BD real                      │
│     d. Si funciona → guardar en ia_ejemplos_sql      │
│     e. Marcar procesado=1                            │
│                                                     │
│  3. Detectar patrones recurrentes:                   │
│     - ¿Siempre falla con la misma tabla?             │
│     - ¿Siempre confunde la misma columna?            │
│     - ¿Siempre falla con JOINs complejos?            │
│                                                     │
│  4. Si hay patrón → generar regla nueva:             │
│     - INSERT INTO ia_logica_negocio                  │
│     - O ajustar <reglas_sql> del system prompt       │
│                                                     │
│  5. Correr suite de pruebas para verificar           │
│     que las mejoras no rompieron nada                │
│                                                     │
│  6. Reportar: "3 errores corregidos, 2 reglas        │
│     nuevas, 1 ejemplo SQL agregado"                  │
└─────────────────────────────────────────────────────┘
```

#### Componentes del script

**A) Recolector de errores** — lee `ia_feedback` y `ia_logs` con errores:
```python
def recolectar_pendientes(empresa):
    """Lee errores no procesados de ia_feedback + ia_logs con errores SQL recientes."""
    ...
```

**B) Corrector SQL** — usa Claude CLI para generar la corrección:
```bash
# El script llama a Claude Code vía CLI
claude -p "Dado este esquema de BD: [DDL reducido]
Esta pregunta del usuario: [pregunta]
Este SQL que falló: [sql_fallido]
Con este error: [error]

Genera el SQL correcto. Solo responde con el SQL."
```

**C) Verificador** — ejecuta el SQL corregido contra la BD en modo READ ONLY:
```python
def verificar_sql(sql_corregido):
    """Ejecuta contra BD real y verifica que retorna datos coherentes."""
    resultado = ejecutor_sql.ejecutar(sql_corregido)
    return resultado['ok'] and resultado['total'] > 0
```

**D) Incorporador** — guarda el ejemplo bueno:
```python
def incorporar_mejora(pregunta, sql_correcto):
    """Guarda en ia_ejemplos_sql + genera embedding."""
    _guardar_ejemplo_sql(empresa, pregunta, sql_correcto)
```

**E) Detector de patrones** — analiza errores repetidos:
```python
def detectar_patrones(errores):
    """Agrupa errores por tipo y genera reglas si hay ≥3 del mismo tipo."""
    # Ej: si 5 errores usan ncvd.id_numeracion → agregar regla:
    # "La tabla zeffi_notas_credito_venta_detalle usa id_nota_credito, no id_numeracion"
```

**F) Suite de pruebas** — verificación post-mejora:
```python
SUITE_PRUEBAS = [
    ("¿Cuánto vendimos ayer?", "analisis_datos", lambda r: r['ok'] and r.get('tabla')),
    ("Hola, ¿cómo estás?", "conversacion", lambda r: r['ok'] and 'hola' in r['respuesta'].lower()),
    ("Ventas netas menos devoluciones de enero 2026", "analisis_datos", lambda r: r['ok']),
    # ... 15+ pruebas más
]
```

#### Cómo el usuario enseña (sin código)

**Opción 1: Botón "Mala respuesta" en Telegram**
- El usuario toca un botón (inline keyboard) → guarda en `ia_feedback` con tipo='respuesta_mala'
- El script CLI lo recoge y lo corrige en el siguiente ciclo

**Opción 2: Comando en Telegram**
```
/enseñar El costo de producto se calcula así: primero costo manual, luego promedio...
```
- Guarda directamente en `ia_logica_negocio` sin depender de que el LLM escriba etiquetas

**Opción 3: Enseñanza conversacional (actual — mejorada)**
- El flujo actual de `[GUARDAR_NEGOCIO]` sigue funcionando, pero con la detección robusta (JSON o regex tolerante)

#### Ejecución del script

```bash
# Manual — cuando quieras mejorar
python3 scripts/ia_mejora_continua.py --empresa ori_sil_2

# Automático — cron diario a las 2am
0 2 * * * cd /home/osserver/Proyectos_Antigravity/Integraciones_OS && python3 scripts/ia_mejora_continua.py --empresa ori_sil_2 >> logs/mejora.log 2>&1

# Con Claude Code CLI como verificador
python3 scripts/ia_mejora_continua.py --usar-claude --max-correcciones 10
```

**Esfuerzo**: ~4-6 horas para el script completo. Pero se puede hacer incremental: primero el recolector + corrector, luego el detector de patrones.

---

### Fase 5: Mejoras menores de robustez

#### 5.1 — Timeout total para pipeline de consulta
**Problema**: Si el SQL tarda 15s, el retry 15s, y el segundo retry 15s → 45s total sin control.
**Solución**: Wrapper con `signal.alarm()` o thread con timeout al inicio de `consultar()`:
```python
MAX_PIPELINE_SEGUNDOS = 30  # configurable en ia_config
```
**Esfuerzo**: 20 min.

#### 5.2 — Limpiar caché de conversaciones
**Problema**: `_rl_windows` y conversaciones en memoria crecen indefinidamente.
**Solución**: Cron o llamada periódica que limpie conversaciones sin actividad en >24h:
```python
# Cada hora: limpiar ventanas de rate limit de usuarios inactivos
```
**Esfuerzo**: 15 min.

#### 5.3 — Eliminar `_limpiar_sql()` duplicado
**Problema**: Existe en `formateador.py:40` y en `ejecutor_sql.py:17`. Hacen casi lo mismo.
**Solución**: Dejar solo la de `ejecutor_sql.py` (es la que realmente se usa antes de ejecutar). La de `formateador.py` se puede eliminar si `extraer_sql()` ya limpia lo necesario.
**Esfuerzo**: 10 min.

#### 5.4 — Caché para `_cargar_agente()` y `_cargar_tipo()`
**Problema**: Cada consulta hace 3-5 lecturas a BD para cargar agente y tipo. Son datos que cambian 1 vez por semana.
**Solución**: Caché en memoria con TTL de 5 minutos:
```python
_cache_agentes = {}  # slug → {data, ts}
_CACHE_AGENTE_TTL = 300
```
**Esfuerzo**: 15 min.

---

## Orden de ejecución recomendado

| # | Fase | Riesgo | Esfuerzo | Impacto |
|---|---|---|---|---|
| 1 | **2.1 — Activar embeddings** | Cero | 15 min | Alto — SQL con ejemplos relevantes |
| 2 | **2.4 — Incrementar veces_usado** | Cero | 10 min | Medio — datos para auto-optimización |
| 3 | **2.3A — Regex tolerante** | Bajo | 5 min | Medio — no perder aprendizaje |
| 4 | **3 — DDL por tema** | Bajo | 30 min | **Altísimo** — 70K→20K tokens |
| 5 | **5.3 — Eliminar duplicado** | Bajo | 10 min | Bajo — limpieza |
| 6 | **5.4 — Caché agentes/tipos** | Bajo | 15 min | Medio — menos queries BD |
| 7 | **1 — Separar servicio.py** | Medio | 2h | **Altísimo** — mantenibilidad |
| 8 | **2.2 — Tabla ia_feedback** | Bajo | 1h | Alto — base para mejora continua |
| 9 | **2.3B — JSON estructurado** | Medio | 30 min | Alto — aprendizaje robusto |
| 10 | **5.1 — Timeout pipeline** | Bajo | 20 min | Medio — protección |
| 11 | **5.2 — Limpiar caché** | Bajo | 15 min | Bajo — higiene |
| 12 | **4 — Script CLI mejora** | Medio | 4-6h | **Transformacional** |

**Total estimado**: ~10-12 horas de implementación.
**Recomendación**: Hacer los primeros 6 pasos de una (2.5 horas, riesgo bajo, alto impacto). La separación de servicio.py se hace después con calma. El script CLI al final cuando toda la estructura esté limpia.

---

## Visión a futuro — lo que se desbloquea

Con estas mejoras, el sistema queda preparado para:

1. **Auto-mejora**: El script CLI revisa errores → genera correcciones → las verifica → las incorpora. Cada día el sistema es mejor que el anterior.

2. **Enseñanza fácil**: El usuario dice "/enseñar X" o toca "Mala respuesta" → el sistema aprende sin depender de etiquetas exactas del LLM.

3. **Eficiencia**: De 70K a ~20K tokens por consulta = 3.5x menos costo, sin perder capacidad. Las consultas de producción (5 tablas) bajan a ~5K tokens.

4. **Mantenibilidad**: Si mañana hay que agregar un nuevo tipo de aprendizaje (ej: aprender de correcciones manuales), hay un solo archivo donde ir (`aprendizaje.py`), no buscar entre 1,756 líneas.

5. **Escalabilidad**: La tabla `ia_feedback` + el detector de patrones permite que el sistema identifique sus propias debilidades y se auto-corrija. Esto es lo que separa un chatbot de un sistema inteligente.

---

## Qué NO incluye este plan (y por qué)

- **Cambiar de proveedores de LLM**: El sistema ya es multi-proveedor con fallback. No hay que cambiar nada.
- **Agregar más tablas al DDL**: Al contrario — la idea es enviar MENOS tablas, no más.
- **Reescribir el enrutador**: Funciona bien (cuando groq responde). El problema era el rate limit, ya corregido.
- **Dashboard visual**: Es bonito pero no mejora el servicio. Se puede hacer después.

---

## Preguntas para Santi antes de empezar

1. **¿Empezamos por las victorias rápidas (Fases 2.1-2.4 + 3)?** Son los primeros 6 pasos — 2.5 horas, riesgo bajo, impacto alto.
2. **¿O preferís que hagamos la separación de servicio.py primero (Fase 1)?** Es más trabajo pero deja todo limpio para lo demás.
3. **El script CLI (Fase 4): ¿lo querés como cron automático o solo manual?** Recomiendo empezar manual y automatizar cuando veamos que funciona bien.
4. **¿Querés el botón "Mala respuesta" en Telegram?** Es útil pero agrega un elemento visual al bot.
