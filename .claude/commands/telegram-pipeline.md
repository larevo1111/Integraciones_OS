# Skill: Telegram Bot — Pipeline Effi

Referencia para entender, mantener y modificar las notificaciones Telegram del pipeline Effi → MariaDB.

---

## Configuración

Las credenciales viven en `scripts/.env` (no commiteado):

```env
TELEGRAM_BOT_TOKEN=<token del bot>
TELEGRAM_CHAT_ID=<ID del chat o grupo>
GMAIL_USER=<correo gmail>
GMAIL_APP_PASSWORD=<app password de gmail>
EMAIL_DESTINO=larevo1111@gmail.com
```

**Dónde está la lógica:** `scripts/orquestador.py` — función `enviar_telegram()`.

---

## Cuándo envía mensajes

| Canal | Cuándo |
|---|---|
| **Email** | Siempre — éxito o error |
| **Telegram** | Solo cuando hay error en export o import |

Un error se define como:
- `exit_code != 0` del export (`export_all.sh`) o del import (`import_all.js`)
- O que haya líneas con `❌ Falló definitivamente:` en la salida del export

---

## Formato del mensaje de error

```
⚠️ Pipeline Effi — ERROR
📅 2026-03-09 11:57:31

<b>Scripts fallidos:</b>
  • export_facturas_venta
  • export_remisiones_venta

✅ Import: ✅ 39 tablas importadas ❌ 0 errores
```

O si el import también falla:
```
⚠️ Pipeline Effi — ERROR
📅 2026-03-09 11:57:31

<b>Scripts fallidos:</b>
  • export_facturas_venta

❌ Import: ✅ 38 tablas importadas ❌ 1 errores
```

**Principio:** el mensaje muestra SOLO los nombres de scripts fallidos, no los errores
técnicos crudos (timeouts, stack traces). El detalle técnico va al email.

---

## Cómo se extraen los scripts fallidos

`export_all.sh` imprime esta línea cuando un script falla definitivamente (incluso después del reintento):
```
❌ Falló definitivamente: export_facturas_venta
```

`orquestador.py` parsea la salida completa del export:
```python
errores_exp = [l.strip() for l in salida.splitlines() if '❌' in l and 'RESULTADO:' not in l]
fallidos    = [l for l in errores_exp if 'Falló definitivamente' in l]
# extrae nombre: "❌ Falló definitivamente: export_X" → "export_X"
nombre = f.split(':', 1)[-1].strip()
```

`errores_exp` puede tener muchas líneas con `❌` (errores de Node, timeouts, etc.) pero
solo las de `Falló definitivamente` van al Telegram.

---

## Cómo probar sin correr el pipeline completo

```python
# Simular parseo de errores
salida = "❌ Error: Timeout\n❌ Falló definitivamente: export_facturas_venta\n"
errores  = [l.strip() for l in salida.splitlines() if '❌' in l and 'RESULTADO:' not in l]
fallidos = [l for l in errores if 'Falló definitivamente' in l]
for f in fallidos:
    print(f.split(':', 1)[-1].strip())
# → export_facturas_venta
```

Para mandar un mensaje de prueba directamente:
```python
import urllib.request, urllib.parse
token   = 'TU_TOKEN'
chat_id = 'TU_CHAT_ID'
msg     = 'Test desde terminal'
url     = f'https://api.telegram.org/bot{token}/sendMessage'
data    = urllib.parse.urlencode({'chat_id': chat_id, 'text': msg}).encode()
urllib.request.urlopen(urllib.request.Request(url, data, method='POST'))
```

O desde bash:
```bash
source scripts/.env
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}&text=Test+pipeline"
```

---

## Función enviar_telegram en orquestador.py

```python
def enviar_telegram(env, mensaje):
    token   = env.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = env.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        log.warning('📱 Telegram no configurado en .env — omitiendo.')
        return
    url  = f'https://api.telegram.org/bot{token}/sendMessage'
    data = urllib.parse.urlencode({
        'chat_id':    chat_id,
        'text':       mensaje,
        'parse_mode': 'HTML',   # ← soporta <b>negrita</b>
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        ...
```

**`parse_mode: HTML`** — el mensaje puede usar `<b>texto</b>` para negrita.
No usar Markdown (`*texto*`) porque el modo configurado es HTML.

---

## Casos especiales

**¿Hay error pero no hay scripts fallidos definitivamente?**
Ocurre si el pipeline completo falla por timeout del orquestador (`EXPORT_TIMEOUT = 30 min`).
En ese caso `fallidos` estará vacío y el mensaje solo mostrará el estado del import.
Para depurar, revisar `logs/pipeline.log` o el email.

**¿El import tiene 1 error pero no se ve cuál tabla?**
El resumen del import (`✅ 38 tablas importadas ❌ 1 errores`) viene de `import_all.js`.
Para ver el detalle, revisar el email o correr import manualmente:
```bash
node scripts/import_all.js
```

**¿No llega mensaje de Telegram pero sí email?**
Verificar que `.env` tenga `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` correctos.
El bot debe ser administrador del chat/grupo o el chat debe ser privado con el bot.

---

## Comandos de diagnóstico

```bash
# Ver últimas ejecuciones del pipeline
tail -50 /home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/pipeline.log

# Correr pipeline completo forzado (ignora horario)
python3 scripts/orquestador.py --forzar

# Ver estado del timer automático
systemctl status effi-pipeline.timer
systemctl list-timers effi-pipeline.timer

# Ver logs del servicio en tiempo real
journalctl -u effi-pipeline -f
```
