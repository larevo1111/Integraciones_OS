# espocrm-custom — Archivos custom de EspoCRM

Estos archivos se despliegan en el contenedor `espocrm` con `docker cp`.

## Estructura en el contenedor

```
/var/www/html/custom/Espo/Custom/
  Controllers/
    ImportEffi.php          ← endpoint POST /api/v1/ImportEffi/action/triggerImport (solo 7a+7b)
    SyncEffi.php            ← endpoint POST /api/v1/SyncEffi/action/triggerSync (6c+6d+7a+7b bidireccional)
  Resources/metadata/
    clientDefs/
      Contact.json          ← override detail view + list view custom

/var/www/html/client/custom/src/
  views/contact/
    list.js                 ← botón "Sincronizar con Effi" en vista de lista de Contactos
    record/
      detail.js             ← botón "Enviar a Effi" en ficha de Contacto (solo CRM→Effi)
```

## Botones disponibles

| Botón | Dónde | Qué hace |
|---|---|---|
| "Sincronizar con Effi" | Lista de Contactos (header) | Sync bidireccional: Effi→CRM (6c) + CRM→Hostinger (6d) + CRM→Effi (7a+7b) |
| "Enviar a Effi" | Ficha de un contacto (detail) | Solo envía pendientes CRM→Effi (7a+7b) |

## Deploy completo

```bash
PROJ=/home/osserver/Proyectos_Antigravity/Integraciones_OS

# PHP Controllers
docker exec espocrm sh -c "mkdir -p /var/www/html/custom/Espo/Custom/Controllers"
docker cp $PROJ/espocrm-custom/Espo/Custom/Controllers/ImportEffi.php espocrm:/var/www/html/custom/Espo/Custom/Controllers/
docker cp $PROJ/espocrm-custom/Espo/Custom/Controllers/SyncEffi.php espocrm:/var/www/html/custom/Espo/Custom/Controllers/

# clientDefs
docker exec espocrm sh -c "mkdir -p /var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs"
docker cp $PROJ/espocrm-custom/Espo/Custom/Resources/metadata/clientDefs/Contact.json espocrm:/var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs/

# JS views
docker exec espocrm sh -c "mkdir -p /var/www/html/client/custom/src/views/contact/record"
docker cp $PROJ/espocrm-custom/client/src/views/contact/list.js espocrm:/var/www/html/client/custom/src/views/contact/
docker cp $PROJ/espocrm-custom/client/src/views/contact/record/detail.js espocrm:/var/www/html/client/custom/src/views/contact/record/

# Permisos y rebuild
docker exec espocrm sh -c "chown -R www-data:www-data /var/www/html/custom/Espo/Custom/Controllers/ /var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs/ /var/www/html/client/custom/"
docker exec espocrm sh -c "php /var/www/html/rebuild.php"
```

## Dependencia: webhook server

Flask en el host en `0.0.0.0:5050`, accesible desde Docker vía `172.18.0.1:5050`.

| Endpoint | Usado por | Acción |
|---|---|---|
| POST /trigger | ImportEffi.php | Solo 7a+7b (CRM→Effi) |
| POST /trigger-sync | SyncEffi.php | 6c+6d+7a+7b (bidireccional) |
| GET /status | — | Estado del último proceso |
| GET /health | — | Health check |

Servicio systemd: `effi-webhook.service` (`scripts/webhook_server.py`)
