# Contexto: EspoCRM — Integración
**Actualizado**: 2026-03-23

## Infraestructura

| Recurso | Detalle |
|---|---|
| URL | crm.oscomunidad.com |
| Contenedor | `espocrm` — puerto 8083 |
| BD | `espocrm` en MariaDB local |
| Skill completa | `/espocrm-integracion` |

## Estado actual

- 488 contactos: 362 Cliente directo, 106 Negocio amigo, 13 Interno, 7 Red de amigos
- Integración bidireccional completamente automatizada
- Botón "Enviar a Effi" activo en ficha de Contacto

## Campos custom en Contact

| Campo | Tipo | Descripción |
|---|---|---|
| `tipoDeMarketing` | enum | Canal de marketing |
| `tipoCliente` | enum | Negocio amigo, Red de amigos, Cliente directo, Interno, Otro |
| `calificacionNegocioAmigo` | enum A/B/C | Solo visible cuando tipoCliente='Negocio amigo' (dynamicLogic) |
| `tarifaPrecios` | enum | Tarifa asignada |
| `numeroIdentificacion` | varchar | Número de documento |
| `tipoIdentificacion` | varchar | Tipo de documento |
| `tipoPersona` | varchar | Natural/Jurídica |
| `formaPago` | varchar | |
| `vendedorEffi` | enum | Vendedor en Effi |
| `fuente` | enum CRM/Effi | readOnly — no editable por usuario |
| `enviadoAEffi` | bool | Si fue importado a Effi |
| `ciudadNombre` | enum | Formato "Ciudad - Departamento" (sistema dinámico) |
| `direccion` | varchar | Dirección línea 1 (campo custom) |
| `direccionLinea2` | varchar | Dirección línea 2 (campo custom) |

**Los campos nativos `address_street/city/state/country` ya NO se usan (deprecados).**

## Reglas críticas

- **`tipoCliente` NO se sincroniza desde Effi** — se gestiona manualmente en EspoCRM. A Effi siempre se manda `tipo_cliente=1` (Común)
- **`fuente`** es readOnly — se asigna automáticamente (CRM = creado en EspoCRM, Effi = importado desde Effi)
- `enviadoAEffi=1` se marca en el paso 7a (antes de subir), no en el 7b

## Sistema de Municipios (ciudadNombre)

- Enum dinámico generado desde `codigos_ciudades_dane` (en effi_data)
- Formato: "Ciudad - Departamento" (ej: "Medellín - Antioquia")
- Script `sync_espocrm_marketing.py` sincroniza el enum desde la BD

### Normalización y aliases

El script traduce ciudad Effi → display con normalización:
- Sin tildes
- Sin puntuación
- Aliases hardcoded: Cali → Santiago De Cali, Cartagena → Cartagena De Indias

### Flujo circular sin pérdida de datos

EspoCRM "Medellín - Antioquia" → exporta como DANE 05001 → Effi → export "Medellín" + "Antioquia" → script resuelve de vuelta "Medellín - Antioquia"

## Entidad Ciudad (DEPRECADA)

- 12,237 ciudades (Colombia, Ecuador, Rep.Dom, Guatemala) desde plantilla_importacion_cliente.xlsx
- Tabla: `ciudad` (id VARCHAR(17), name, id_effi INT UNIQUE, departamento, pais)
- SIN created_at/modified_at (a diferencia de otras entidades)
- **Ya NO se usa para Contact** — reemplazada por enum `ciudadNombre`

## EspoCRM gotchas técnicos

- `Rebuild.php` crea columnas pero NO modifica tipos existentes
- Enums se almacenan como VARCHAR(255) en BD aunque entityDefs diga enum
- `sync_espocrm_marketing.py` compara solo marketing/tarifas/vendedores para detectar cambios (no detecta campos nuevos automáticamente)
- Mismatch marketing: `zeffi_clientes` puede tener nombres distintos a `zeffi_tipos_marketing` (renombrados en Effi). Solo afecta contactos `fuente='Effi'`

## Clasificación inicial de contactos (2026-03-11)

Script `clasificar_contactos.py` disponible para reclasificar (usar `--dry-run` para preview).
- 362 → Cliente directo
- 106 → Negocio amigo (calificación B inicial)
- 13 → Interno
- 7 → Red de amigos

## Flujo EspoCRM → Effi (bidireccional automatizado)

### Pasos del pipeline

1. Vendedor crea contacto en EspoCRM (`fuente='CRM'` automático, `enviado_a_effi=0`)
2. **Paso 7a** — `generar_plantilla_import_effi.py`: genera `/tmp/import_clientes_effi_<fecha>.xlsx` con contactos `fuente='CRM'` y `enviado_a_effi=0`
3. **Paso 7b** — `import_clientes_effi.js` (Playwright): sube el XLSX a Effi
   - URL: `https://effi.com.co/app/tercero/cliente`
   - Modal: "Crear o modificar clientes masivamente"
   - Selector file: `#modalImportarCrearMasivo input[type="file"]`
   - Selector submit: `#modalImportarCrearMasivo #btn_submit`
4. Contacto queda marcado `enviado_a_effi=1`

### Flujo Effi → EspoCRM

- **Paso 6c** — `sync_espocrm_contactos.py`: upsert clientes Effi → EspoCRM Contact (`fuente='Effi'`)
- Traduce ciudad Effi → formato "Ciudad - Departamento" con normalización + aliases

## Botón "Enviar a Effi" (activo)

Botón verde en ficha de Contacto (detail view) → dispara pasos 7a+7b a demanda.

### Arquitectura del botón

```
Botón JS en EspoCRM (detail view)
  → POST /api/v1/ImportEffi/action/triggerImport (PHP custom)
  → Flask 172.18.0.1:5050
  → scripts 7a + 7b
```

| Componente | Detalle |
|---|---|
| Flask server | `scripts/webhook_server.py`, puerto 5050 |
| Systemd | `effi-webhook.service` (activo, auto-restart) |
| Archivos versionados | `espocrm-custom/` con instrucciones de deploy |
| Deploy | `docker cp` + `php rebuild.php` |

### Routing custom de EspoCRM

`/:controller/action/:action` (NO `/:controller/:action`)

## Sync EspoCRM → Hostinger (paso 6d)

- Script: `sync_espocrm_to_hostinger.py`
- Tabla destino: `crm_contactos` en `u768061575_os_integracion` (Hostinger)
- Estrategia: DROP + CREATE + INSERT
- Usa campos custom (`direccion`, `ciudad_nombre`), NO los nativos `address_*`
- 480+ contactos sincronizados

## Archivos clave

| Archivo | Propósito |
|---|---|
| `scripts/sync_espocrm_contactos.py` | Effi → EspoCRM (paso 6c) |
| `scripts/sync_espocrm_marketing.py` | Enums dinámicos en EspoCRM (paso 6b) |
| `scripts/sync_espocrm_to_hostinger.py` | EspoCRM → Hostinger crm_contactos (paso 6d) |
| `scripts/generar_plantilla_import_effi.py` | CRM → XLSX (paso 7a) |
| `scripts/import_clientes_effi.js` | Playwright sube XLSX a Effi (paso 7b) |
| `scripts/webhook_server.py` | Flask API puerto 5050 para botón Enviar a Effi |
| `scripts/clasificar_contactos.py` | Reclasificación masiva de contactos |
| `espocrm-custom/` | Archivos PHP/JS versionados del botón |
