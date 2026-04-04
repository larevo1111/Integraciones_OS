# Plan: Esquema dinámico por temas

**Creado**: 2026-04-04
**Estado**: Pendiente
**Prioridad**: Alta — impacto directo en latencia Ollama

---

## Objetivo

Inyectar solo las tablas relevantes al tema de la consulta en vez de las 52 tablas completas. El router ya detecta el tema; falta que el esquema se filtre dinámicamente.

## Impacto esperado

| Escenario | Tokens esquema | Total por llamada | ¿Cabe en 8192? |
|---|---|---|---|
| Hoy (52 tablas siempre) | ~6,100 | ~14,200 | No → offloading |
| Comercial (21 tablas) | ~3,300 | ~10,400 | No, pero cerca |
| Producción (8 tablas) | ~770 | ~7,900 | **Sí** |
| Finanzas (14 tablas) | ~1,900 | ~9,100 | No, pero cerca |
| Administración (9 tablas) | ~660 | ~7,800 | **Sí** |

Con la mayoría de temas el prompt bajaría a ~8-10K tokens. Si además se comprime el `<reglas_sql>` (3K tokens) filtrando solo las reglas del tema, muchos cabrían en 8192 = **0 offloading, 100% VRAM, ~35 tok/s**.

Para los que no caben (comercial es el más pesado), igual se reduce de 14K a 10K tokens = menos offloading = más rápido.

## Infraestructura existente

- `ia_temas.schema_tablas` — ya configurado para 8 temas con listas de tablas
- `<esquema>` en system_prompt — contiene las 52 tablas con descripciones unificadas
- Router (`_enrutar`) — ya devuelve 1 tema por consulta
- `servicio.py` — ya carga `tema_cfg` con `schema_tablas`

## Lo que falta implementar

### Paso 1: Corregir cobertura de tablas en `ia_temas`

5 tablas no están en ningún tema:
- `zeffi_cotizaciones_ventas_detalle` → agregar a `comercial`
- `zeffi_devoluciones_venta_detalle` → agregar a `comercial`
- `zeffi_notas_credito_venta_detalle` → agregar a `comercial` y `finanzas`
- `zeffi_ordenes_compra_detalle` → agregar a `finanzas`
- `zeffi_remisiones_compra_detalle` → agregar a `finanzas`

### Paso 2: Router multi-tema

Cambiar el prompt del router para que devuelva array de temas:

```json
{"tipo":"analisis_datos","temas":["comercial","finanzas"],"requiere_sql":true}
```

Reglas:
- Si la pregunta toca solo un área → 1 tema: `"temas":["comercial"]`
- Si cruza áreas (ej: "ventas vs compras") → múltiples: `"temas":["comercial","finanzas"]`
- Máximo 3 temas por consulta (para no anular el beneficio)
- Si no puede determinar → `"temas":["general"]` (fallback con las tablas clave)

Actualizar el prompt de `ia_tipos_consulta` WHERE `slug='enrutamiento'`.

### Paso 3: Separar `<esquema>` del system_prompt estático

Actualmente el `<esquema>` completo está dentro de `ia_tipos_consulta.system_prompt`. Necesitamos:

1. **Extraer las descripciones de tablas** a `ia_temas.schema_descripcion` (nuevo campo MEDIUMTEXT) o a una tabla nueva `ia_esquema_tablas` (nombre_tabla, descripcion)
2. **El system_prompt base** queda sin `<esquema>` — solo rol + precision + reglas_sql + ejemplos
3. **En runtime**, `servicio.py` combina: system_prompt base + esquema filtrado por temas

**Opción recomendada**: tabla `ia_esquema_tablas` con una fila por tabla. Más flexible que meter todo en `ia_temas.schema_descripcion`.

```sql
CREATE TABLE ia_esquema_tablas (
    nombre_tabla VARCHAR(100) PRIMARY KEY,
    descripcion TEXT NOT NULL,        -- la descripción del <esquema> para esa tabla
    empresa VARCHAR(50) DEFAULT 'ori_sil_2'
);
```

### Paso 4: Función de filtrado en `servicio.py`

Nueva función `_obtener_esquema_por_temas(temas: list, empresa: str) -> str`:
1. Lee los `schema_tablas` de cada tema en la lista
2. Combina (union) las tablas sin duplicados
3. Busca la descripción de cada tabla en `ia_esquema_tablas`
4. Arma la sección `<esquema>` solo con esas tablas
5. La inyecta en el system_prompt

```python
# En servicio.py, reemplazar CAPA 3:
if tipo == 'analisis_datos':
    esquema_filtrado = _obtener_esquema_por_temas(temas_detectados, empresa)
    system_prompt += f'\n\n<esquema>\n{esquema_filtrado}\n</esquema>'
```

### Paso 5: Adaptar `_enrutar()` para multi-tema

En `servicio.py`, modificar `_enrutar()`:
- Parsear `temas` (array) en vez de `tema` (string)
- Mantener backward compatibility: si devuelve `tema` (string), convertir a `[tema]`
- Devolver la lista de temas al flujo principal

### Paso 6: Recrear modelo `qwen-coder-ctx` con `num_ctx` ajustado

Si el prompt promedio baja a ~8-10K tokens:
- `num_ctx=10240` en vez de 14500
- Menos KV cache → más VRAM para capas del modelo
- Potencialmente 0 offloading para la mayoría de consultas

### Paso 7: Tests

1. Verificar que las 52 tablas están cubiertas por al menos 1 tema
2. Correr las 15 preguntas del benchmark con esquema dinámico
3. Medir tokens reales por tema
4. Medir latencia y comparar con los 57s actuales
5. Verificar que consultas multi-tema (ej: "compras de materia prima" = producción + finanzas) funcionan

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `ia_service_os` BD | Crear tabla `ia_esquema_tablas`, poblarla con las 52 descripciones |
| `ia_service_os` BD | Actualizar `ia_temas.schema_tablas` (5 tablas faltantes) |
| `ia_service_os` BD | Actualizar prompt de `enrutamiento` (multi-tema) |
| `ia_service_os` BD | Quitar `<esquema>` del system_prompt de `analisis_datos` |
| `scripts/ia_service/servicio.py` | `_obtener_esquema_por_temas()`, adaptar `_enrutar()`, inyección dinámica |
| Modelo `qwen-coder-ctx` | Ajustar `num_ctx` según tokens resultantes |
| `.agent/docs/CONFIG_QWEN_CTX.md` | Actualizar con nueva config |

## Riesgos

1. **Router clasifica mal el tema** → falta una tabla → SQL falla → se activa retry con más contexto
   - Mitigación: el tema `general` tiene las tablas más usadas como fallback
   - Mitigación: si SQL falla, el retry puede incluir el esquema completo

2. **Consultas que cruzan muchos temas** → se combinan 3+ temas → prompt igual de grande
   - Mitigación: límite de 3 temas. Si necesita más, usar esquema completo.

3. **Tabla faltante en un tema** → el agente no sabe que existe
   - Mitigación: paso 1 verifica cobertura completa. Mantener actualizado.

## Tareas para Subagentes

- Poblar `ia_esquema_tablas` con las 52 descripciones (extraer del `<esquema>` actual)
- Crear los SQL de migración (CREATE TABLE, INSERT)
- Tests unitarios de filtrado por tema

## Tareas para Antigravity

- N/A (cambio interno, no requiere revisión visual)

## Estimación de esfuerzo

1 sesión interactiva con Santi para implementar y validar.
