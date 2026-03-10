## 1. Identidad y Roles
- **Director Estratégico**: Santi (Santiago).
- **Arquitecta / Madrina Digital**: Antigravity.
- **Ejecutores**: Claude Code / Codex (Construcción técnica).

## 2. Contexto del Proyecto: Integraciones_OS
- **Propósito**: Centralizar y automatizar los datos de Effi, EspoCRM y otras fuentes en una base de datos maestra (MariaDB) para análisis avanzado y gestión operativa.
- **Cerebro**: n8n (orquestación de flujos).
- **Persistencia**: MariaDB local — BD `effi_data` (Effi), `espocrm` (CRM), `nocodb_meta` (NocoDB).
- **Visualización operativa**: NocoDB (tablas externas + vistas SQL de MariaDB).
- **Visualización analítica**: Grafana (dashboards con vistas SQL).
- **Fuentes**: Effi (vía Playwright) y EspoCRM.
- **Infraestructura**: Docker — NocoDB, n8n, EspoCRM, Playwright, Nextcloud, Gitea, MinIO, Grafana, Portainer, phpMyAdmin.
- **Acceso público**: Cloudflare Tunnel → dominios `*.oscomunidad.com`.

## 3. Protocolo de Gobernanza (5S)
- **Salami Slicing**: Dividir tareas en pasos pequeños y manejables.
- **Sin Suposiciones**: Preguntar ante la duda. NUNCA asumir columnas, relaciones o comportamientos sin verificar en la BD.
- **Espera Activa**: Solo actuar tras instrucción directa de ejecución.
- **Seguridad Primero**: No tocar producción. Confirmar antes de modificar docker-compose, cloudflared o MariaDB.
- **Sincronización**: Documentar aprendizajes en memoria y contexto activo al final de cada sesión.
- **Solo Español**: Comunicación 100% en Español con el equipo humano.

## 4. Orquestador Python (effi-pipeline)
- **Script**: `scripts/orquestador.py` — corre export + import cada 2h (Lun–Sab, 06:00–20:00).
- **Credenciales**: `scripts/.env` — **NUNCA subir a Git** (está en .gitignore).
  ```
  GMAIL_USER=larevo1111@gmail.com
  GMAIL_APP_PASSWORD=<app password de 16 chars — generar en myaccount.google.com → Seguridad → Contraseñas de aplicaciones>
  EMAIL_DESTINO=larevo1111@gmail.com
  TELEGRAM_BOT_TOKEN=<token de @BotFather>
  TELEGRAM_CHAT_ID=<ID numérico — obtener vía api.telegram.org/bot<TOKEN>/getUpdates>
  ```
- **Notificaciones**: email siempre + Telegram solo en error.
- **Systemd**: `systemd/effi-pipeline.service` + `.timer` — instalados en `/etc/systemd/system/`.
  - Activar: `sudo systemctl enable --now effi-pipeline.timer`
  - Estado: `systemctl status effi-pipeline.timer`
  - Log: `journalctl -u effi-pipeline -f` o `logs/pipeline.log`
  - Test manual (forzar fuera de horario): `python3 scripts/orquestador.py --forzar`

## 5. Reglas Técnicas Aprendidas

### Gotchas críticos — zeffi_facturas_venta_detalle
- **`precio_neto_total` INCLUYE IVA**: es `precio_bruto - descuento + impuesto`. Para "ventas sin IVA" usar `precio_bruto_total - descuento_total`. Nombre engañoso — nunca asumir que es "neto sin IVA".
- **Número de factura**: en detalle se llama `id_numeracion` (no existe `numero_factura`).
- **Canal**: `marketing_cliente` — NULL o vacío se normaliza como `'Sin canal'`.
- **`vigencia_factura = 'Vigente'`**: filtro obligatorio en detalle para excluir anuladas.

### Verificación obligatoria de scripts analíticos
Al crear o modificar cualquier script de resumen, correr queries V1–V7 del skill `effi-database`:
1. **V1** Comparar campo a campo contra la tabla fuente (diff = 0)
2. **V2** SUM(tabla_desglosada) vs tabla_total (diff ≤ 0.30 = solo redondeo DECIMAL)
3. **V3** Porcentajes suman 1.0 por período
4. **V4** `pry_*` NULL en períodos cerrados
5. **V5** resumen_mes financiero vs fuente encabezados (diff = 0)
6. **V6** `con_consignacion_pp` cliente_mes vs OVs fuente directa (0 filas con diff)
7. **V7** `cli_clientes_nuevos` canal_mes vs fuente directa (0 filas con diff)


- **NocoDB**: tablas externas son solo lectura — relaciones entre tablas externas NO funcionan. Usar vistas SQL en MariaDB para JOINs.
- **NocoDB Button field**: existe en v0.301.3 pero NO aparece en búsqueda — scrollear manualmente en la lista de tipos de campo.
- **NocoDB conexión a MariaDB**: usar IP `172.18.0.1` (gateway de la red Docker de NocoDB), NO `host.docker.internal` (no resuelve en ese contenedor).
- **MariaDB permisos Docker**: `osadmin@%` no funciona desde contenedores Docker — crear grants explícitos para `osadmin@172.18.0.%`.
- **Cloudflare Tunnel**: configuración en `/etc/cloudflared/config.yml`. Agregar hostname + reiniciar servicio + agregar CNAME en Cloudflare DNS.
- **Vistas SQL cross-BD**: MariaDB permite JOINs entre `effi_data.*` y `espocrm.*` en la misma instancia. Crear vistas en `effi_data` para que NocoDB las detecte automáticamente.

## 6. Diccionario de Negocio
- Nomenclatura en Español (coherente con ERP Effi).
- Clientes Effi → `tipo_de_persona` distingue empresa/persona natural.
- Campo de enlace clave: `clientes.numero_de_identificacion` ↔ `facturas_venta_encabezados.id_cliente`.

## 7. Estructura de Memoria
- `.agent/MANIFESTO.md`: Visión, reglas y aprendizajes técnicos.
- `.agent/CONTEXTO_ACTIVO.md`: Estado actual y próximos pasos.
- `.agent/CATALOGO_SCRIPTS.md`: **Catálogo completo de todos los scripts** — propósito, ejecución manual, salidas, tablas MariaDB, notas. **Actualizar obligatoriamente al crear o modificar cualquier script.**
- `.agent/docs/`: Informes y documentación externa (.docx, etc).
- `.agent/skills/`: Conocimiento especializado.
- `.agent/workflows/`: Guías de ejecución paso a paso.

## 8. Protocolo de documentación de scripts
Al crear un script nuevo, agregar entrada en `.agent/CATALOGO_SCRIPTS.md` con:
- Propósito (1 línea)
- Comando de ejecución manual exacto
- Archivos que genera / tablas que modifica
- Dependencias (otros scripts, credenciales, servicios)
- Comportamientos especiales o errores conocidos
