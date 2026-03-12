# Skill: EspoCRM — Integración Bidireccional con Effi

Guía técnica para trabajar con EspoCRM en el contexto de la integración Integraciones_OS.

---

## Acceso y credenciales

| Parámetro | Valor |
|---|---|
| URL | https://crm.oscomunidad.com |
| Contenedor Docker | `espocrm` |
| BD MariaDB | `espocrm` en localhost:3306 |
| Usuario MariaDB | `osadmin` / `Epist2487.` |
| Archivos custom | dentro del contenedor: `/var/www/html/custom/Espo/Custom/Resources/` |

```bash
# Ver logs del contenedor
docker logs espocrm --tail 50

# Ejecutar comando dentro del contenedor
docker exec espocrm php /var/www/html/rebuild.php
docker exec espocrm php /var/www/html/clear_cache.php

# Leer un JSON de metadata desde el contenedor
docker exec espocrm cat /var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/Contact.json
```

---

## Estructura de archivos custom en EspoCRM

```
/var/www/html/custom/Espo/Custom/Resources/
  metadata/
    entityDefs/
      Contact.json    ← campos custom de Contact
    clientDefs/
      Contact.json    ← botones custom, handlers, menu
  i18n/
    es_MX/
      Contact.json    ← etiquetas en español para campos custom
  layouts/
    Contact/
      detail.json     ← layout del formulario de contacto (list, detail, edit)
```

**Flujo para agregar/modificar un campo custom:**
1. Modificar el JSON local (`/tmp/espo_*.json`)
2. `docker cp /tmp/archivo.json espocrm:/ruta/destino`
3. `docker exec espocrm php /var/www/html/rebuild.php`
4. `docker exec espocrm php /var/www/html/clear_cache.php`

**IMPORTANTE:** rebuild.php crea columnas nuevas en la BD pero **NO modifica tipos de columnas existentes**.

---

## Campos custom en la entidad Contact

### Campos activos (en el layout)

| Campo EspoCRM | Columna BD | Tipo | Descripción |
|---|---|---|---|
| firstName | first_name | VARCHAR(100) | Nombre (nativo, separado de name compuesto) |
| lastName | last_name | VARCHAR(100) | Apellido (nativo, separado de name compuesto) |
| tipoDeMarketing | tipo_de_marketing | VARCHAR(255) | Enum dinámico (desde zeffi_tipos_marketing) |
| tipoCliente | tipo_cliente | VARCHAR(255) | Enum: Común, Fiel, Desertor, Mayorista, Importador, Industrial |
| numeroIdentificacion | numero_identificacion | VARCHAR(100) | Número de documento |
| tipoIdentificacion | tipo_identificacion | VARCHAR(255) | Enum: Cédula, NIT, Pasaporte, Extranjería |
| tipoPersona | tipo_persona | VARCHAR(255) | Enum: Física (natural) / Jurídica (moral) |
| vendedorEffi | vendedor_effi | VARCHAR(255) | Enum dinámico (DISTINCT vendedor de clientes + remisiones) |
| tarifaPrecios | tarifa_precios | VARCHAR(255) | Enum dinámico (desde zeffi_tarifas_precios) |
| formaPago | forma_pago | VARCHAR(255) | Enum: Contraentrega, Contado, 15/30/45/60 días |
| ciudadNombre | ciudad_nombre | VARCHAR(200) | **Enum dinámico**: formato "Municipio - Departamento" (desde codigos_ciudades_dane) |
| direccion | direccion | VARCHAR(255) | Dirección principal (campo custom, NO el nativo address) |
| direccionLinea2 | direccion_linea2 | VARCHAR(255) | Referencia / Línea 2 de dirección |
| fuente | fuente | VARCHAR(255) | **"CRM"** = creado manualmente, **"Effi"** = sincronizado |
| enviadoAEffi | enviado_a_effi | TINYINT(1) | 0=pendiente exportar a Effi, 1=ya importado |

### Campos nativos desactivados / no usados

| Campo | Estado | Notas |
|---|---|---|
| `name` (compuesto) | Reemplazado por firstName + lastName | El compuesto incluye salutationName (Sr/Sra) que no se quiere |
| `address` (compuesto) | **NO USAR** | Reemplazado por campos custom `direccion` + `direccionLinea2` |
| `address_street/city/state/country` | **NO USAR** | Subcampos del address nativo, ya no se populan |
| `salutationName` | No visible | Al no usar `name` compuesto, no aparece |
| `ciudad_id` (link → Ciudad) | **DEPRECADO** | Se usaba antes; ahora se usa `ciudadNombre` (enum con display) |

### Layout del formulario (detail.json)

```json
[
  { "label": "", "rows": [
    [{"name": "firstName"},              {"name": "lastName"}],
    [{"name": "emailAddress"},           {"name": "phoneNumber"}],
    [{"name": "tipoDeMarketing"},        {"name": "tipoCliente"}],
    [{"name": "numeroIdentificacion"},   {"name": "tipoIdentificacion"}],
    [{"name": "tipoPersona"},            {"name": "vendedorEffi"}],
    [{"name": "tarifaPrecios"},          {"name": "formaPago"}],
    [{"name": "ciudadNombre"},             false],
    [{"name": "direccion"},              {"name": "direccionLinea2"}],
    [{"name": "fuente"},                 {"name": "enviadoAEffi"}],
    [{"name": "description", "fullWidth": true}]
  ]}
]
```

---

## Sistema de municipios (ciudadNombre)

### Cómo funciona

- **En EspoCRM**: campo enum `ciudadNombre` con ~1,100 opciones en formato "Municipio - Departamento"
- **Fuente de datos**: tabla `codigos_ciudades_dane` en `effi_data` (NO en espocrm)
- **Ejemplo**: "Medellín - Antioquia", "Bogotá, D.C. - Bogotá, D.C.", "Santiago De Cali - Valle Del Cauca"
- **Sync marketing** (`sync_espocrm_marketing.py`): lee `codigos_ciudades_dane.nombre_display` → actualiza opciones del enum
- **Sync contactos** (`sync_espocrm_contactos.py`): traduce `zeffi_clientes.ciudad` al formato display usando normalización + alias

### Tabla codigos_ciudades_dane (effi_data)

```sql
-- Estructura
codigo_municipio VARCHAR(5) PK    -- Código DANE (ej: '05001')
nombre_municipio VARCHAR(200)     -- Nombre oficial (ej: 'Medellín')
codigo_departamento VARCHAR(2)    -- Código depto (ej: '05')
nombre_departamento VARCHAR(100)  -- Nombre depto (ej: 'Antioquia')
nombre_display VARCHAR(150)       -- 'Medellín - Antioquia' (lo que se muestra en EspoCRM)
```

### Flujo circular de ciudades (NO se daña al ir y volver)

```
EspoCRM: ciudad_nombre = "Medellín - Antioquia"
  ↓ generar_plantilla_import_effi.py busca en codigos_ciudades_dane
  ↓ nombre_display "Medellín - Antioquia" → codigo_municipio "05001"
XLSX para Effi: columna "Código DANE Ciudad" = 05001
  ↓ Effi recibe el código numérico
  ↓ Effi guarda internamente el nombre
Effi exporta: zeffi_clientes.ciudad = "Medellín", .departamento = "Antioquia"
  ↓ sync_espocrm_contactos.py traduce de vuelta
  ↓ ("Medellín", "Antioquia") → normalización → "Medellín - Antioquia"
EspoCRM: ciudad_nombre = "Medellín - Antioquia" ← mismo valor, sin pérdida
```

**El valor en EspoCRM NUNCA se sobreescribe con solo "Medellín"** — siempre pasa por el traductor.

### Matching Effi → display (sync_espocrm_contactos.py)

El matching es robusto:
1. Normaliza texto: quita tildes, puntuación, minúsculas
2. Aplica alias comunes: "Cali" → "Santiago de Cali", "Cartagena" → "Cartagena de Indias"
3. Busca por (municipio, departamento) normalizado
4. Si no hay match por dupla, busca solo por municipio (si no es ambiguo)
5. Caso especial Bogotá (variantes: "Bogotá D.C.", "Bogotá")

**Alias actuales** (en `ALIAS_CIUDADES`):
- cali → santiago de cali
- cartagena → cartagena de indias
- cartagena de indias distrito turistico y cultural → cartagena de indias

**Ciudades sin match** (no existen en DANE como municipio):
- "Aguas Claras" (vereda de Antioquia) → queda vacío en EspoCRM

---

## Scripts de sincronización

### sync_espocrm_marketing.py (paso 6b)
- Lee opciones dinámicas de `effi_data`: tipos_marketing, tarifas_precios, vendedores, **municipios**
- Compara con lo que hay en EspoCRM. Solo reconstruye si hay cambios.
- Genera JSONs (entityDefs, i18n, layout) → docker cp → rebuild.php
- Enums fijos hardcodeados: tipoCliente, tipoIdentificacion, tipoPersona, formaPago

```bash
python3 scripts/sync_espocrm_marketing.py
```

### sync_espocrm_contactos.py (paso 6c)
- Fuente: `zeffi_clientes` WHERE vigencia='Vigente'
- Upsert por `numero_identificacion`
- Setea `fuente='Effi'` en todos los contactos importados
- **Municipio**: traduce ciudad de Effi → formato "Ciudad - Departamento" (con normalización y alias)
- **Dirección**: escribe en campo custom `direccion` (NO en address_street nativo)
- Maneja email y teléfonos en tablas separadas (entity_email_address, entity_phone_number)

```bash
python3 scripts/sync_espocrm_contactos.py
```

### sync_espocrm_to_hostinger.py (paso 6d)
- Lee todos los contactos no borrados de EspoCRM (con email y teléfono primarios)
- DROP + CREATE + INSERT en `crm_contactos` en Hostinger (`u768061575_os_integracion`)
- Campos: id, nombre_completo, direccion, direccion_linea2, ciudad_nombre, etc.
- **Ya NO usa** campos nativos address_street/city/state/country ni JOIN a tabla ciudad

```bash
python3 scripts/sync_espocrm_to_hostinger.py
```

### generar_plantilla_import_effi.py (paso 7a)
- Lee contactos con `fuente='CRM'` y `enviado_a_effi=0`
- Genera XLSX de 36 columnas (formato plantilla importación Effi)
- **Ciudad**: lee `ciudad_nombre` (ej: "Medellín - Antioquia") → busca código DANE en `codigos_ciudades_dane.nombre_display`
- **Dirección**: concatena `direccion` + `direccion_linea2` en un solo campo para Effi
- Mapeos de IDs numéricos:
  - tipo_identificacion → TIPO_ID_MAP (hardcoded)
  - ciudad → código DANE via `codigos_ciudades_dane`
  - tarifa → id via zeffi_tarifas_precios
  - marketing → id via zeffi_tipos_marketing
  - tipo_persona → 1 (Física) / 2 (Jurídica)
  - regimen_tributario → 5 (natural) / 4 (jurídica)
  - email_responsable = 'equipo.origensilvestre@gmail.com' (fijo)
  - sucursal=1, moneda=COP, permitir_venta=1
- Tras generar, marca `enviado_a_effi=1`

```bash
python3 scripts/generar_plantilla_import_effi.py           # solo pendientes
python3 scripts/generar_plantilla_import_effi.py --todos    # todos los CRM
python3 scripts/generar_plantilla_import_effi.py --no-marcar  # sin marcar
```
Salida: `/tmp/import_clientes_effi_YYYY-MM-DD.xlsx`

### import_clientes_effi.js (paso 7b — Playwright)
- Navega a https://effi.com.co/app/tercero/cliente
- Click "Crear o modificar clientes masivamente"
- Sube XLSX via `#modalImportarCrearMasivo input[type="file"]`
- Submit via `#modalImportarCrearMasivo #btn_submit`

---

## Botón "Enviar a Effi" (detail view)

Botón en la ficha de cada Contact para disparar la importación manual a Effi.

**Flujo:**
```
JS (client) → POST /api/v1/ImportEffi/action/triggerImport
  → PHP Controller (ImportEffi)
    → HTTP POST a Flask 172.18.0.1:5050/trigger-import
      → Flask (webhook_server.py) ejecuta paso 7a + 7b
```

**Componentes:**
- JS handler: `espocrm-custom/client/custom/src/handlers/import-effi-handler.js`
- PHP controller: `espocrm-custom/custom/Espo/Custom/Controllers/ImportEffi.php`
- Flask webhook: `scripts/webhook_server.py` (puerto 5050, systemd `effi-webhook.service`)
- Deploy: `docker cp espocrm-custom/... espocrm:/var/www/html/...` + `php rebuild.php`

**EspoCRM routing custom:** `/:controller/action/:action` (NO `/:controller/:action`)

---

## Gotchas y problemas conocidos

### 1. Campos compuestos (name, address)
- **NO sobreescribir vistas** (`recordViews.detail` / `.edit`) — es extremadamente frágil y rompe create/detail
- La solución correcta para ocultar subcampos: **usar los subcampos individuales en el layout** en vez del campo compuesto
- `name` → `firstName` + `lastName` (elimina salutationName)
- `address` → reemplazado por campos custom `direccion` + `direccionLinea2`

### 2. rebuild.php
- Crea columnas nuevas pero **NO modifica tipos de columnas existentes**
- Si necesitas cambiar un tipo de columna: ALTER TABLE manual en la BD

### 3. Enums almacenados como VARCHAR
- Los enums se almacenan como VARCHAR(255) en la BD aunque entityDefs diga `type: enum`
- El valor guardado es el texto del option, no un ID numérico

### 4. Dynamic Logic limitado
- Soporta mostrar/ocultar campos y hacerlos required según condiciones
- **NO soporta filtrar opciones de un enum según otro enum** (no hay cascading nativo)
- Por eso se usa formato "Municipio - Departamento" en vez de 2 dropdowns separados

### 5. id_cliente en facturas tiene prefijo tipo doc
- `zeffi_facturas_venta_detalle.id_cliente` = "CC 74084937" o "NIT 900982270"
- `zeffi_clientes.numero_de_identificacion` = "74084937" (solo el número)
- Para hacer JOIN: usar `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`
- El script `calcular_resumen_ventas_canal.py` NO tiene este problema (usa `marketing_cliente` del detalle)

### 6. Mismatch tipo_de_marketing
- Los contactos fuente='Effi' pueden tener valores de tipo_de_marketing que no coinciden con `zeffi_tipos_marketing` (porque Effi renombra tipos)
- Solo afecta fuente='Effi' al generar plantilla (lookup devuelve None)
- No afecta fuente='CRM'

### 6. Tabla ciudad (DEPRECADA para municipios)
- 12,237 ciudades cargadas con `bootstrap_ciudades_espocrm.py`
- Ahora se usa `codigos_ciudades_dane` + campo enum `ciudadNombre` en vez del link a ciudad
- La tabla ciudad sigue existiendo pero ya no se consulta activamente

---

## Queries de diagnóstico

```bash
# Contactos pendientes de importar a Effi
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT first_name, last_name, numero_identificacion, ciudad_nombre
FROM contact WHERE fuente='CRM' AND (enviado_a_effi=0 OR enviado_a_effi IS NULL) AND deleted=0;" 2>/dev/null

# Distribución fuente / enviado_a_effi
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT fuente, enviado_a_effi, COUNT(*) n FROM contact WHERE deleted=0 GROUP BY 1,2 ORDER BY 1,2;" 2>/dev/null

# Contactos sin municipio asignado
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT COUNT(*) FROM contact WHERE deleted=0 AND (ciudad_nombre IS NULL OR ciudad_nombre='');" 2>/dev/null

# Verificar que rebuild creó las columnas custom
mysql -u osadmin -pEpist2487. espocrm -e "
SHOW COLUMNS FROM contact WHERE Field IN ('direccion','direccion_linea2','ciudad_nombre','tipo_de_marketing');" 2>/dev/null

# Ver opciones actuales de ciudadNombre (entityDefs en contenedor)
docker exec espocrm cat /var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/Contact.json | python3 -c "
import sys,json; d=json.load(sys.stdin); print(len(d['fields']['ciudadNombre']['options']), 'municipios')"
```

---

## Flujo completo EspoCRM → Effi

```
Vendedor crea contacto en EspoCRM
  ↓ (fuente='CRM', enviado_a_effi=0 automáticos)
  ↓ selecciona municipio como "Medellín - Antioquia"
  ↓ ingresa dirección en campo custom "direccion"
Pipeline paso 7a: generar_plantilla_import_effi.py
  ↓ lee ciudad_nombre → busca código DANE en codigos_ciudades_dane
  ↓ concatena direccion + direccion_linea2 para columna "Dirección" del XLSX
  ↓ genera /tmp/import_clientes_effi_<hoy>.xlsx
  ↓ marca enviado_a_effi=1
Pipeline paso 7b: import_clientes_effi.js (Playwright — automático)
  ↓ sube XLSX a Effi vía Playwright
  ↓ contactos aparecen en Effi como Vigentes
En próxima corrida del pipeline:
  sync_espocrm_contactos.py → el contacto vuelve como fuente='Effi'
  ↓ traduce ciudad de Effi ("Medellín") → "Medellín - Antioquia" (normalización + alias)
```

**Para borrar contactos de prueba (bandera TEST_PIPELINE_DELETE):**
```sql
UPDATE contact SET deleted=1 WHERE description='TEST_PIPELINE_DELETE';
```
