# Notas inventario 2026-04-30

**Fecha de corte**: 2026-04-30 23:59:59
**Fuente teórico**: `inventario/snapshots/inventario_2026-04-30_teorico.xlsx` (export crudo Effi tomado el 1-may, 372 artículos vigentes)
**Bodegas activas**: Principal, Productos No Conformes, Jenifer
**Estado actual**: 100 % contado + 2 ajustes manuales documentados abajo

---

## Excepciones aplicadas

### 1. Cacao San Luis — precarga manual (cods 593, 594)
- **Cod 593** NIBS DE CACAO SL x KG → físico precargado **97.5 kg** en Principal
- **Cod 594** CASCARILLA DE CACAO SL x KG → físico precargado **16 kg** en Principal
- **Razón**: ambos cods se crearon en Effi el 03-may pero el material físicamente estaba en planta desde abril (pagado en abril, entrada formal en mayo, sin orden de compra todavía). Como los cods aún no aparecen en `zeffi_inventario` (el espejo se sincroniza cada 1h), el teórico = 0 y el físico se precargó manualmente.
- **Notas en BD**: campo `notas` con texto `Precarga: ... — restaurado tras recuento erróneo a 0`. El equipo de conteo los recontó a 0 inicialmente sin saber que ya estaban precargados; se restauraron via UPDATE.
- **Diferencia esperada**: +97.5 (cod 593) y +16 (cod 594) — entran como ingreso a Effi cuando se aplique el ajuste.

### 2. Envases UNICOR — remisión de compra #479 sumada al físico
- **Remisión #479** (UNICOR S.A., creada 04-may 17:12, $359.784,60) trae 4 envases:
  - cod **85** Envase Vidrio 750cc UNICOR — 36 unds × $2.205
  - cod **86** Envase Vidrio 110cc UNICOR — 72 unds × $1.000
  - cod **87** Envase Vidrio 230cc UNICOR — 72 unds × $1.060
  - cod **88** Envase Vidrio 500cc UNICOR — 48 unds × $1.555
- **Razón**: pagados en abril, recibidos físicamente el 04-may (entregados a Arancel para envasado de miel). La remisión es del 04-may pero la compra cuenta para abril.
- **Acción aplicada**: sumadas las 4 cantidades al `inventario_fisico` de cada cod (en bodega Principal).
- **Diferencias resultantes** post-ajuste:
  - 85: teo 0 / fis 41 → +41
  - 86: teo 112 / fis 72 → -40
  - 87: teo 102 / fis 74 → -28
  - 88: teo 0 / fis 48 → +48

---

## Compras pagadas pero no llegadas / pendientes de registrar en Effi

Ninguna pendiente al 04-may. La remisión #479 ya fue registrada y reflejada (vía sync directo `effi_data` → `os_integracion`).

---

## OPs derivadas del inventario

### OP 2241 — Arancel envasado miel sin etiquetar (creada 04-may)
- **Origen**: los envases UNICOR de la remisión #479 fueron entregados a Arancel para que envasara miel. Arancel devolvió hoy 04-may los envases llenos (vendió la miel a OS + cobra envasado).
- **Materiales**: 97 kg miel cod 373 (vendida por Arancel) + los 4 envases UNICOR
- **Productos**: 36×550 + 48×547 + 72×546 + 72×548 (mieles SIN ETIQUETAR)
- **Otro costo**: 228 unds × $500 = $114.000 (envasado APICA — id 8)
- Patrón documentado en skill `produccion-recetas/SKILL.md` §"Línea ARANCEL"

---

## Decisiones de criterio

### a) OV #720 (1-may 00:03 KAKAW $877k)
- Excluida del cálculo "Paso 1 trazabilidad" para validar el xlsx (370/372 vigentes coinciden si se ignora #720).
- El xlsx ya descontó esta OV (fue tomado a las 00:03+) → teórico final cargado = del xlsx → coherente con el cierre real al 30-abr 23:59.

### b) Mercancía en consignación
- Reporte aparte en `consignacion_al_30abr.{md,csv,por_ov.csv,por_articulo.csv}` (10 OVs, 312 unds, $5.879.323).
- Effi descuenta del `stock_total_empresa` al crear la OV → ya está descontada del xlsx → NO requiere ajuste.

### c) 14 cods con stock en categorías excluidas (T999/T05/XMATERIAL)
- Insertados como **excluidos** (`bodega='—'`, `excluido=1`) con su stock del xlsx como referencia, pero NO se cuentan físicamente.
- Cods: 63, 181, 200, 234, 246, 270, 271, 280, 281, 282, 286, 408, 409.

### d) 13 anulados-con-stock del 29-abr
- Insertados manualmente con teórico del CSV de depuración. Bodega Principal. Estado pendiente para que el equipo confirme físico.
- Cods: 70, 82, 199, 204, 274, 351, 352, 353, 354, 372, 402, 403, 404.

### e) 8 stocks negativos del xlsx
- Insertados con teórico negativo (cods 14, 15, 53, 93, 319, 342, 528, 554, 582). Diferencia se calculará al confirmar físico.

---

## Pendientes para próximo inventario

- Definir flujo formal para **cacao San Luis** (cods 593, 594): cuándo crear OC para regularizar la entrada en Effi, ajuste teórico vs físico al cierre próximo.
- Revisar el patrón "compra pagada en mes X pero registrada en mes Y" — quizás conviene sistemizar mediante una nota campo `pagada_en` en `inv_observaciones`.
- Bug visual confirmado: la pausa de jornada en el detalle de la app pinta hora en formato 12h con offset -1h vs BD (BD dice 12:29-14:00 = 91 min, app pinta 01:29-02:00 PM = 31 min). Excel tiene el dato correcto.

---

## Backups de este inventario

- `backups/inventario_produccion_effi/inventario_2026-04-30_2026-05-04_234901.sql` — snapshot 100% contado pre-restauración SL
- `backups/inventario_produccion_effi/inventario_2026-04-30_post_precargas_2026-05-04_235430.sql` — post-restauración SL
- `inventario/snapshots/inventario_2026-04-30_fisico_completo.csv` — versionable en repo
