---
name: desarrollo-python
description: >
  Reglas obligatorias de desarrollo Python. Triggers: python, script, módulo, refactor, archivo python, .py, servicio.py, función, import.
---

# Skill: Desarrollo de Scripts Python — Reglas de Mantenibilidad

> **Por qué existe este documento:** En marzo 2026, `servicio.py` llegó a 1,756 líneas con 5 responsabilidades mezcladas (seguridad, alertas, aprendizaje, depurador, orquestación). Fue necesario un refactor mayor para separarlo en 4 módulos. Este manual existe para que eso **no vuelva a pasar**.

---

## Regla #1 — Límites duros por archivo

| Métrica | Límite | Acción si se supera |
|---|---|---|
| Líneas por archivo | **400** | Obligatorio dividir en módulos |
| Líneas por función | **80** | Extraer subfunciones |
| Funciones por archivo | **15** | El archivo tiene más de 1 responsabilidad → separar |
| Imports internos (del mismo paquete) | **5 módulos** | Señal de que el archivo es un "hub" → reestructurar |

**Excepción única:** El orquestador (`servicio.py`) puede llegar a **1,200 líneas** porque coordina todos los módulos. Pero si supera 1,200 → refactor obligatorio.

---

## Regla #2 — Un archivo, una responsabilidad

Cada `.py` debe tener UN propósito claro que se pueda describir en una línea:

```
✅ seguridad.py      → "Rate limiting, circuit breaker, verificación de límites"
✅ alertas.py        → "Notificaciones Telegram de eventos del sistema"
✅ aprendizaje.py    → "Guardar reglas, ejemplos SQL, depurador, resúmenes"
✅ utilidades_sql.py → "Consultas auxiliares: columnas reales, fecha máxima, cobertura"
✅ ejecutor_sql.py   → "Ejecución segura de SQL (validación AST + read-only)"

❌ servicio_v1.py    → "Orquestación + seguridad + alertas + aprendizaje + utilidades"
```

**Test rápido:** Si necesitás usar la palabra "y" para describir qué hace el archivo, probablemente tiene más de una responsabilidad.

---

## Regla #3 — Estructura estándar de un módulo Python

Todo módulo nuevo debe seguir esta estructura:

```python
"""
modulo_x.py — Descripción en una línea.

Responsabilidad: qué hace este módulo y nada más.
Usado por: quién lo importa (servicio.py, bot.py, etc.)
"""

import stdlib          # stdlib primero
import third_party     # terceros después
from .config import get_local_conn  # internos al final

# ── Constantes ──────────────────────────────────
MAX_ALGO = 100
_CACHE_TTL = 300

# ── Funciones públicas ──────────────────────────
def funcion_principal():
    """Docstring obligatorio en funciones públicas."""
    pass

def otra_publica():
    pass

# ── Funciones internas ──────────────────────────
def _auxiliar_privada():
    pass
```

**Convenciones obligatorias:**
- Funciones públicas: `snake_case` sin prefijo `_`
- Funciones internas: prefijo `_` (solo las usa el mismo archivo)
- Si una función "privada" necesita ser importada por otro módulo → **quitarle el `_`**, es pública
- Constantes: `MAYUSCULAS_CON_GUION`
- Constantes internas: `_PREFIJO_MAYUSCULAS`

---

## Regla #4 — Cuándo crear un archivo nuevo vs agregar a uno existente

### Crear archivo nuevo cuando:
1. La funcionalidad tiene una responsabilidad distinta a todo lo existente
2. El archivo destino superaría 400 líneas al agregar el código
3. El código nuevo tiene dependencias (imports) que el archivo actual no necesita
4. Vas a agregar más de 3 funciones relacionadas entre sí

### Agregar al archivo existente cuando:
1. La función es una utilidad directa de lo que ya hace el archivo
2. Son 1-2 funciones pequeñas (<30 líneas cada una)
3. No introduce imports nuevos pesados

### NUNCA:
- Crear un archivo para una sola función de <20 líneas → ponerla donde corresponda
- Duplicar funciones en 2 archivos → importar desde una fuente única
- Crear `utils.py` genérico → cada utilidad va en el módulo de su dominio

---

## Regla #5 — Prevención de código duplicado

**Antes de escribir una función, verificar si ya existe algo similar:**

```bash
# Buscar en todo el proyecto
grep -rn "def nombre_similar" scripts/
```

**Si existe algo parecido:**
1. ¿Hace exactamente lo mismo? → Importar, no duplicar
2. ¿Hace algo similar pero no igual? → Generalizar la existente con un parámetro
3. ¿Son 2 variantes irreconciliables? → OK crear nueva, pero documentar por qué

**Caso real que motivó esta regla:** `limpiar_sql()` existía en `formateador.py` Y en `ejecutor_sql.py` haciendo lo mismo. Se unificó en `ejecutor_sql.py` y el otro archivo la importa.

---

## Regla #6 — Caché y estado en memoria

Todo caché in-memory debe seguir este patrón:

```python
_cache_datos = {}       # {clave: {"data": ..., "ts": timestamp}}
_CACHE_TTL = 300        # segundos

def obtener_dato(clave):
    ahora = time.time()
    if clave in _cache_datos and (ahora - _cache_datos[clave]["ts"]) < _CACHE_TTL:
        return _cache_datos[clave]["data"]

    # Ir a BD/API
    dato = _consultar_fuente(clave)
    _cache_datos[clave] = {"data": dato, "ts": ahora}
    return dato
```

**Reglas de caché:**
- TTL obligatorio — nada se cachea indefinidamente
- TTL por defecto: 300s (5 min) para config, 3600s (1h) para schemas
- Incluir función de limpieza si el dict puede crecer sin límite (ej: rate limiting por usuario)
- Documentar el TTL como constante con nombre descriptivo

---

## Regla #7 — Manejo de conexiones a BD

```python
# ✅ CORRECTO — conexión efímera, se cierra siempre
def leer_algo():
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            return cur.fetchall()
    finally:
        conn.close()

# ✅ TAMBIÉN CORRECTO — con context manager
def leer_algo():
    conn = get_local_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT ...")
        resultado = cur.fetchall()
    conn.commit()  # solo si hubo INSERT/UPDATE
    conn.close()
    return resultado

# ❌ MAL — conexión global que nunca se cierra
_conn = get_local_conn()  # al importar el módulo
def leer_algo():
    with _conn.cursor() as cur:  # reutiliza conexión → timeout, stale
        ...
```

**Regla:** Cada función abre y cierra su propia conexión. Nunca reutilizar conexiones entre funciones.

---

## Regla #8 — Manejo de errores

```python
# ✅ CORRECTO — captura específica, log útil
try:
    resultado = ejecutar_sql(sql)
except pymysql.err.OperationalError as e:
    logger.error(f"Error SQL en {tabla}: {e}")
    return {"ok": False, "error": str(e)}

# ❌ MAL — except genérico que traga todo
try:
    resultado = ejecutar_sql(sql)
except Exception:
    pass  # silencia errores → bugs invisibles

# ❌ MAL — except demasiado amplio
try:
    # 50 líneas de código
except Exception as e:
    return {"error": str(e)}  # no sabés qué falló
```

**Reglas:**
- `except Exception: pass` solo se permite en funciones de logging/notificación (no críticas)
- Try/except debe envolver la operación específica, no bloques de 50+ líneas
- Siempre loguear el error antes de tragarlo

---

## Regla #9 — Scripts independientes (fuera de ia_service)

Scripts como `ia_mejora_continua.py`, `orquestador.py`, `sync_hostinger.py`:

1. **Deben ser ejecutables directamente:** `python3 scripts/nombre.py`
2. **Incluir bloque `if __name__ == '__main__':`** con argparse si aceptan parámetros
3. **Documentar en el header:**
   ```python
   """
   ia_mejora_continua.py — Procesa feedback acumulado y mejora el sistema.

   Uso: python3 scripts/ia_mejora_continua.py --max 10
   Cron: 0 */6 * * * (cada 6 horas)
   Logs: logs/mejora_continua.log
   """
   ```
4. **Límite: 300 líneas.** Si supera → extraer lógica a un módulo e importar.

---

## Regla #10 — Checklist antes de dar código por terminado

Antes de hacer commit de cualquier cambio Python:

- [ ] ¿Algún archivo supera 400 líneas? → Dividir
- [ ] ¿Alguna función supera 80 líneas? → Extraer subfunciones
- [ ] ¿Dupliqué código que ya existía? → `grep -rn "def nombre" scripts/`
- [ ] ¿Las conexiones a BD se cierran? → `conn.close()` en cada función
- [ ] ¿Los cachés tienen TTL? → No cachear indefinidamente
- [ ] ¿El except es específico? → No `except Exception: pass` salvo logging
- [ ] ¿El import es circular? → Si `A importa B` y `B importa A` → reestructurar
- [ ] ¿Actualicé `CATALOGO_SCRIPTS.md` si creé/modifiqué un script?

---

## Inventario actual (2026-03-23) — Referencia de tamaños

### ia_service/ (el módulo principal)

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| servicio.py | 1,028 | Orquestador (EXCEPCIÓN: límite 1,200) |
| aprendizaje.py | 399 | Aprendizaje, reglas, ejemplos, depurador |
| rag.py | 248 | Indexación y búsqueda de documentos |
| seguridad.py | 236 | Rate limit, circuit breaker, niveles |
| extractor.py | 228 | Extracción de texto (PDF, DOCX, XLSX, CSV, imagen) |
| conector.py | 218 | Conexiones a BDs externas + schema sync |
| contexto.py | 199 | Conversaciones, resumen, caché SQL |
| ejecutor_sql.py | 182 | Ejecución segura SQL (AST + read-only) |
| utilidades_sql.py | 174 | Columnas reales, fecha máxima, cobertura |
| embeddings.py | 166 | Vectores gemini-embedding-001 + búsqueda cosine |
| esquema.py | 128 | DDL para LLM con caché por tema |
| formateador.py | 103 | Parseo de respuestas, extracción SQL/JSON |
| alertas.py | ~85 | Notificaciones Telegram |
| config.py | 53 | Credenciales .env, conexiones BD |
| proveedores/ | 496 | 4 archivos: google, openai_compat, anthropic, tavily |

### telegram_bot/

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| bot.py | 622 | Handlers Telegram (vigilar — cerca del límite) |
| tabla.py | 145 | Formato de tablas para Telegram |
| db.py | 132 | Sesiones y autenticación |
| teclado.py | 78 | Keyboards de Telegram |
| whisper.py | 44 | Transcripción de audio |
| api_ia.py | 41 | Cliente HTTP a ia_service |

### Scripts independientes

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| ia_mejora_continua.py | ~250 | Mejora continua (cron cada 6h) |
| orquestador.py | ~200 | Pipeline Effi (cron cada 1h) |

---

## Señales de alarma — Cuándo intervenir

| Señal | Acción |
|---|---|
| Un archivo pasa de 400 líneas | Parar y separar ANTES de seguir agregando código |
| Una función pasa de 80 líneas | Extraer la lógica interna a subfunciones |
| `grep` encuentra la misma función en 2 archivos | Unificar inmediatamente |
| Un import circular aparece | Mover la función compartida a un tercer módulo |
| `bot.py` supera 700 líneas | Extraer handlers a módulos: `handlers_consulta.py`, `handlers_config.py` |
| `aprendizaje.py` supera 450 líneas | Separar `depurador.py` del resto |
| `servicio.py` supera 1,200 líneas | Extraer `_llamar_agente()` y proveedores a módulo aparte |
