# espocrm-custom — Archivos custom de EspoCRM

Estos archivos se despliegan en el contenedor `espocrm` con `docker cp`.

## Estructura en el contenedor

```
/var/www/html/custom/Espo/Custom/
  Controllers/
    ImportEffi.php          ← endpoint POST /api/v1/ImportEffi/action/triggerImport
  Resources/metadata/
    clientDefs/
      Contact.json          ← override recordViews.detail → custom:views/contact/record/detail

/var/www/html/client/custom/src/
  views/contact/record/
    detail.js               ← botón "Enviar a Effi" en ficha de Contacto
```

## Deploy

```bash
# PHP Controller
docker exec espocrm sh -c "mkdir -p /var/www/html/custom/Espo/Custom/Controllers"
docker cp espocrm-custom/Espo/Custom/Controllers/ImportEffi.php espocrm:/var/www/html/custom/Espo/Custom/Controllers/

# clientDefs
docker exec espocrm sh -c "mkdir -p /var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs"
docker cp espocrm-custom/Espo/Custom/Resources/metadata/clientDefs/Contact.json espocrm:/var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs/

# JS view
docker exec espocrm sh -c "mkdir -p /var/www/html/client/custom/src/views/contact/record"
docker cp espocrm-custom/client/src/views/contact/record/detail.js espocrm:/var/www/html/client/custom/src/views/contact/record/

# Permisos y rebuild
docker exec espocrm sh -c "chown -R www-data:www-data /var/www/html/custom/Espo/Custom/Controllers/ /var/www/html/custom/Espo/Custom/Resources/metadata/clientDefs/ /var/www/html/client/custom/"
docker exec espocrm sh -c "php /var/www/html/rebuild.php"
```

## Dependencia: webhook server

El PHP controller llama a `http://172.18.0.1:5050/trigger` (Flask en el host).
Servicio systemd: `effi-webhook.service` (scripts/webhook_server.py)
