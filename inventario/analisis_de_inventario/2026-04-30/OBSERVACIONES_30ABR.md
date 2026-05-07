# Observaciones del cierre de inventario — 30-abr-2026

## ✅ Lo que mejoró respecto al cierre anterior (31-mar)

1. **Conteo más completo**: 100% de los inventariables contados (vs 187/314 = 60% en marzo).
2. **Bodega No Conformes separada**: ahora se cuenta y reporta aparte. Antes se mezclaba con Principal.
3. **Documentación de excepciones**: precarga SL (cods 593/594), remisión UNICOR #479 y OP Arancel 2241 quedaron documentadas en `notas.md` ANTES del cierre — sin fricción posterior.
4. **Análisis profundo automatizado**: 17 inconsistencias críticas/significativas cada una con archivo `.md` individual con trazabilidad Effi (movimientos, OPs, compras). Antes el análisis era manual.
5. **Método de testeo formalizado**: fórmula `físico + Σtraza_post_corte = stock_actual_effi` documentada en `METODO_TESTEO_AJUSTES.md` para verificar cada ajuste post-aplicación.

---

## 🔧 Lo que hay que mejorar para el próximo cierre

### 1. Reportar cantidades reales al validar OPs (NO estimadas)
Hoy los validadores de OPs (Deivy, Laura) suben las cantidades planificadas como reales. Eso genera ~24% de sobreconsumo invisible en mieles del Carmen (cod 586: -14.27 kg sin documentar).

**Acción**: en el módulo Gestión OS, exigir el peso/conteo real al cerrar la OP. Si difiere >5% del estimado, pedir nota explicativa.

### 2. Crear OPs ANTES de procesar físicamente
Caso emblemático: cacao San Luis. La transformación física (almendra → nibs + cascarilla) ocurrió en abril, pero la OP 2252 se creó hoy 06-may. Resultado: cod 585 quedó "fantasma" en el cierre del 30-abr con teórico 111 kg cuando físico era 0.

**Acción**: política "no se procesa material sin OP creada en estado Generada". Cuando se valida la OP, la cantidad real se ajusta — pero la trazabilidad queda en la fecha correcta.

### 3. Convención clara para compras pagadas un mes / recibidas en otro
La remisión UNICOR #479 llegó 04-may pero pertenecía a abril. Esta vez la sumamos manualmente al físico del 30-abr.

**Acción**: regla operativa — para el inventario físico cuenta lo que hay físicamente al corte, sin importar cuándo se pagó. Las facturas pendientes (pagadas no recibidas) se documentan en `inv_observaciones` con tipo `compra_pendiente_llegar`.

### 4. Eliminar artículos con nombres confusos / duplicados
Casos detectados con nombres muy similares que llevan a errores de conteo:
- **CREMA DE MANI**: cod 25 (130g) vs 151 (x kilo) vs 187 (230g) vs 241 (500g) — nombres similares, presentaciones distintas
- **Etiquetas Infusión**: cod 284 (200g delantera) vs 524 (200g trasera) vs 490/523 (400g delantera/trasera)
- **CHOCOBEETAL**: cod 405 (130g) vs 406 (230g) vs 557 (65g) — varias presentaciones del mismo producto base
- **Cajas chocolate**: cod 412 (73% chocolate) vs 580 (100%) — fácil de confundir
- **Etiquetas Chocolate Bombón**: cod 528 vs 283 vs 312 vs 376 — múltiples versiones

**Acción**: sesión específica de depuración. Anular el cod menos usado, mover stock al cod oficial. Normalizar nombres con patrón `<producto> <presentación> <variante>` consistente.

### 5. Auditar AJUSTES MANUALES de inventario antes del cierre
Los ajustes #361 (15-abr) y #369 (28-abr) generaron errores: crearon stock fantasma o sobreestimaron cantidades. Impacto combinado: ~$830k.

**Acción**: ningún ajuste manual sin evidencia (foto, conteo, pesaje documentado en `inv_observaciones`). Revisar quién hizo cada ajuste y con qué soporte.

### 6. Alerta semanal automática de stock negativo
En el cierre de 28-abr resolvimos 22 stocks negativos. En el cierre de 30-abr aparecieron otros 5 (319, 93, 342, 15, 411). El patrón se repite porque solo se detecta al hacer inventario físico.

**Acción**: cron semanal que escaneen `zeffi_inventario` por stocks negativos vigentes y notifique a Telegram. Atender ANTES del próximo cierre, no después.

### 7. Calibrar recetas que muestran cruce MP↔PT
Detectado en chocolate granulado: el MP cod 478 quedó faltante (-3.31 kg) mientras el PT cod 411 quedó sobrante (+9 unds). Misma cosa con mieles San Carlos vs Panal y tabletas almendra. Las recetas en `prod_recetas` declaran menos MP del que el empaque realmente consume.

**Acción**: en el próximo lote de cada producto problemático, pesar componentes uno por uno y actualizar gramaje en BD.

### 8. Comunicar al sistema CADA gasto / consumo / merma
Patrón sistémico: hay descuadres porque se consume material físicamente sin reportarlo en una OP, factura o ajuste. Ejemplos:
- Polen APICA cod 146: +5.42 kg físicos sin remisión registrada (proveedor entregó, no facturó)
- OP 2227 Miel Carmen 640: registró +12 unds que físicamente no aparecen
- Consumos de empaque no reportados en las recetas correspondientes

**Acción**: regla "todo material que entra o sale de planta tiene un documento Effi asociado" — sin excepción. Si entra sin remisión, se crea ajuste de inventario tipo ingreso con observación. Si sale sin OV, se crea ajuste tipo egreso con motivo (merma/dañado/regalo/promo).

---

## 📊 Cifras del cierre

| Métrica | Valor |
|---|---:|
| Artículos inventariables | 281 |
| Con diferencia | 169 (60%) |
| Sin diferencia (OK) | 112 (40%) |
| Casos críticos (impacto >2%) | 6 |
| Casos significativos (impacto 0.5-2%) | 14 |
| Casos menores (impacto <0.5%) | 149 |
| Impacto bruto total ajustes | +$1.035.750 |
| Impacto operativo real (excl precarga SL justificada) | ~-$650.000 |

**Lectura**: el inventario tiene una pérdida operativa real cercana a $650k al cierre, principalmente por sobreconsumo en envasado de mieles, recetas mal calibradas y ajustes históricos sin soporte. Si en el próximo cierre bajamos a < $300k, vamos en buen camino.

---

## 🎯 Acciones aplicadas en este cierre

1. ✅ Conteo físico 100% completado
2. ✅ Bodega Jenifer consolidada a Principal (37 ítems sumados)
3. ✅ 8 NM matriculados (3 envases nuevos en Effi: cods 597/598/599; 5 reasignados a cods existentes)
4. ✅ Análisis profundo de 17 inconsistencias con .md individual
5. ✅ 177 ajustes aplicados en Effi (Principal #371 y No Conformes #372)
6. ✅ Todo registrado en `inv_analisis_inconsistencias` e `inv_ajustes_historico`
7. ✅ Método de testeo documentado y aplicado para validar cada ajuste

---

## 📁 Archivos de referencia

- `notas.md` — excepciones aplicadas durante el conteo
- `RESUMEN_INCONSISTENCIAS.md` — detalle de las 17 inconsistencias profundas
- `METODO_TESTEO_AJUSTES.md` — fórmula de verificación post-ajuste
- `2026-04-28/RESUMEN.md` — auditoría previa de stocks negativos
- `inv_analisis_inconsistencias`, `inv_ajustes_historico` (BD `inventario_produccion_effi`) — registro permanente
