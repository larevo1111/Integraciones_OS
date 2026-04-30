# Depuración inventariables inactivos — 2026-04-30

**Criterio:** vigentes en Effi + presentes en inventario físico del 31 marzo 2026 + sin movimientos (ventas/compras/OPs material/OPs producto) desde **2025-04-30** (1 año).

## Trazabilidad del universo

| Paso | Cods |
|---|---|
| 1. Inventario físico 31-mar-2026 | 493 |
| 2. − anulados el 29-abr (94) | 399 |
| 3. ∩ vigentes hoy en zeffi_inventario | 391 |
| 4. **Sin movimientos desde 2025-04-30** | **196** |

## Resumen

- **Candidatos a depurar: 196**
- Sin stock (anular limpio): 149
- Con stock > 0 (revisar antes): 47
- Valor inventario actual de los candidatos: $2,654,605

## Por categoría

| Categoría | N° artículos | Con stock |
|---|---|---|
| GASTOS | 62 | 0 |
| T03.03. ENVASES ECOLOGICOS | 28 | 19 |
| T03.21. ETIQUETAS ADESIVAS | 16 | 5 |
| T999. PRODUCTOS QUE NO SE USAN | 12 | 2 |
| T05.06. CONSUMIBLES PRODUCCION Y VENTAS | 10 | 4 |
| T03.01. ENVASES Y TAPAS | 9 | 2 |
| T05.02. A.F. MOLDES | 7 | 5 |
| T09.01. SERVICIOS MAQUILA | 7 | 0 |
| TPT.01. VENTA AGROECOLOGICOS VARIOS | 7 | 0 |
| T03.31. BOLSAS PLASTICAS | 6 | 5 |
| T05.03. HERRAMIENTAS | 6 | 1 |
| XMATERIAL DE APOYO VENTAS POP | 6 | 1 |
| DESARROLLO DE PRODUCTO | 4 | 0 |
| TPT.02. VENTA OTROS | 4 | 1 |
| T01.03. AGROECOLOGICOS GRAL | 3 | 1 |
| (sin categoría) | 3 | 0 |
| T09.02. SERVICIOS M.O. | 2 | 0 |
| T03.31. BOLSAS DE PAPEL | 1 | 0 |
| T03.41. CAJAS | 1 | 1 |
| T09.06. SERVICIOS LOGISTICA | 1 | 0 |
| T09.10. SERVICIOS GENERALES | 1 | 0 |

## Cómo usar este archivo

1. Abrí `depuracion_inventariables_inactivos.csv` en LibreOffice/Excel.
2. Marcá con **x** (en columna 3) los que querés ANULAR en Effi.
3. Guardá el CSV.
4. Ejecutá `python3 scripts/import_articulo_anular_post.py` para anularlos.

## Lista completa

Ordenada por categoría → cod.

| cod | nombre | categoría | tipo | stock | costo unit | valor | acción |
|---|---|---|---|---|---|---|---|
| 388 | CREMA DE MACADAMIA CON NIBS X KILO | DESARROLLO DE PRODUCTO | Producto en proceso | — | 1 | — | CANDIDATO ANULAR — sin stock |
| 393 | CREMA DE MACADAMIA CON NIBS OS 60 GRS | DESARROLLO DE PRODUCTO | Producto en proceso | — | 6696 | — | CANDIDATO ANULAR — sin stock |
| 394 | CREMA DE MACADAMIA CON NIBS OS 110 GRS | DESARROLLO DE PRODUCTO | Producto en proceso | — | 10332 | — | CANDIDATO ANULAR — sin stock |
| 395 | CREMA DE MACADAMIA CON NIBS OS 200 GRS | DESARROLLO DE PRODUCTO | Producto en proceso | — | 16672 | — | CANDIDATO ANULAR — sin stock |
| 415 | O01.01. Papeleria | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 416 | O01.02. Impuestos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 417 | O01.03. Gastos de publicidad e imagen | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 418 | O01.04. Gastos desarrollo de producto | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 419 | O01.05. Fletes Ventas OS | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 420 | O01.06. Gastos de Venta OS | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 421 | O01.07. Software | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 422 | O01.08. Gestiones administrativas y legales | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 423 | O01.09. Viaticos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 424 | O01.10. Gastos Bancarios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 425 | O01.11. Arriendo | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 426 | O01.12. Servicios Publicos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 427 | O01.13. Ferreteria | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 428 | O01.14. Feria viaticos y general | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 429 | O01.15. Feria gastos de venta | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 430 | O01.16. Feria insumos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 431 | O01.17. Gastos en mejoras y varios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 432 | O01.18. Uniformes y dotacion | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 433 | O01.19. Consumibles produccion | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 434 | O01.20. Gastos Generales | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 435 | O01.21. Tecnologia | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 436 | O01.22. Fletes compras | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 437 | O01.23. Estudios de mercado y competencia | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 438 | O01.30. Por Identificar | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 439 | O06.01. Herramientas | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 440 | O06.02. Maquinas | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 441 | O06.03. Activos Muebles | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 442 | O06.04. Activos Fijos y reformas | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 443 | O06.05. Vehiculos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 444 | O06.06. Tecnologia | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 445 | O06.07. Molderia general | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 446 | O06.08. Material POP | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 447 | O06.20. Otros Activos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 448 | O07.01. Honorarios a socios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 449 | O07.02. Comisiones miembros | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 450 | O07.03. Honorarios a terceros | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 451 | O07.04. Salarios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 452 | O07.05. Eps | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 453 | O07.06. Arl | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 454 | O07.07. Pension | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 455 | O07.08. Parafiscales | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 456 | O07.09. Primas | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 457 | O07.10. Cesantias | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 458 | O07.11. Bonificaciones e incentivos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 459 | O07.12. Pago Dividendos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 460 | O07.13. Subsidio de transporte | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 461 | O07.14. Comision x desempéño | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 462 | O07.15. Pagos x Dia | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 463 | O07.16. Comisiones red de amigos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 464 | O07.17. Comisiones a terceros | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 465 | O07.18. x | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 466 | O07.19. x | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 467 | O07.20. Pagos de Honorarios y dividendos General | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 468 | O08.04. Pago Intereses Socios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 469 | O08.05. Pago Intereses Familiares y amigos | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 470 | O08.06. Pago Intereses Entidades Financieras | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 471 | O08.10. Pago Deudas e Intereses: | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 472 | O09.04. Inversiones Financieras | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 473 | O10.01. Cursos y mentorias | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 474 | O10.02. Talleres y seminarios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 475 | O10.02. Estudios periodos medios | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 476 | O10.10. Capacitaciones y Asesorias General | GASTOS | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 137 | MANI SIN CASCARA X KILO | T01.03. AGROECOLOGICOS GRAL | Materia prima | 18 | 11000 | 198000 | REVISAR — tiene stock |
| 324 | ENVASE 500G CON PANAL X UNIDAD | T01.03. AGROECOLOGICOS GRAL | Producto en proceso | — | — | — | CANDIDATO ANULAR — sin stock |
| 520 | DESPERDICIO - CHOCOMIEL 80/20 x Kg | T01.03. AGROECOLOGICOS GRAL | Producto en proceso | — | 21276 | — | CANDIDATO ANULAR — sin stock |
| 64 | TAPA METALICA B.53 UNICOR | T03.01. ENVASES Y TAPAS | Materia prima | — | 325,25 | — | CANDIDATO ANULAR — sin stock |
| 68 | TAPA METALICA DORADA B.38 UNICOR | T03.01. ENVASES Y TAPAS | Materia prima | — | 183,2 | — | CANDIDATO ANULAR — sin stock |
| 78 | TAPA METALICA B.63 X UNIDAD | T03.01. ENVASES Y TAPAS | Materia prima | 84 | 370 | 31080 | REVISAR — tiene stock |
| 135 | ENVASE VIDRIO R 4186-2465, 130 CC B.48 C Tapa UNICOR | T03.01. ENVASES Y TAPAS | Materia prima | — | 947 | — | CANDIDATO ANULAR — sin stock |
| 180 | TAPA METALICA DORADA B.48 | T03.01. ENVASES Y TAPAS | Materia prima | — | 462 | — | CANDIDATO ANULAR — sin stock |
| 208 | Envase Vidrio R mb110h Flint, 110cc, B. 46 UNICOR | T03.01. ENVASES Y TAPAS | Materia prima | — | 1020,2 | — | CANDIDATO ANULAR — sin stock |
| 233 | Envase Vidrio MB30R Flint, 30cc, B. 41 C Tapa UNICOR | T03.01. ENVASES Y TAPAS | Materia prima | — | 784 | — | CANDIDATO ANULAR — sin stock |
| 322 | TAPA METÁLICA B46 X UNIDAD | T03.01. ENVASES Y TAPAS | Materia prima | 24 | 200 | 4800 | REVISAR — tiene stock |
| 337 | ENVASE MB50R FLINT 50CCTO B.45 DEGUSTACION REDONDO | T03.01. ENVASES Y TAPAS | Materia prima | — | 915 | — | CANDIDATO ANULAR — sin stock |
| 95 | BOLSA FLEX UP MINI 133 X 170 80-160 GRS ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 3 | 315,2 | 945,6 | REVISAR — tiene stock |
| 96 | BOLSA FLEX UP PEQUE 133 X 210 150-250 GRS ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 8 | 372,3 | 2978,4 | REVISAR — tiene stock |
| 98 | BOLSA FLEX UP GRANDE 190 X 250 480-650 GRS ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | — | 591,6 | — | CANDIDATO ANULAR — sin stock |
| 99 | BOLSA FLEX UP VENTANA PEQUE 133 X 210 150-250 GRS ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 8 | 382,36 | 3058,88 | REVISAR — tiene stock |
| 101 | BOLSA TRANSP VALVULA DOY PACK 10 X 18 + FFA 6cms 200 - 300 GRS (ABIERTA) Bolsa transparente con tapa pequeña ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 1 | 344,6 | 344,6 | REVISAR — tiene stock |
| 102 | BOLSA TRANSP VALVULA DOY PACK 10 X 18 + FFA 6cms 200 - 300 GRS (CERRADA) Bolsa transparente con tapa pequeña ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 45 | 345 | 15525 | REVISAR — tiene stock |
| 103 | BOLSA TRANSP VALVULA DOY PACK 13.3 X 21 + FFA 7cms 300 - 400 GRS (ABIERTA) Bolsa transparente con tapa mediana ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 6 | 458 | 2748 | REVISAR — tiene stock |
| 104 | BOLSA TRANSP VALVULA DOY PACK 13.3 X 21 + FFA 7cms 300 - 400 GRS (CERRADA) Bolsa transparente con tapa mediana ALICO | T03.03. ENVASES ECOLOGICOS | Materia prima | 32 | 458 | 14656 | REVISAR — tiene stock |
| 139 | BOLSA DOY PACK PET/FLEXIBLE SIN IMPRESION TRANSPARENTE 7.0 X 8.0 80 MICRAS CON VALVULA | T03.03. ENVASES ECOLOGICOS | Materia prima | — | — | — | CANDIDATO ANULAR — sin stock |
| 140 | RECIPACK 2.0 - AB 100X180FFA60MM FLEX UP TTE | T03.03. ENVASES ECOLOGICOS | Materia prima | 27 | 236 | 6372 | REVISAR — tiene stock |
| 141 | RECIPACK 2.0-AB 133X210FFA70MM FLEX UP TTE | T03.03. ENVASES ECOLOGICOS | Materia prima | 19 | 216 | 4104 | REVISAR — tiene stock |
| 142 | RECIPACK 2.0 160X240FFA80MM FLEX UP TTE | T03.03. ENVASES ECOLOGICOS | Materia prima | 27 | 279 | 7533 | REVISAR — tiene stock |
| 560 | BOLSA FLEX UP VENTANA MED CON ETIQUETAS INFUSION 400 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 18 | 1487,4 | 26773,2 | REVISAR — tiene stock |
| 561 | BOLSA METALIZADA VENTANA CON ETIQUETAS INFUSION 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 562 | BOLSA METALIZADA VENTANA CON ETIQUETAS CHOCOLATE BOMBONES 250 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 12 | 1487,4 | 17848,8 | REVISAR — tiene stock |
| 563 | BOLSA METALIZADA VENTANA CON ETIQUETAS CHOCOLATE GRANULADO 250 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 16 | 1487,4 | 23798,4 | REVISAR — tiene stock |
| 565 | BOLSA METALIZADA VENTANA CON ETIQUETAS NIBS 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 15 | 1487,4 | 22311 | REVISAR — tiene stock |
| 566 | BOLSA METALIZADA VENTANA CON ETIQUETAS ALMENDRA 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 5 | 1487,4 | 7437 | REVISAR — tiene stock |
| 567 | BOLSA METALIZADA VENTANA CON ETIQUETAS ALMENDRA DE CACAO 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 568 | BOLSA METALIZADA VENTANA CON ETIQUETAS MACADAMIA 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 569 | BOLSA METALIZADA VENTANA CON ETIQUETAS MARAÑON 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 4 | 1487,4 | 5949,6 | REVISAR — tiene stock |
| 570 | BOLSA METALIZADA VENTANA CON ETIQUETAS MIX FRUTOS SECOS 200 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 571 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS MIX FRUTOS SECOS 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 572 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS MACADAMIA 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 2 | 1487,4 | 2974,8 | REVISAR — tiene stock |
| 573 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS ALMENDRA 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 12 | 1487,4 | 17848,8 | REVISAR — tiene stock |
| 574 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS MARAÑON 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | 8 | 1487,4 | 11899,2 | REVISAR — tiene stock |
| 575 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS NIBS 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 576 | BOLSA PEQUEÑA TRANSPARENTE CON ETIQUETAS ALMENDRA DE CACAO 100 GR | T03.03. ENVASES ECOLOGICOS | Producto en proceso | — | 1487,4 | — | CANDIDATO ANULAR — sin stock |
| 491 | ETIQUETA MIEL OS 500G PLAST. | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 150 | — | CANDIDATO ANULAR — sin stock |
| 492 | ETIQUETA MIEL OS 265G PLAST. | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 150 | — | CANDIDATO ANULAR — sin stock |
| 507 | ETIQUETA PRECIOS X HOJA | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 6500 | — | CANDIDATO ANULAR — sin stock |
| 531 | Etiqueta tableta tornasol cacao organico x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 22,5 | — | CANDIDATO ANULAR — sin stock |
| 532 | Etiqueta tableta tornasol 100p natural x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 22,5 | — | CANDIDATO ANULAR — sin stock |
| 533 | Etiqueta tableta tornasol solo chocolate x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 534 | Etiqueta tableta tornasol con macadamia x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 535 | Etiqueta tableta tornasol con mani x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 536 | Etiqueta tableta tornasol con almendra x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 537 | Etiqueta tableta tornasol con nibs de cacao x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 538 | Etiqueta tableta tornasol con sal marina x unidad | T03.21. ETIQUETAS ADESIVAS | Materia prima | — | 19,54 | — | CANDIDATO ANULAR — sin stock |
| 541 | ETIQUETA MIX FRUTOS SECOS 100G TRASERA X UNIDAD | T03.21. ETIQUETAS ADESIVAS | Materia prima | 134 | 410 | 54940 | REVISAR — tiene stock |
| 542 | ETIQUETA MACADAMIA 100G TRASERA X UNIDAD | T03.21. ETIQUETAS ADESIVAS | Materia prima | 55 | 818 | 44990 | REVISAR — tiene stock |
| 544 | ETIQUETA MARAÑON 100G TRASERA X UNIDAD | T03.21. ETIQUETAS ADESIVAS | Materia prima | 45 | 1000 | 45000 | REVISAR — tiene stock |
| 577 | Etiqueta Transparente Miel Panal 275 gr | T03.21. ETIQUETAS ADESIVAS | Materia prima | 2 | 300 | 600 | REVISAR — tiene stock |
| 578 | Etiqueta Transparente Miel Panal 150 gr | T03.21. ETIQUETAS ADESIVAS | Materia prima | 11 | 300 | 3300 | REVISAR — tiene stock |
| 256 | BOLSA PAPEL CON CARGADERA 50uds 23.5 x12 x 33 SIGMAPLAST | T03.31. BOLSAS DE PAPEL | Materia prima | — | — | — | CANDIDATO ANULAR — sin stock |
| 253 | BOLSA FLEX UP 16 X 26 CON VALVULA | T03.31. BOLSAS PLASTICAS | Materia prima | 10 | 693,48 | 6934,8 | REVISAR — tiene stock |
| 254 | BOLSA PLANA FLEXIBLE15 X 20 CM CON VALVULA | T03.31. BOLSAS PLASTICAS | Materia prima | 15 | 302,81 | 4542,15 | REVISAR — tiene stock |
| 338 | BOLSA PLANA PET METALIZADA / FLEXIBLE SIN IMPRESION 16X22 EMPAQUE COBERTURA | T03.31. BOLSAS PLASTICAS | Materia prima | 4 | 318 | 1272 | REVISAR — tiene stock |
| 341 | BOLSA PLANA PET METALIZADA  FELXIBLE 16X28CM | T03.31. BOLSAS PLASTICAS | Materia prima | 50 | 405 | 20250 | REVISAR — tiene stock |
| 374 | BOLSA GRAN FORMATO 13KG EMPAQUE MAT. PRIMA | T03.31. BOLSAS PLASTICAS | Materia prima | 1 | 2566,36 | 2566,36 | REVISAR — tiene stock |
| 375 | BOLSA VERDE 35KG IMPRESA EMPAQUE MAT. PRIMA | T03.31. BOLSAS PLASTICAS | Materia prima | — | 6647 | — | CANDIDATO ANULAR — sin stock |
| 179 | Empaque mini para muestra de chocolate de mesa | T03.41. CAJAS | Materia prima | 74 | 1000 | 74000 | REVISAR — tiene stock |
| 200 | MOLDE POLICARBONATO FORMA CACAITO | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | 2 | 55000 | 110000 | NO TOCAR (catálogo permanente) |
| 202 | REJILLA COCINA | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 203 | TAPETE SILICONA | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 270 | MOLDE POLICARBONATO AMAZON FIGURAS 9 - 12g X UNIDAD | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | 19 | 55000 | 1045000 | NO TOCAR (catálogo permanente) |
| 271 | MOLDE POLICARBONATO AMAZON TABLETA  CUADRICULA X UNIDAD | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | 16 | 15000 | 240000 | NO TOCAR (catálogo permanente) |
| 408 | MOLDE POLICARBONATO AMAZON TABLETA RAYA X UNIDAD | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | 1 | 55000 | 55000 | NO TOCAR (catálogo permanente) |
| 409 | MOLDE POLICARBONATO AMAZON FIGURAS  VARIAS X UNIDAD | T05.02. A.F. MOLDES | Activo fijo (Propiedad, planta y equipo) | 4 | 55000 | 220000 | NO TOCAR (catálogo permanente) |
| 201 | ESPATULA BLANCA | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 210 | TERMOMIX | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 211 | REFINADORA CHOCOLATE PREMIER1 | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 221 | PISTOLA DE CALOR RANGER | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | — | 100840 | — | NO TOCAR (catálogo permanente) |
| 234 | Espátula Alta Temperatura 16pulg. | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | 1 | 31933 | 31933 | NO TOCAR (catálogo permanente) |
| 304 | Bowld Metálico de 32cms | T05.03. HERRAMIENTAS | Activo fijo (Propiedad, planta y equipo) | — | 18500 | — | NO TOCAR (catálogo permanente) |
| 224 | CABUYA TAMBOR X 25METROS | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 3000 | — | CANDIDATO ANULAR — sin stock |
| 257 | PLATO CANOA BAMBÚ 10CMS 25uds SIGMAPLAST | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 22400 | — | CANDIDATO ANULAR — sin stock |
| 258 | ROLLO EXTENSIBLE PLASTICO ALIMENTOS RAP 300M | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 16500 | — | CANDIDATO ANULAR — sin stock |
| 259 | TOALLA DE PAPEL PARA COCINA x 3 Rollos | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 11000 | — | CANDIDATO ANULAR — sin stock |
| 260 | PAPEL PARAFINADO ROLLO X 100M EMPAQUES Y DESECHABLES LA MAYORISTA | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 20000 | — | CANDIDATO ANULAR — sin stock |
| 280 | BATA DESECHABLE POLIPROPILENO X UNIDAD | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | 10 | 5090 | 50900 | REVISAR — tiene stock |
| 281 | GORRO DESECHABLE BLANCO X 100 UNIDADS | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | 1 | 19300 | 19300 | REVISAR — tiene stock |
| 282 | GUANTES DE NITRILO TALLA M CAJA X 50 PARES | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | 1 | 33000 | 33000 | REVISAR — tiene stock |
| 286 | Amonio Cuaternario x litro (Limpieza y desinfección) | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | 1 | 12700 | 12700 | REVISAR — tiene stock |
| 340 | VINAGRE / ACIDO ACETICO X 3 LITROS / MINORISTA (LIMPIEZA Y DESINFECCION) | T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Materia prima | — | 4800 | — | CANDIDATO ANULAR — sin stock |
| 56 | REFINADO CF CACAO 12H | T09.01. SERVICIOS MAQUILA | Servicio | — | 5000 | — | NO TOCAR (catálogo permanente) |
| 57 | REFINADO CACAO 24H | T09.01. SERVICIOS MAQUILA | Servicio | — | 7000 | — | NO TOCAR (catálogo permanente) |
| 58 | TOSTADO CF CACAO | T09.01. SERVICIOS MAQUILA | Servicio | — | 2000 | — | NO TOCAR (catálogo permanente) |
| 59 | DESCASCARILLADO CF CACAO | T09.01. SERVICIOS MAQUILA | Servicio | — | 2000 | — | NO TOCAR (catálogo permanente) |
| 94 | PROCESO MOLDEADO CHOCOLATE DE MESA | T09.01. SERVICIOS MAQUILA | Servicio | — | 3000 | — | NO TOCAR (catálogo permanente) |
| 176 | MAQUILA OBTENCION DE NIBS DE CACAO X KG | T09.01. SERVICIOS MAQUILA | Servicio | — | 4845 | — | NO TOCAR (catálogo permanente) |
| 177 | ENMOLDADO DE CHOCOLATE X KG | T09.01. SERVICIOS MAQUILA | Servicio | — | 5000 | — | NO TOCAR (catálogo permanente) |
| 117 | PROCESO EMPACADO CHOCOLATE | T09.02. SERVICIOS M.O. | Servicio | — | 800 | — | NO TOCAR (catálogo permanente) |
| 150 | MANO DE OBRA OS GENERAL | T09.02. SERVICIOS M.O. | Servicio | — | 1 | — | NO TOCAR (catálogo permanente) |
| 236 | Flete Mercadolibre | T09.06. SERVICIOS LOGISTICA | Servicio | — | 9100 | — | NO TOCAR (catálogo permanente) |
| 166 | Comision bold | T09.10. SERVICIOS GENERALES | Servicio | — | 1 | — | NO TOCAR (catálogo permanente) |
| 61 | FILTRADO APICA | T999. PRODUCTOS QUE NO SE USAN | Servicio | — | 500 | — | NO TOCAR (catálogo permanente) |
| 62 | ENVASADO APICA | T999. PRODUCTOS QUE NO SE USAN | Servicio | — | 700 | — | NO TOCAR (catálogo permanente) |
| 63 | ENVASE VIDRIO R 3590, 255 CC B.53 UNICOR | T999. PRODUCTOS QUE NO SE USAN | Materia prima | 10 | 945,4 | 9454 | REVISAR — tiene stock |
| 69 | ENVASE VIDRIO R. 4353, 400 CC, B.38 UNICOR | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 905,1 | — | CANDIDATO ANULAR — sin stock |
| 84 | ENVASE VIDRIO R. 4353, 400 CC, B.38 C Tapa UNICOR | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 1088,3 | — | CANDIDATO ANULAR — sin stock |
| 115 | AVELLANA GR | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 72 | — | CANDIDATO ANULAR — sin stock |
| 181 | Envase Vidrio R 4267 Flint, 450cc, B.89, C Tapa UNICOR | T999. PRODUCTOS QUE NO SE USAN | Materia prima | 8 | 2242 | 17936 | REVISAR — tiene stock |
| 212 | Bicarbonato x gramo | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 15 | — | CANDIDATO ANULAR — sin stock |
| 217 | PITAHAYA DESHIDRATADA X GRAMO | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 190 | — | CANDIDATO ANULAR — sin stock |
| 218 | PIÑA DESHIDRATADA X GRAMO | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 100 | — | CANDIDATO ANULAR — sin stock |
| 220 | BANANO DESHIDRATADO X GRAMO | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 137 | — | CANDIDATO ANULAR — sin stock |
| 255 | BOLSA DE PAPEL ANTIGRASA 2LB X 100UDS | T999. PRODUCTOS QUE NO SE USAN | Materia prima | — | 12353 | — | CANDIDATO ANULAR — sin stock |
| 9 | MIEL OS PLASTICO 500grs | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 10250 | — | CANDIDATO ANULAR — sin stock |
| 12 | Miel os plastico 265 grs | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 6222 | — | CANDIDATO ANULAR — sin stock |
| 361 | Miel Os Carmen degustacion 65 grs | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 1 | — | CANDIDATO ANULAR — sin stock |
| 397 | DS CREMA DE MANI DOY PACK 10X18 (ID102) | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 1 | — | CANDIDATO ANULAR — sin stock |
| 398 | CREMA DE MANI BOLSA PLANA VALVULA PERFORACION  (ID 138) | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 1 | — | CANDIDATO ANULAR — sin stock |
| 489 | Tableta Chocolate 73p 50 grs pack x 5 CPM | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto en proceso | — | 29856 | — | CANDIDATO ANULAR — sin stock |
| 499 | Tableta Chocolate 100Pgm (sin empacar) | TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto terminado | — | 5200 | — | CANDIDATO ANULAR — sin stock |
| 173 | Muestra Chocolate de mesa 2 porciones | TPT.02. VENTA OTROS | Producto en proceso | 5 | 2000 | 10000 | REVISAR — tiene stock |
| 321 | CHOCOLATE MESA GRANULADO OS BOLSA 1 KILO | TPT.02. VENTA OTROS | Producto en proceso | — | 41275 | — | CANDIDATO ANULAR — sin stock |
| 335 | DEGUSTACION DOY PACK 45gm Miel | TPT.02. VENTA OTROS | Producto en proceso | — | 3000 | — | CANDIDATO ANULAR — sin stock |
| 336 | DEGUSTACION DOY PACK 45gm Propoleo | TPT.02. VENTA OTROS | Producto en proceso | — | 3000 | — | CANDIDATO ANULAR — sin stock |
| 235 | EXHIBIDOR MEDIANO MADERA 2 NIVELES | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | — | 35000 | — | NO TOCAR (catálogo permanente) |
| 245 | EXHIBIDOR GRANDE MADERA 3 NIVELES | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | — | 60000 | — | NO TOCAR (catálogo permanente) |
| 246 | HABLADOR EN ACRILICO BASE MADERA | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | 4 | 28000 | 112000 | NO TOCAR (catálogo permanente) |
| 251 | EXHIBIDOR PEQUEÑO MADERA 1 NIVEL | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 268 | VITRINA RODAJA MADERA | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | — | — | — | NO TOCAR (catálogo permanente) |
| 391 | HABLADOR MADERA | XMATERIAL DE APOYO VENTAS POP | Activo fijo (Propiedad, planta y equipo) | — | 28000 | — | NO TOCAR (catálogo permanente) |
| 369 | DESCUENTOS | — | Servicio | — | — | — | NO TOCAR (catálogo permanente) |
| 522 | Exhibidor tableta pequeño | — | Activo fijo (Propiedad, planta y equipo) | — | 12000 | — | NO TOCAR (catálogo permanente) |
| 564 | Exhibidor Tableta Grande | — | Activo fijo (Propiedad, planta y equipo) | — | 22000 | — | NO TOCAR (catálogo permanente) |
