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
      Ciudad.json     ← entidad Ciudad (catálogo de ciudades)
    scopes/
      Ciudad.json     ← configuración de la entidad Ciudad
  i18n/
    es_MX/
      Contact.json    ← etiquetas en español para campos custom
      Ciudad.json     ← etiquetas para Ciudad
  layouts/
    Contact/
      detail.json     ← layout del formulario de contacto
```

**Flujo para agregar/modificar un campo custom:**
1. Modificar el JSON local (`/tmp/espo_*.json`)
2. `docker cp /tmp/archivo.json espocrm:/ruta/destino`
3. `docker exec espocrm php /var/www/html/rebuild.php`
4. `docker exec espocrm php /var/www/html/clear_cache.php`

**IMPORTANTE:** rebuild.php crea columnas nuevas en la BD pero **NO modifica tipos de columnas existentes**.

---

## Campos custom en la entidad Contact

| Campo EspoCRM | Columna BD | Tipo BD | Descripción |
|---|---|---|---|
| tipoDeMarketing | tipo_de_marketing | VARCHAR(255) | Enum dinámico (desde zeffi_tipos_marketing) |
| tipoCliente | tipo_cliente | VARCHAR(255) | Enum: Común, Fiel, Desertor, Mayorista, Importador, Industrial |
| tarifaPrecios | tarifa_precios | VARCHAR(255) | Enum dinámico (desde zeffi_tarifas_precios) |
| numeroIdentificacion | numero_identificacion | VARCHAR(100) | Número de doc |
| tipoIdentificacion | tipo_identificacion | VARCHAR(255) | Enum: Cédula, NIT, Pasaporte, Extranjería |
| tipoPersona | tipo_persona | VARCHAR(255) | Enum: Física (natural) / Jurídica (moral) |
| formaPago | forma_pago | VARCHAR(100) | Texto libre |
| vendedorEffi | vendedor_effi | VARCHAR(255) | Enum dinámico (DISTINCT vendedor de clientes + remisiones) |
| fuente | fuente | VARCHAR(255) | **"CRM"** = creado manualmente, **"Effi"** = sincronizado |
| enviadoAEffi | enviado_a_effi | TINYINT(1) | 0=pendiente exportar a Effi, 1=ya importado |
| ciudad (link) | ciudad_id | VARCHAR(17) | FK → tabla ciudad |

---

## Entidad Ciudad

Catálogo de 12,237 ciudades cargado con `bootstrap_ciudades_espocrm.py`.

```sql
-- Buscar ciudad por nombre
SELECT id, name, id_effi, departamento, pais
FROM espocrm.ciudad WHERE LOWER(name) LIKE '%bogot%' AND deleted=0;

-- Ver distribución por país
SELECT pais, COUNT(*) FROM espocrm.ciudad WHERE deleted=0 GROUP BY pais;
```

**Campos:**
- `id` — VARCHAR(17), formato EspoCRM (17 hex chars)
- `name` — nombre de la ciudad
- `id_effi` — INT UNIQUE, ID numérico en Effi (para plantilla de importación)
- `departamento` — departamento/estado/provincia
- `pais` — Colombia / Ecuador / República Dominicana / Guatemala

**NOTA:** La tabla `ciudad` NO tiene columnas `created_at` ni `modified_at`.

---

## Scripts de sincronización

### sync_espocrm_marketing.py (paso 6b)
- Lee opciones de `effi_data`: tipos_marketing, tarifas_precios, vendedores (DISTINCT)
- Compara con lo que hay en EspoCRM. Solo reconstruye si hay cambios.
- Genera JSONs → docker cp → rebuild.php
- Enums fijos hardcodeados (no consulta BD): tipoCliente, tipoIdentificacion, tipoPersona

```bash
python3 scripts/sync_espocrm_marketing.py
```

### sync_espocrm_contactos.py (paso 6c)
- Fuente: `zeffi_clientes` WHERE vigencia='Vigente'
- Upsert por `numero_identificacion`
- Setea `fuente='Effi'` en todos los contactos importados
- Resuelve nombre ciudad → `ciudad_id` (match por nombre + departamento + país)
- Maneja email y teléfonos en tablas separadas (entity_email_address, entity_phone_number)

```bash
python3 scripts/sync_espocrm_contactos.py
```

### sync_espocrm_to_hostinger.py (paso 6d)
- Lee todos los contactos no borrados de EspoCRM (con JOIN ciudad, email, teléfono)
- TRUNCATE + INSERT en `crm_contactos` en Hostinger (`u768061575_os_integracion`)
- ~480 contactos, ~30 segundos

```bash
python3 scripts/sync_espocrm_to_hostinger.py
```

### generar_plantilla_import_effi.py (paso 7)
- Lee contactos con `fuente='CRM'` y `enviado_a_effi=0`
- Genera XLSX de 36 columnas (formato plantilla importación Effi)
- Mapeos de IDs numéricos para Effi:
  - tipo_identificacion → TIPO_ID_MAP (hardcoded)
  - ciudad → id_effi via tabla ciudad
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

### bootstrap_ciudades_espocrm.py (ejecución única)
Ya fue ejecutado. Crea Ciudad entity + carga las 12,237 ciudades.
**NO volver a ejecutar** sin limpiar la tabla ciudad primero.

---

## Queries de diagnóstico

```bash
# Contactos pendientes de importar a Effi
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT first_name, last_name, numero_identificacion, tipo_de_marketing, ciudad_id
FROM contact WHERE fuente='CRM' AND (enviado_a_effi=0 OR enviado_a_effi IS NULL) AND deleted=0;" 2>/dev/null

# Distribución fuente / enviado_a_effi
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT fuente, enviado_a_effi, COUNT(*) n FROM contact WHERE deleted=0 GROUP BY 1,2 ORDER BY 1,2;" 2>/dev/null

# Contactos sin ciudad asignada
mysql -u osadmin -pEpict2487. espocrm -e "
SELECT COUNT(*) FROM contact WHERE deleted=0 AND ciudad_id IS NULL;" 2>/dev/null

# Verificar que rebuild creó las columnas custom
mysql -u osadmin -pEpist2487. espocrm -e "
SHOW COLUMNS FROM contact LIKE '%effi%';" 2>/dev/null
```

---

## Mismatch tipo_de_marketing (gotcha conocido)

Los contactos sincronizados desde Effi (fuente='Effi') pueden tener valores de `tipo_de_marketing` que no coinciden con los nombres actuales en `zeffi_tipos_marketing`. Esto es porque Effi puede renombrar los tipos sin que los registros históricos se actualicen.

**Solo afecta** a contactos fuente='Effi' al generar la plantilla (lookup devuelve None).
**No afecta** a contactos fuente='CRM' — estos usan el dropdown actualizado del pipeline.

---

## Flujo completo EspoCRM → Effi

```
Vendedor crea contacto en EspoCRM
  ↓ (fuente='CRM', enviado_a_effi=0 automáticos)
python3 scripts/generar_plantilla_import_effi.py
  ↓ genera /tmp/import_clientes_effi_<hoy>.xlsx
Subir XLSX a Effi (manual: Configuración → Importar clientes)
  ↓ verificar que los registros aparecen en Effi
  ↓ contacto marcado enviado_a_effi=1
En próxima corrida del pipeline:
  sync_espocrm_contactos.py → el contacto vuelve como fuente='Effi' (si Effi lo devuelve)
```
