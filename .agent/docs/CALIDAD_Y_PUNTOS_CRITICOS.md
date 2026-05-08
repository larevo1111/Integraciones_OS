# Calidad y puntos críticos — Bitácora de proceso productivo

**Última actualización**: 2026-04-29
**Audiencia**: equipo OS + agentes Claude que trabajen en módulos de Producción / Gestión / Calidad
**Estándar de referencia**: HACCP / ISO 22000 (PCC = Puntos Críticos de Control)

---

## 1. Modelo conceptual (clasificación 5S)

Hay **dos secciones distintas** en la bitácora de calidad de una OP. Es crítico no mezclarlas.

### A. Inspección de calidad (genérica, igual para TODOS los productos)

Booleanos / contadores fijos que aplica a cualquier producto que pase por control:

| Campo | Tipo | Notas |
|---|---|---|
| Inspección visual normal | Sí / No / N.A. | — |
| Bien tapado / sellado | Sí / No / N.A. | Aplica a empacados |
| Etiquetado normal | Sí / No / N.A. | — |
| Sabor / olor normal | Sí / No / N.A. | — |
| Tamaño de muestra (AQL) | numérico | — |
| Defectos críticos / mayores / menores | numéricos | Conteo |
| Resultado | Aprobado / Rechazado | — |
| Firma / revisor | texto | — |

Esto **NO va en la ficha del producto** — vive en la ficha de la OP en el módulo Gestión OS.

### B. Puntos críticos (configurables POR producto)

Parámetros específicos de cada producto que requieren medición. Definidos en la **ficha de la receta** (Producción), heredados automáticamente en cada OP.

**Tabla en BD**: `prod_recetas_puntos_criticos` (en `inventario_produccion_effi` VPS).

---

## 2. Reglas para definir puntos críticos (5S)

### Filosofía
- **Solo lo medible**: si no tenés instrumento o procedimiento estándar para medirlo, NO va.
- **Máximo 3-5 puntos por producto**: más se vuelve ruido y el operario llena con valores falsos para terminar.
- **Cada parámetro debe tener acción**: si una desviación no genera decisión (ajuste, rechazo, alerta), no vale la pena medirla.
- **Los rangos vienen de medición real**, no de manual técnico copiado.

### Tipos disponibles en `prod_recetas_puntos_criticos`
| Tipo | Cuándo usar | Campos requeridos |
|---|---|---|
| `numerico` | Mediciones con instrumento | `unidad`, `valor_min`, `valor_max` |
| `booleano` | Sí / No con criterio claro | — |
| `texto` | Observación libre, sin validación | — |
| `seleccion` | Lista cerrada de opciones | `opciones_json` (CSV) |

### Instrumentos disponibles en planta OS (2026-04-29)
- **Termómetro** (sonda y/o infrarrojo)
- **Cronómetro / timer**
- **Balanza / gramera**
- **pH-metro** (toma muestras en agua + nevera, productos refrigerados)
- **Revisión organoléptica**: visual, olfativa, gusto (sin instrumento)
- **Test de papel** para templado de chocolate (NO test de cuchillo — se usa papel)

NO tenemos: refractómetro (Brix), higrómetro (humedad ambiental), micrómetro (tamaño partícula).

### Cosas que NO recomendamos
1. Copiar parámetros de manuales sin medir realmente en la planta. Los rangos varían por equipo, ingredientes, altitud (Medellín 1.500 msnm).
2. Hacer todos los parámetros obligatorios — el operario falsea para terminar.
3. Definir parámetros sin rango — sin min/max el sistema no puede alertar.

---

## 3. Procesos productivos identificados en OS

Los 99 productos en proceso (PP) de OS se agrupan en **~10 procesos base**. Los puntos críticos se definen por proceso (no por SKU final), porque las presentaciones (150g / 275g / 640g) comparten el proceso de fabricación.

| Proceso base | Productos clave (cod) | Etapa crítica |
|---|---|---|
| **Cocción chocolate de mesa** | 73 (24h), 74 (12h), 93 (moldeado) | Cocción |
| **Refinado/conchado chocolate** (24h) | Salida del 73 | Tiempo + temperatura |
| **Templado chocolate** | 583 (CHOC 100% templada), 581 (CPM 73% templada), 485 (manteca templada) | T° trabajo + test papel |
| **Pasteurización miel** | 373, 586, 60 (San Miguel) | T° máxima + tiempo + pH |
| **Cristalización miel** | 348 (Carmen Cristalizada) | T° controlada + tiempo |
| **Infusionado de miel** | 134 (Vainilla), 384 (Aromática), 387 (Fuego) | T° infusión + tiempo + pH |
| **Tostado cacao** | 80 (cascarilla), 178/261 (nibs/almendra granel) | T° + tiempo + color |
| **Tostado frutos secos** | 196 (macadamia), 508 (almendra), 516 (marañón) | T° + tiempo |
| **Crema (molienda)** | 151 (mani), 479 (almendra), 367 (macadamia), 388 (mac+nibs) | T° molienda + organoléptico |
| **Infusión cacao+menta+polen** | 339 | T° infusión + tiempo |
| **Chocomiel** | 346 (80/20) | T° mezcla + ratio |
| **Chocobeetal** | 275 (granel) | T° fusión + ratio polen |

### Productos derivados (no requieren puntos críticos propios)
Las presentaciones (envases de distinto tamaño) heredan los puntos críticos del proceso base. Ej:
- **Mieles San Carlos / Carmen / Panel / Vidrio** (150/275/640/1000 grs) → puntos críticos del proceso "Pasteurización miel"
- **Tabletas / Bombones / Granulados** → puntos del "Templado chocolate"
- **Chocobeetal 50/65/90/130/230 grs** → puntos del "Chocobeetal granel"

---

## 4. Plantillas concretas (3-5 puntos por proceso)

### 🍫 Cocción chocolate de mesa (cod 73, 74, 93)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura cocción | numérico | °C | 70 | 85 | Termómetro |
| 2 | Tiempo cocción | numérico | min | 30 | 45 | Cronómetro |
| 3 | Sabor / olor normal | booleano | — | — | — | Organoléptico |

### 🍫 Templado chocolate (cod 583, 581, 485, todos derivados de tabletas/bombones/granulados)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura fusión | numérico | °C | 45 | 50 | Termómetro |
| 2 | Temperatura trabajo | numérico | °C | 31 | 32 | Termómetro |
| 3 | Test de papel (cristaliza en 3 min) | booleano | — | — | — | Test papel |

### 🍯 Pasteurización miel (cod 373, 586, 60 → derivados todas las mieles envasadas)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura máxima | numérico | °C | 60 | 65 | Termómetro |
| 2 | Tiempo a temperatura | numérico | min | 20 | 30 | Cronómetro |
| 3 | pH (muestra en agua, nevera) | numérico | pH | 3.5 | 4.5 | pH-metro |
| 4 | Sabor / olor normal | booleano | — | — | — | Organoléptico |

### 🍯 Mieles infusionadas (cod 134, 384, 387)
Igual que pasteurización + parámetro de tiempo de infusión.

### 🌰 Tostado cacao (cod 80 cascarilla, 178 nibs, 261 almendra cacao)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura tostado | numérico | °C | 110 | 140 | Termómetro |
| 2 | Tiempo tostado | numérico | min | 15 | 45 | Cronómetro |
| 3 | Color final | seleccion | — | — | — | Visual (Claro/Medio/Oscuro) |

### 🥜 Tostado frutos secos (cod 196 macadamia, 508 almendra, 516 marañón)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura tostado | numérico | °C | (definir por producto) | — | Termómetro |
| 2 | Tiempo tostado | numérico | min | (definir por producto) | — | Cronómetro |
| 3 | Sabor normal | booleano | — | — | — | Organoléptico |

### 🥜 Crema de molienda (cod 151 mani, 479 almendra, 367 macadamia, 388 mac+nibs)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura molienda final | numérico | °C | (definir) | — | Termómetro |
| 2 | Textura (consistencia) | seleccion | — | — | — | Visual (Líquido/Pastoso/Sólido) |
| 3 | Sabor normal | booleano | — | — | — | Organoléptico |

### 🍫 Chocobeetal (cod 275 granel)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura fusión chocolate | numérico | °C | 45 | 50 | Termómetro |
| 2 | Temperatura mezcla con polen | numérico | °C | 35 | 40 | Termómetro |
| 3 | Sabor / olor normal | booleano | — | — | — | Organoléptico |

### 🌿 Infusión cacao+menta+polen granel (cod 339)
| # | Parámetro | Tipo | Unidad | Min | Max | Instrumento |
|---|---|---|---|---|---|---|
| 1 | Temperatura infusión | numérico | °C | (definir) | — | Termómetro |
| 2 | Tiempo infusión | numérico | min | (definir) | — | Cronómetro |
| 3 | Sabor / olor normal | booleano | — | — | — | Organoléptico |

---

## 5. Vinculación con HACCP (futuro)

Cuando OS certifique HACCP / ISO 22000, los puntos críticos de este sistema = PCC de la norma. Solo agregar campos opcionales:
- `limite_critico` (override del rango normal)
- `accion_correctiva`
- `responsable_monitoreo`

El esqueleto ya está. Migración será add-only.

---

## 6. Histórico de validación (qué SKUs tienen puntos críticos definidos)

Esta sección se actualiza cada vez que validamos puntos críticos en producción.

| Fecha | Proceso | SKUs cubiertos | Validó |
|---|---|---|---|
| 2026-04-29 | Múltiples (importación CSV inicial) | 17 recetas / 99 | Santi |

---

## 7. Implementación digital — Sistema Gestión OS (v2.10.30, 2026-05-08)

La bitácora de calidad en papel ahora vive como bloque **CalidadPanel** dentro del panel de cada OP en `gestion.oscomunidad.com`.

### Tablas (BD `os_gestion` VPS)
- `g_op_inspeccion_calidad` — 1 row por inspección (puede haber N por OP).
- `g_op_pc_registro` — FK a inspeccion. Snapshot de cada PC medido.

### Endpoints
- `GET /api/gestion/op/:id/calidad/sugerencia` — devuelve PCs de la receta del producto principal de la OP + AQL sugerido (ANSI/ASQ Z1.4 simplificado).
- `GET /api/gestion/op/:id/calidad` — lista inspecciones con sus PCs.
- `POST /api/gestion/op/:id/calidad` — crea inspección + PCs en transacción.

### Componente `sistema_gestion/app/src/components/CalidadPanel.vue`
5 sub-bloques: muestreo / inspección visual genérica / mediciones PCs / defectos / resultado.

### Restricciones de alcance (acordadas con Santi 2026-05-08)
- Calidad vive 100% en `os_gestion`. NUNCA toca Effi (no estados nuevos en zeffi, no workflows nuevos).
- "Aprobado/Rechazado" es metadato informativo. Soft-block al validar — el director decide.
- Workflow de no conformidades / reproceso / descarte → módulo ERP futuro.

Plan completado: `.agent/planes/completados/calidad_inspeccion_op_2026-05-08.md`.
