# Configuración Qwen CTX — Ollama Local para IA Service

**Creado**: 2026-04-04
**Modelo**: qwen-coder-ctx (basado en qwen2.5-coder:14b Q4_K_M)
**Hardware**: RTX 3060 12GB, Ryzen 5 5600X, 32GB RAM
**Ollama**: v0.18.3

---

## Configuración actual (optimizada)

### Modelo Ollama

```bash
# Modelfile
FROM qwen2.5-coder:14b
PARAMETER num_ctx 14500
PARAMETER num_gpu 49
```

**Crear/recrear el modelo:**
```bash
cat > /tmp/Modelfile-qwen-ctx << 'EOF'
FROM qwen2.5-coder:14b
PARAMETER num_ctx 14500
PARAMETER num_gpu 49
EOF
ollama create qwen-coder-ctx -f /tmp/Modelfile-qwen-ctx
```

### Servicio Ollama (systemd)

Archivo: `/etc/systemd/system/ollama.service`

Variables de entorno requeridas:
```
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
```

Aplicar cambios:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama.service
```

### BD — ia_agentes

```sql
-- Verificar
SELECT slug, modelo_id, endpoint_url FROM ia_agentes WHERE slug='ollama-qwen-coder';
-- Debe ser:
-- modelo_id = qwen-coder-ctx
-- endpoint_url = http://localhost:11434/v1
```

---

## Por qué cada parámetro

| Parámetro | Valor | Razón |
|---|---|---|
| `num_ctx=14500` | Tamaño ventana de contexto | El prompt completo (esquema + lógica + pregunta) usa ~14,244 tokens. 14500 da margen justo sin desperdiciar VRAM en KV cache vacío. |
| `num_gpu=49` | Forzar TODAS las capas a GPU | Sin esto, Ollama calcula que no caben y deja 1-9 capas en CPU. Cada capa en CPU genera graph splits que matan la velocidad de generación (de 22 tok/s a 5 tok/s). Con 49/49 en GPU: 2 graph splits, 22.7 tok/s. |
| `OLLAMA_FLASH_ATTENTION=1` | Algoritmo de atención optimizado | Reduce uso de VRAM para compute buffers. Mismo resultado, menos memoria. |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | KV cache comprimido a 8 bits | Reduce KV cache de 3 GB (F16) a 1.6 GB (Q8). Pérdida de calidad imperceptible. Libera ~1.4 GB de VRAM que permiten meter más capas en GPU. |

### Balance de VRAM (12,288 MiB total)

```
Pesos modelo (49 capas):    8,148 MiB
KV cache Q8 (14500 ctx):    1,453 MiB
Compute buffer:               317 MiB
─────────────────────────────────────
Ollama total:               ~9,918 MiB
Desktop (Xorg+Cinnamon):      ~440 MiB
Otros (Code, etc):             ~130 MiB
─────────────────────────────────────
TOTAL GPU:                 ~10,500 MiB de 12,288 MiB
Libre:                      ~1,788 MiB
Graph splits:                    2
RAM offloading:                  0
```

---

## System prompt (sección `<esquema>` unificada)

El system prompt de `analisis_datos` fue comprimido el 2026-04-04.

**Antes**: 3 fuentes separadas = ~87K chars (~25K tokens)
- `<tablas_disponibles>` (13.5K chars) — descripción de cada tabla
- `<diccionario_campos>` (40.7K chars) — descripción de cada campo
- DDL de `esquema.py` (32.7K chars) — CREATE TABLE inyectado en runtime

**Ahora**: 1 fuente unificada = ~42K chars (~12K tokens)
- `<esquema>` — tabla + descripción + campos con significado, todo junto
- DDL de esquema.py ya NO se inyecta (eliminado en servicio.py)
- 52 tablas documentadas, todos los campos, todos los gotchas preservados

**Tokens reales por llamada LLM** (medido con tokenizer Qwen):
```
System prompt BD (<esquema> + reglas + ejemplos):  ~12,000 tokens
Lógica de negocio (ia_logica_negocio):              ~1,200 tokens
Fecha + nombre usuario:                                ~20 tokens
RAG (si aplica):                                    0-500 tokens
User message + ejemplos dinámicos:                   ~240 tokens
────────────────────────────────────────────────────────────────
TOTAL por llamada:                                 ~14,244 tokens
num_ctx:                                            14,500 tokens
Margen libre:                                          256 tokens
```

---

## Verificación de la configuración

Ejecutar para verificar que todo está bien:

```bash
# 1. Verificar modelo
ollama show qwen-coder-ctx --modelfile | grep PARAMETER

# 2. Verificar servicio
grep 'OLLAMA_' /etc/systemd/system/ollama.service

# 3. Cargar modelo y verificar GPU allocation
curl -s http://localhost:11434/api/generate -d '{"model":"qwen-coder-ctx","prompt":"test","keep_alive":"5m"}' > /dev/null
sleep 3
curl -s http://localhost:11434/api/ps | python3 -c "
import sys,json
d=json.load(sys.stdin)['models'][0]
t=d['size']; v=d['size_vram']; r=t-v
print(f'Total: {t/1e9:.2f} GB | VRAM: {v/1e9:.2f} GB | RAM: {r/1e9:.2f} GB | ctx: {d[\"context_length\"]}')
print(f'Estado: {\"✅ OK\" if r < 100000000 else \"❌ HAY OFFLOADING\"}')
"

# 4. Verificar layers en GPU
journalctl -u ollama.service --no-pager -n 30 | grep 'offloaded'
# Debe decir: offloaded 49/49 layers to GPU

# 5. Verificar graph splits
journalctl -u ollama.service --no-pager -n 30 | grep 'graph splits'
# Debe decir: graph splits = 2
```

---

## Benchmark — resultados 2026-04-04

| # | Pregunta | SQL | Tiempo |
|---|---|---|---|
| 1 | ¿Cuánto vendimos este mes? | ✅ | 55s |
| 2 | ¿Cuánto vendimos en febrero 2026? | ✅ | 56s |
| 3 | Top 5 productos más vendidos en unidades este año | ✅ | 61s |
| 4 | ¿Cuánto hay en cartera vencida? | ✅ | 55s |
| 5 | ¿Cuántas remisiones pendientes de facturar hay? | ✅ | 57s |
| 6 | ¿Cuál fue el canal de venta más fuerte en enero 2026? | ✅ | 57s |
| 7 | ¿Cuánto stock hay de productos terminados? | ✅ | 57s |
| 8 | ¿Cuántas órdenes de producción vigentes hay? | ✅ | 54s |
| 9 | ¿Cuánto valor hay en consignación activa? | ✅ | 55s |
| 10 | Ventas por canal este mes | ✅ | 63s |
| 11 | ¿Cuántos clientes nuevos compraron este año? | ✅ | 56s |
| 12 | Top 3 clientes por valor facturado este mes | ✅ | 62s |
| 13 | ¿Cuál es el margen promedio de las ventas de febrero? | ✅ | 55s |
| 14 | Dame las compras de materia prima de este año | ✅ | 59s |
| 15 | ¿Cuántas notas crédito se hicieron en marzo 2026? | ✅ | 55s |

**Resultado: 15/15 SQL correctos, promedio 57s por consulta.**

Comparación:
| | Benchmark 29 mar | 04 abril (optimizado) |
|---|---|---|
| SQL correctos | 15/15 | 15/15 |
| Latencia promedio | 14s | 57s |
| Generación tok/s | ~35 (estimado) | 22.7 |
| Prompt eval | ~3s (estimado) | 17s |
| Capas GPU | ? | 49/49 |

La diferencia de velocidad (~4x) se concentra en prompt eval (17s por llamada). No se logró reproducir la velocidad del benchmark original — la causa exacta no fue identificada.

---

## Hallazgos de la investigación (2026-04-04)

### 1. El endpoint /v1 ignora `options.num_ctx`
El código tenía `payload['options'] = {'num_ctx': 24576}` en `openai_compat.py` para llamadas Ollama. **No hacía nada** — el endpoint `/v1/chat/completions` de Ollama ignora ese campo. El num_ctx siempre viene del Modelfile del modelo. Se eliminó esa línea.

### 2. Offloading a RAM mata la velocidad
Con incluso 1 capa del modelo en CPU, la velocidad de generación cae de ~22 tok/s a ~5 tok/s. Con 9 capas en CPU, cae a 2.6 tok/s. Los graph splits (que miden cuántas veces el cómputo salta entre GPU y CPU) son el indicador: 2 splits = rápido, 116 splits = lento.

### 3. KV cache Q8 vs F16
La diferencia de calidad es imperceptible (15/15 SQL correctos en ambos). Pero Q8 ahorra ~1.4 GB de VRAM, que es la diferencia entre meter 40 vs 49 capas en GPU.

### 4. El system prompt estaba duplicando información
Tres fuentes describían las mismas tablas: `<tablas_disponibles>` (qué es cada tabla), `<diccionario_campos>` (qué es cada campo), y el DDL (CREATE TABLE con tipos). Fusionar en `<esquema>` eliminó ~45K chars de redundancia sin perder información.

### 5. El modelo puede recrearse en cualquier momento
Si por cualquier razón el modelo `qwen-coder-ctx` se pierde o se corrompe (ialocal, otro proceso, actualización de Ollama), recrearlo con el Modelfile de esta doc. El warmup automático en `servicio.py` (_warmup_ollama) verifica que el modelo correcto esté cargado.

---

## Qué hacer si se desconfigura

### Síntoma: consultas tardan >100s
1. Verificar: `curl -s http://localhost:11434/api/ps | python3 -m json.tool`
2. Si `size_vram < size` → hay offloading → recrear modelo con los parámetros de arriba
3. Si modelo no es `qwen-coder-ctx` → el modelo_id en ia_agentes fue cambiado
4. Si graph splits > 10 → faltan `OLLAMA_FLASH_ATTENTION` o `OLLAMA_KV_CACHE_TYPE`

### Síntoma: SQL incorrectos o truncados
1. Verificar tokens: el prompt debe caber en 14500 tokens
2. Si se agregaron reglas a `ia_logica_negocio` o creció el system prompt → medir tokens reales
3. Si los tokens exceden 14500 → comprimir prompt o subir num_ctx (pero cuidado con VRAM)

### Script de recuperación completo
```bash
# Recrear modelo
cat > /tmp/Modelfile-qwen-ctx << 'EOF'
FROM qwen2.5-coder:14b
PARAMETER num_ctx 14500
PARAMETER num_gpu 49
EOF
ollama create qwen-coder-ctx -f /tmp/Modelfile-qwen-ctx

# Asegurar env vars en Ollama
grep -q 'OLLAMA_FLASH_ATTENTION' /etc/systemd/system/ollama.service || \
  sudo sed -i '/\[Service\]/a Environment="OLLAMA_FLASH_ATTENTION=1"\nEnvironment="OLLAMA_KV_CACHE_TYPE=q8_0"' /etc/systemd/system/ollama.service

sudo systemctl daemon-reload
sudo systemctl restart ollama.service

# Verificar
sleep 5
curl -s http://localhost:11434/api/generate -d '{"model":"qwen-coder-ctx","prompt":"test","keep_alive":"5m"}' > /dev/null
sleep 3
journalctl -u ollama.service --no-pager -n 5 | grep 'offloaded'
```
