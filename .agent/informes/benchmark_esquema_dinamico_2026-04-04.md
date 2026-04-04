# Benchmark: Esquema Dinámico + Optimización Ollama
**Fecha**: 2026-04-04
**Hardware**: RTX 3060 12GB, Ryzen 5 5600X, 32GB RAM
**Ollama**: v0.18.3 + Flash Attention + KV Q8_0
**Modelo**: qwen-coder-ctx (qwen2.5-coder:14b Q4_K_M, num_ctx=12288, num_gpu=49)
**Config GPU**: 49/49 capas, 0 RAM offloading, 2 graph splits, 100% VRAM

---

## Resultado: 25/25 exitosos

| Categoría | Tests | OK | Promedio | Rango |
|---|---|---|---|---|
| SQL-comercial | 8 | 8/8 ✅ | **79s** | 71-104s |
| SQL-finanzas | 3 | 3/3 ✅ | **51s** | 43-65s |
| SQL-produccion | 2 | 2/2 ✅ | **41s** | 37-46s |
| SQL-operaciones | 2 | 2/2 ✅ | **40s** | 39-42s |
| SQL-admin | 1 | 1/1 ✅ | **37s** | — |
| SQL-multi | 1 | 1/1 ✅ | **51s** | — |
| Conversación | 5 | 5/5 ✅ | **23s** | 9-31s |
| Redacción | 1 | 1/1 ✅ | **19s** | — |
| Aprendizaje | 1 | 1/1 ✅ | **17s** | — |
| Búsqueda web | 1 | 1/1 ✅ | **17s** | — |
| **TOTAL** | **25** | **25/25** | **SQL: 61s / No-SQL: 21s** | |

---

## Detalle — SQL (17 preguntas)

| # | Pregunta | Tema detectado | SQL | Tiempo |
|---|---|---|---|---|
| 1 | ¿Cuánto vendimos este mes? | comercial | ✅ | 77s |
| 2 | ¿Cuánto vendimos en febrero 2026? | comercial | ✅ | 80s |
| 3 | Top 5 productos más vendidos en unidades este año | comercial | ✅ | 84s |
| 4 | ¿Cuántas remisiones pendientes de facturar hay? | comercial | ✅ | 80s |
| 5 | ¿Cuánto valor hay en consignación activa? | comercial | ✅ | 80s |
| 6 | Ventas por canal este mes | comercial | ✅ | 104s |
| 7 | Top 3 clientes por valor facturado este mes | comercial | ✅ | 71s |
| 8 | ¿Cuánto hay en cartera vencida? | finanzas | ✅ | 46s |
| 9 | ¿Cuánto debemos a proveedores? | finanzas | ✅ | 65s |
| 10 | ¿Cuántas facturas de compra hay en marzo 2026? | finanzas | ✅ | 43s |
| 11 | ¿Cuántas notas crédito se hicieron en marzo 2026? | comercial | ✅ | 54s |
| 12 | ¿Cuántas órdenes de producción vigentes hay? | produccion | ✅ | 37s |
| 13 | ¿Cuánto costó la producción este año en materiales? | produccion | ✅ | 46s |
| 14 | ¿Cuánto stock hay de productos terminados? | produccion | ✅ | 42s |
| 15 | ¿Cuántos traslados de inventario se hicieron en marzo? | operaciones | ✅ | 39s |
| 16 | ¿Cuántos empleados activos tenemos? | administracion | ✅ | 37s |
| 17 | Dame las compras de materia prima de este año | finanzas | ✅ | 51s |

## Detalle — No-SQL (8 preguntas)

| # | Pregunta | Tipo | Tema | Tiempo |
|---|---|---|---|---|
| 18 | Hola, ¿cómo estás? | conversacion | general | 9s |
| 19 | ¿Cómo funciona la consignación? | conversacion | general | 19s |
| 20 | Explícame las tarifas de precios | conversacion | administracion | 30s |
| 21 | ¿Qué canales de marketing maneja la empresa? | conversacion | marketing | 26s |
| 22 | ¿Cómo se clasifican los clientes? | conversacion | marketing | 31s |
| 23 | Escríbeme un correo de cobro a un cliente moroso | redaccion | general | 19s |
| 24 | Aprende: plazo de pago para negocios amigos tipo A es 45 días | aprendizaje | estrategia | 17s |
| 25 | Busca en internet el precio del cacao en Colombia | busqueda_web | general | 17s |

---

## Comparación histórica

| Benchmark | SQL correctos | Promedio SQL | Config |
|---|---|---|---|
| 29 mar (original) | 15/15 | **14s** | num_ctx=28672(?), prompt 44K tokens, condiciones ideales |
| 04 abr (antes optimizar) | 15/15 | **200s** | num_ctx=28672, 40/49 GPU, 6.3GB RAM |
| 04 abr (prompt comprimido) | 15/15 | **57s** | num_ctx=14500, 49/49 GPU, Flash+Q8 |
| **04 abr (esquema dinámico)** | **17/17** | **61s** | num_ctx=12288, 49/49 GPU, Flash+Q8, dinámico |

Mejora total: 200s → 61s SQL promedio (**3.3x más rápido**). No-SQL: 21s promedio.

La diferencia con el benchmark original (14s) se atribuye a prompt caching de Ollama: en el benchmark, el mismo system prompt se reutilizaba entre llamadas consecutivas, evitando re-evaluación. Con esquema dinámico, cada tema genera un prompt diferente → sin cache.

---

## Esquema dinámico — impacto por tema

| Tema | Tablas | Tokens esquema | Prompt total (est.) | Velocidad |
|---|---|---|---|---|
| administracion | 9 | ~583 | ~8,000 | **37s** |
| produccion | 8 | ~767 | ~8,200 | **41s** |
| operaciones | 6 | ~764 | ~8,200 | **40s** |
| finanzas | 14 | ~1,919 | ~9,500 | **51s** |
| comercial | 24 | ~3,457 | ~10,800 | **79s** |

Temas más livianos (admin, producción, operaciones) son **2x más rápidos** que comercial.

---

## Configuración activa

### Modelo Ollama
```
FROM qwen2.5-coder:14b
PARAMETER num_ctx 12288
PARAMETER num_gpu 49
```

### Ollama service (/etc/systemd/system/ollama.service)
```
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

### BD — ia_service_os
- `ia_esquema_tablas`: 52 tablas con descripciones (1 fila por tabla)
- `ia_temas`: 8 temas con `schema_tablas` (52/52 cubiertas)
- `ia_tipos_consulta.analisis_datos`: system_prompt sin `<esquema>` (se inyecta dinámicamente)
- Router (`enrutamiento`): devuelve `temas:[]` (array multi-tema)

### servicio.py
- `_enrutar()` retorna `temas: list[str]` (multi-tema)
- `_obtener_esquema_por_temas()` combina tablas de los temas sin duplicados
- CAPA 3 inyecta `<esquema>` filtrado dinámicamente
- `_asegurar_qwen_coder_ctx()` recrea el modelo si se pierde

### Documentación
- `.agent/docs/CONFIG_QWEN_CTX.md` — configuración completa y recuperación
- `.agent/planes/plan_esquema_dinamico.md` — plan original (completado)
