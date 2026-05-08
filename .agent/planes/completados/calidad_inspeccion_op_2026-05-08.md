# Plan: Sección Calidad e Inspección por OP

**Inicio**: 2026-05-08
**Estado**: en progreso
**Módulo**: Sistema Gestión OS (`gestion.oscomunidad.com`)
**Doc base**: `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md`

---

## Objetivo

Digitalizar la bitácora de calidad en papel ("BITÁCORA DE CALIDAD - PRODUCTO TERMINADO/PROCESADO") como una sección dentro del panel de cada OP. Combina:
- **A. Inspección visual genérica** (4 booleanos para todos los productos)
- **B. Mediciones de Puntos Críticos** (dinámicos según receta, leídos de `prod_recetas_puntos_criticos`)
- Conteo de defectos (críticos/mayores/menores)
- Resultado final (Aprobado / Rechazado / Liberado con observación)
- Auto-firma del inspector logueado

**Restricciones de alcance** (acordadas con Santi):
- ✅ Calidad vive 100% en `os_gestion`. **NUNCA toca Effi** (no nuevos estados, no workflows nuevos).
- ✅ El resultado es **metadato informativo**. Soft-block al validar si rechazado (warning + confirmación), no bloqueo duro.
- ❌ NO workflow de no conformidad / reproceso / descarte. Eso es módulo ERP futuro.
- ❌ NO firma con canvas — firma = email del usuario logueado + timestamp.

---

## Pasos

### Paso 1 — BD (en `os_gestion` VPS)

Crear 2 tablas nuevas:

```sql
g_op_inspeccion_calidad (
  id, empresa, id_op,
  tamano_lote_unidades INT,
  tamano_muestra INT,
  visual_normal      ENUM('si','no','na'),
  tapado_sellado     ENUM('si','no','na'),
  etiqueta_normal    ENUM('si','no','na'),
  sabor_olor_normal  ENUM('si','no','na'),
  defectos_criticos  INT DEFAULT 0,
  defectos_mayores   INT DEFAULT 0,
  defectos_menores   INT DEFAULT 0,
  resultado ENUM('aprobado','rechazado','liberado_observacion'),
  observacion TEXT,
  inspector_email,
  inspeccionado_en DATETIME,
  KEY (empresa, id_op),
  KEY (resultado, inspeccionado_en)
)

g_op_pc_registro (
  id, inspeccion_id FK,
  pc_receta_id INT,
  parametro VARCHAR(100),                  -- snapshot
  tipo ENUM('numerico','booleano','texto','seleccion'),
  unidad VARCHAR(20),                      -- snapshot
  rango_min DECIMAL(12,4),                 -- snapshot
  rango_max DECIMAL(12,4),                 -- snapshot
  valor_numerico DECIMAL(12,4),
  valor_booleano TINYINT,
  valor_texto TEXT,
  dentro_rango TINYINT,                    -- calculado al insert
  observacion TEXT
)
```

**Test**: `DESCRIBE g_op_inspeccion_calidad; DESCRIBE g_op_pc_registro;`

---

### Paso 2 — Backend (sistema_gestion/api/server.js)

3 endpoints nuevos:

#### `GET /api/gestion/op/:id_op/calidad/sugerencia`

Devuelve los PCs de la receta del producto principal de la OP + AQL sugerido según ANSI/ASQ Z1.4 simplificado.

```
{
  receta_cod: "73",
  receta_nombre: "CHOCOLATE MESA OS/CF 24H X BLOQUE",
  tamano_lote_unidades: 8,
  aql_sugerido: 2,
  puntos_criticos: [
    { id, parametro, tipo, unidad, rango_min, rango_max, instrumento, opciones_json, obligatorio }
  ]
}
```

Lógica AQL ANSI/ASQ Z1.4 (S-2):
- 2-15 → 2
- 16-25 → 3
- 26-50 → 5
- 51-90 → 8
- 91-150 → 13
- 151-280 → 20
- 281+ → 32

Lookup PCs:
1. Identificar producto principal de la OP: `g_op_lineas WHERE id_op = ? AND tipo='producto' ORDER BY es_no_previsto LIMIT 1`
2. Buscar receta en `prod_recetas WHERE cod_articulo = X` (DB inventario_produccion_effi)
3. Cargar `prod_recetas_puntos_criticos WHERE receta_id = ?`

#### `POST /api/gestion/op/:id_op/calidad`

Crea inspección + registros de PCs en una transacción.

Body:
```json
{
  "tamano_muestra": 2,
  "visual_normal": "si",
  "tapado_sellado": "si",
  "etiqueta_normal": "si",
  "sabor_olor_normal": "si",
  "defectos_criticos": 0,
  "defectos_mayores": 0,
  "defectos_menores": 0,
  "resultado": "aprobado",
  "observacion": "...",
  "puntos_criticos": [
    { "pc_receta_id": 1, "parametro": "T° cocción", "tipo": "numerico",
      "unidad": "°C", "rango_min": 70, "rango_max": 85,
      "valor_numerico": 78, "observacion": null }
  ]
}
```

Calcula `dentro_rango` server-side por seguridad.

#### `GET /api/gestion/op/:id_op/calidad`

Lista inspecciones de la OP con sus PCs. Ordenado DESC por fecha.

Tests con curl + JWT:
- 404 si OP no existe
- Sugerencia devuelve estructura correcta
- POST inserta en transacción
- GET devuelve histórico

---

### Paso 3 — Frontend componente `CalidadPanel.vue`

Componente nuevo, mobile-first, embebido en `OpPanel.vue` entre "Tiempos consolidados" y "Tareas vinculadas".

#### Estructura visual (5 sub-bloques)

**Header del bloque**:
```
✅ CALIDAD                               [+ Nueva inspección]

[Si ya hay 1+ inspecciones → mostrar la más reciente]
🟢 Aprobado · 8 abr 14:30 · Santi
   2 muestras de 8 · 0 defectos · T°: 78°C ✓ · Tiempo: 40min ✓
```

**Form de nueva inspección** (collapse — abre al click "Nueva inspección"):

```
Bloque 1 — Muestreo
  Tamaño del lote: 8 unidades (auto)
  Tamaño de muestra: [2] (sugerido AQL: 2)

Bloque 2 — Inspección visual
  Visual normal       [Sí] [No] [N/A]
  Bien tapado         [Sí] [No] [N/A]
  Etiqueta normal     [Sí] [No] [N/A]
  Sabor / olor normal [Sí] [No] [N/A]

Bloque 3 — Mediciones (dinámicas por PC de la receta)
  🌡️ Temperatura cocción
     [_78_] °C    🟢 dentro de 70–85
  ⏱️ Tiempo cocción
     [_40_] min   🟢 dentro de 30–45
  👅 Sabor normal
     [Sí] [No] [N/A]

Bloque 4 — Defectos (input numérico simple con +/-)
  Críticos:  [-] [0] [+]   ⚠️ tolerancia 0
  Mayores:   [-] [0] [+]
  Menores:   [-] [0] [+]

Bloque 5 — Resultado
  ( ) Aprobado   ( ) Rechazado   ( ) Liberado con observación
  Observación: [textarea]
  Inspector: santi@gmail.com (auto)

  [Cancelar]    [Guardar inspección]
```

#### Reglas de validación frontend
- AQL sugerido por default, editable.
- Si fuera de rango → input se pinta rojo + chip "Fuera de rango".
- Si rechazado o críticos > 0 → observación obligatoria (botón Guardar disabled hasta llenar).
- Auto-set resultado="rechazado" si críticos > 0.

---

### Paso 4 — Integración con OpPanel

1. Importar `CalidadPanel` en `OpPanel.vue`.
2. Agregar el bloque `<CalidadPanel :id-op="idOp" :estado="estado" />` entre Tiempos y Tareas.
3. **Badge de calidad** en el header del panel (al lado del estado de Effi):
   - 🟢 Aprobado | 🔴 Rechazado | 🟡 Liberado con obs. | ⚪ Sin inspección
4. **Soft-block al validar**:
   - Si última inspección = rechazado → dialog "Esta OP tiene Calidad = Rechazado. ¿Validar de todos modos?".
   - Si NO hay inspección → dialog "Esta OP no tiene inspección de calidad. ¿Validar igual?".

---

### Paso 5 — Tests E2E

1. Abrir OP → ver bloque Calidad vacío.
2. Click "Nueva inspección":
   - PCs cargados según receta.
   - AQL sugerido correcto.
3. Llenar todo → guardar → ver en histórico.
4. Editar OP → ver inspección anterior.
5. Validar OP con calidad rechazada → confirmar dialog soft-block.
6. Mobile (≤500px) → form usable, inputs grandes.

---

### Paso 6 — Bump versión + commit + deploy

- `MainLayout.vue` → v2.10.30
- Build PWA + rsync VPS api/public + restart os-gestion
- Commit: `feat(gestion): sección Calidad por OP — inspección + registro PCs (v2.10.30)`
- Push a origin/main

---

### Paso 7 — Documentación

- Update `.agent/contextos/sistema_gestion.md` con la nueva sección.
- Update `CONTEXTO_ACTIVO.md` con un bloque "Completado 2026-05-08".
- Update `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md` §Histórico de validación.
- Mover este plan a `.agent/planes/completados/`.

---

## Pendientes futuros (NO en este plan)

- Vista `/calidad` con tabla histórica filtrable + export CSV.
- KPI dashboard "% lotes aprobados últimos 30 días".
- Integración con módulo ERP de no conformidades (cuando exista).
- Soporte de múltiples inspecciones intra-OP con timestamps.
