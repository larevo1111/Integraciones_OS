# Zona Horaria en Tablas Effi — Referencia Definitiva

**Verificado**: 2026-04-20
**Conclusión**: CASI todas las tablas están en **hora Colombia (UTC-5)**, EXCEPTO `zeffi_cambios_estado` que está en **UTC**

---

## Por qué están en UTC-5

1. Effi exporta los Excel con timestamps en hora Colombia
2. Los scripts de exportación (`export_*.js`) no convierten timezone
3. El importador (`import_all.js`) inserta como TEXT sin modificación
4. Verificado con movimientos reales del 20 de abril: las horas coinciden con horario laboral colombiano

## Tabla por tabla

| Tabla | Columna timestamp | Timezone | Verificado |
|---|---|---|---|
| zeffi_trazabilidad | fecha | UTC-5 | Sí — horas 9am-6pm Colombia |
| zeffi_produccion_encabezados | fecha_de_creacion | UTC-5 | Sí — creación OPs en horario laboral |
| zeffi_cambios_estado | f_cambio_de_estado | **UTC** | Sí — exactamente +5h respecto a fecha_de_creacion de la misma OP |
| zeffi_remisiones_venta_encabezados | fecha_de_creacion | UTC-5 | Sí — confirmado con screenshot Effi |
| zeffi_facturas_venta_encabezados | fecha_de_creacion | UTC-5 | Asumido (mismo patrón) |
| zeffi_inventario | fecha_de_creacion, fecha_de_modificacion | UTC-5 | Asumido |
| zeffi_ajustes_inventario | fecha_de_creacion | UTC-5 | Asumido |

## Solución implementada

`import_all.js` convierte `zeffi_cambios_estado.f_cambio_de_estado` de UTC a UTC-5 al importar:
```sql
UPDATE zeffi_cambios_estado SET f_cambio_de_estado = DATE_SUB(f_cambio_de_estado, INTERVAL 5 HOUR)
```

Así TODA la BD effi_data queda uniformemente en UTC-5 y ningún script necesita hacer conversiones.

## Regla para queries

**NO hacer conversiones de timezone.** Todas las fechas ya están en hora Colombia.

```sql
-- CORRECTO: comparar directo
WHERE fecha <= '2026-04-20 14:30:00'

-- INCORRECTO: no sumar ni restar horas
WHERE fecha <= DATE_ADD('2026-04-20 14:30:00', INTERVAL 5 HOUR)  -- MAL
```
