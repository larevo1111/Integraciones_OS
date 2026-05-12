# Plan de testeo riguroso — Migración a Infisical

**Fecha**: 2026-05-11
**Objetivo**: validar que TODOS los servicios funcionan idéntico que antes Y verificar empíricamente que los secrets se leen de Infisical (no del `.env` ni del filesystem viejo).

---

## Resumen del testing

| # | Fase | Tiempo | Criticidad |
|---|---|---|---|
| 1 | Revisión de código (estática) | 30 min | 🔴 Alta — encontrar bugs antes que prod |
| 2 | Tests unitarios de helpers (`lib/infisical`, `lib/db_conn`) | 15 min | 🔴 Alta |
| 3 | Tests funcionales por servicio (8 servicios) | 60 min | 🔴 Alta |
| 4 | **Verificación "viene de Infisical"** por servicio | 30 min | 🔴 CRÍTICA — núcleo del audit |
| 5 | Tests de cache + fallback | 15 min | 🟡 Media |
| 6 | Tests de resiliencia (Infisical down, tailnet down) | 20 min | 🟡 Media |
| 7 | Auditoría de seguridad (logs, archivos, permisos) | 20 min | 🔴 Alta |
| **TOTAL** | | **~3 horas** | |

---

## FASE 1 — Revisión de código (estática)

### 1.1 Archivos a revisar

| Archivo | Líneas a revisar | Qué buscar |
|---|---|---|
| `lib/infisical.js` | 0-200 | Manejo de errores, refresh token, cache TTL, encoding correcto de URL params |
| `scripts/lib/infisical.py` | 0-200 | Mismo + verificar paramiko object loading sin escribir a disco |
| `lib/db_conn.js` | bootstrap section | Promise `_bootstrapPromise` se espera correctamente antes de SSH connect |
| `scripts/lib/db_conn.py` | bootstrap section | Import `from infisical import` no choca con stdlib |
| `sistema_gestion/api/server.js` | `cargarSecretsInfisical()` | Errors no crashean, fallback funciona |
| `scripts/inventario/api.py` | JWT_SECRET load | Fallback al valor hardcoded si Infisical falla (transición) |
| `scripts/produccion/api.py` | JWT + Google load | Idem |
| `scripts/ia_service/config.py` | bootstrap section | get_many no falla si Infisical no responde |

### 1.2 Checklist de revisión por archivo

**Para cada archivo, verificar**:
- [ ] No hay credenciales hardcoded después del refactor
- [ ] No hay `console.log()` / `print()` con valores de secrets
- [ ] El fallback al `.env` funciona si Infisical es inaccesible
- [ ] El cache tiene TTL razonable (5 min default)
- [ ] No hay race conditions en la inicialización
- [ ] Si una variable es None/undefined, el código no crashea

### 1.3 Búsqueda de patrones peligrosos

```bash
# 1. Buscar logging de secrets (debe devolver 0 hits)
grep -rnE "console\.log\(.*PASS|print\(.*pass|console\.log\(.*SECRET|console\.log\(.*KEY|console\.log\(.*TOKEN" lib/ scripts/lib/ scripts/ sistema_gestion/api/ frontend/api/

# 2. Buscar credenciales hardcoded restantes en código
grep -rnE "'[A-Za-z0-9]{32,}'|\"[A-Za-z0-9]{32,}\"" lib/ scripts/lib/ scripts/inventario/ scripts/produccion/ scripts/ia_service/ sistema_gestion/api/server.js | grep -vE "node_modules|test|comment|//|\\bexample\\b"

# 3. Buscar lectura de filesystem para SSH keys (debe ser solo fallback)
grep -rnE "readFileSync.*\.ssh|expanduser.*\.ssh" lib/ scripts/

# 4. Verificar que ningún servicio tenga API keys hardcoded
grep -rnE "api_key\s*=\s*['\"][^$\{]" scripts/ia_service/ scripts/inventario/ scripts/produccion/ | grep -v "process\.env\|os\.environ\|get\(\|infisical"
```

### 1.4 Output esperado de Fase 1

- Lista de hallazgos (issues encontrados)
- Para cada hallazgo: severidad (crit/alto/medio/bajo), archivo:línea, descripción, propuesta de fix
- Decisión: arreglar antes de Fase 2 o documentar como deuda

---

## FASE 2 — Tests unitarios de helpers

### 2.1 lib/infisical.js

```javascript
// Test suite
describe('lib/infisical.js', () => {
  it('get() recupera un secret existente', async () => {
    const v = await get('DB_LOCAL_USER', '/shared');
    expect(v).toBe('osadmin');
  });

  it('get() lanza error si secret no existe', async () => {
    await expect(get('SECRET_INEXISTENTE', '/shared')).rejects.toThrow();
  });

  it('get() usa cache en llamadas repetidas', async () => {
    const t1 = Date.now();
    await get('DB_LOCAL_USER', '/shared');
    const t2 = Date.now();
    await get('DB_LOCAL_USER', '/shared');  // debe ser <5ms (cache)
    const t3 = Date.now();
    expect(t3 - t2).toBeLessThan(50);  // mucho menor que t2-t1 (red)
  });

  it('getMany() retorna todos los secrets de un folder', async () => {
    const all = await getMany('/shared');
    expect(Object.keys(all).length).toBe(83);
    expect(all.DB_LOCAL_PASS).toBeDefined();
  });

  it('getSSHKey() retorna string con BEGIN/END markers', async () => {
    const k = await getSSHKey('VPS');
    expect(k).toContain('BEGIN OPENSSH PRIVATE KEY');
    expect(k).toContain('END OPENSSH PRIVATE KEY');
  });

  it('clearCache() invalida cache', async () => {
    await get('DB_LOCAL_USER', '/shared');
    clearCache();
    // siguiente get() debe ir a la red de nuevo (medible si quisiéramos)
  });
});
```

### 2.2 scripts/lib/infisical.py

```python
def test_get():
    from lib.infisical import get
    assert get('DB_LOCAL_USER', '/shared') == 'osadmin'

def test_get_secret_inexistente():
    from lib.infisical import get
    with pytest.raises(RuntimeError):
        get('SECRET_INEXISTENTE', '/shared')

def test_get_many():
    from lib.infisical import get_many
    all_shared = get_many('/shared')
    assert len(all_shared) == 83
    assert 'DB_LOCAL_PASS' in all_shared

def test_ssh_key_string():
    from lib.infisical import get_ssh_key_string
    k = get_ssh_key_string('VPS')
    assert 'BEGIN OPENSSH PRIVATE KEY' in k

def test_ssh_key_object():
    from lib.infisical import get_ssh_key_object
    pkey = get_ssh_key_object('VPS')
    # Verifica que es un objeto paramiko (no string ni path)
    from paramiko import Ed25519Key
    assert isinstance(pkey, Ed25519Key)
    assert pkey.get_bits() == 256
```

### 2.3 lib/db_conn.{js,py}

```bash
# Test bootstrap correcto
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib import db_conn
assert db_conn._INFISICAL_LOADED == True, 'bootstrap falló'
# Verificar que process.env tiene DB_LOCAL_PASS
import os
assert os.environ.get('DB_LOCAL_PASS'), 'DB_LOCAL_PASS no en env post-bootstrap'
print('✓ Bootstrap OK')
"

# Test conexión local
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib.db_conn import local
with local('ia_service_os') as c:
    cur = c.cursor()
    cur.execute('SELECT 1')
    assert cur.fetchone() == (1,)
print('✓ Conexión local OK')
"

# Test conexión remota (SSH tunnel con key de Infisical)
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from lib.db_conn import integracion
with integracion() as c:
    cur = c.cursor()
    cur.execute('SELECT VERSION()')
    print('✓ SSH tunnel + remote DB OK:', cur.fetchone()[0])
"
```

---

## FASE 3 — Tests funcionales por servicio

Por cada servicio, ejecutar:

### 3.1 ia-service (puerto 5100)

| Test | Comando | Resultado esperado |
|---|---|---|
| Health | `curl http://localhost:5100/ia/health` | HTTP 200 `{"ok":true}` |
| List agents | `curl http://localhost:5100/ia/agentes \| jq '.agentes \| length'` | 17 |
| Real query | `curl -X POST http://localhost:5100/ia/consultar -H 'Content-Type: application/json' -d '{"pregunta":"hola","usuario_id":"test_infisical","canal":"api"}' \| jq '.ok'` | true |
| Consumo | `curl http://localhost:5100/ia/consumo \| jq '.hoy.llamadas'` | número > 0 |

### 3.2 os-telegram-bot

| Test | Cómo | Resultado |
|---|---|---|
| Service activo | `systemctl is-active os-telegram-bot.service` | active |
| Logs sin error | `journalctl -u os-telegram-bot.service --since '5 min ago' \| grep -iE 'error\|exception'` | 0 líneas |
| Conexión Telegram | logs muestran `getMe HTTP/1.1 200 OK` reciente | sí |
| **Manual**: Santi envía `/start` al bot | El bot responde | ✓ |

### 3.3 os-gestion (puerto 9300)

| Test | Comando | Resultado |
|---|---|---|
| Health | `curl http://localhost:9300/` | HTTP 200 (HTML del SPA) |
| Bootstrap logs | `journalctl -u os-gestion.service \| grep 'Secrets cargados desde Infisical'` | ≥1 línea |
| SSH tunnels | logs `SSH tunnel listo → osserver@94.72.115.156` | sí (×2: GESTION, INTEGRACION) |
| Pool MySQL | logs `Pools listos (master Postgres + gestion/integracion/inventario)` | sí |
| **Endpoint real**: `curl http://localhost:9300/api/gestion/usuarios` (sin auth) | HTTP 401 (no autorizado, pero responde) |
| Conexión Postgres VPS | log `Pool Postgres listo → 127.0.0.1:5432/sos_master_erp` | sí |

### 3.4 os-inventario-api (puerto 9401)

| Test | Comando | Resultado |
|---|---|---|
| Health | `curl http://localhost:9401/` | HTTP 200 |
| FastAPI docs | `curl http://localhost:9401/docs` | HTTP 200 |
| Endpoint sin auth | `curl http://localhost:9401/articulos` | HTTP 401 (espera JWT) |
| JWT funciona | Generar JWT con `INVENTARIO_JWT_SECRET` de Infisical y hacer request | HTTP 200 |
| Logs sin error | `journalctl -u os-inventario-api.service --since '5 min ago' \| grep -iE 'error\|exception'` | solo eventos esperados |

### 3.5 os-produccion-api (puerto 9600)

| Test | Comando | Resultado |
|---|---|---|
| Health | `curl http://localhost:9600/` | HTTP 200 |
| FastAPI startup | `journalctl -u os-produccion-api \| grep 'Application startup complete'` | sí |

### 3.6 wa-bridge (puerto 3100)

| Test | Comando | Resultado |
|---|---|---|
| Service activo | `systemctl is-active wa-bridge.service` | active |
| Logs OK | logs no muestran errores fatales | sí |
| Conexión a Baileys | log `WA Bridge listo` o equivalente | sí |

### 3.7 effi-webhook (puerto 5050)

| Test | Comando | Resultado |
|---|---|---|
| Service activo | `systemctl is-active effi-webhook.service` | active |
| Flask up | log `Running on http://127.0.0.1:5050` | sí |
| Test endpoint | `curl http://localhost:5050/` | HTTP 404 (sin ruta /, OK) |

### 3.8 os-erp-frontend (VPS, puerto 9100)

| Test | Comando | Resultado |
|---|---|---|
| Service activo VPS | `ssh root@vps-contabo systemctl is-active os-erp-frontend.service` | active |
| HTTPS público | `curl https://menu.oscomunidad.com/` | HTTP 200 |
| API bot tabla | `curl https://menu.oscomunidad.com/api/bot/tabla?token=...` | HTTP 200 con tabla |
| Logs bootstrap | `ssh root@vps-contabo "journalctl -u os-erp-frontend \| grep 'OS ERP corriendo en puerto 9100'"` | sí |
| SSH tunnel desde VPS | logs `db_conn:INTEGRACION` indicando tunnel/pool | sí |

---

## FASE 4 — Verificación "viene de Infisical" 🔴 CRÍTICA

**Objetivo**: probar empíricamente que cada servicio lee los secrets de Infisical, NO del `.env`.

### Estrategia: prueba destructiva controlada

Para cada servicio, voy a:

1. **Renombrar temporalmente el `.env`** que ese servicio usaba antes
2. **Restart del servicio**
3. **Si arranca y funciona** → vino de Infisical ✓
4. **Si falla** → todavía depende del `.env` → bug

### 4.1 Test global — bootstrap Infisical

Verificar en logs de cada servicio el mensaje de éxito:

```bash
# Para servicios Node (gestion, erp)
journalctl -u os-gestion.service --since '30 min ago' | grep -E "Secrets cargados desde Infisical|Infisical bootstrap"

# Para servicios Python (inventario, produccion, ia-service)
journalctl -u os-inventario-api.service --since '30 min ago' | grep -E "Infisical|secrets"
```

**Cada servicio debe loggear "secrets cargados desde Infisical" o equivalente al startup.**

### 4.2 Test específico — Sistema Gestión (puerto 9300)

```bash
# Backup del .env
mv sistema_gestion/api/.env sistema_gestion/api/.env.BAK

# Restart (debe arrancar igual leyendo solo de Infisical)
sudo systemctl restart os-gestion.service
sleep 5
systemctl is-active os-gestion.service

# Test funcional
curl -sS http://localhost:9300/ | head -c 100

# Restaurar .env (pero ya validamos que NO lo necesitaba)
mv sistema_gestion/api/.env.BAK sistema_gestion/api/.env
```

**⚠ Atención**: hay 2 variables que el `.env` también tenía y son necesarias para el cliente Infisical:
- `INFISICAL_CLIENT_ID`
- `INFISICAL_CLIENT_SECRET`

Sin estas, los servicios no pueden hablar con Infisical. El bootstrap file `/home/osserver/tempoclv/.infisical_admin_bootstrap.env` actúa como fallback, así que técnicamente el `.env` se puede quitar y todo sigue funcionando.

### 4.3 Test por cada servicio

Lo mismo para los otros 7 servicios. Repetir el patrón "rename → restart → validate → restore".

### 4.4 Test del SSH key (memoria pura)

```bash
# Renombrar SSH key del filesystem
mv ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.BAK_TEST

# Restart un servicio que use SSH tunnel (ej: os-gestion)
sudo systemctl restart os-gestion.service
sleep 8

# Verificar logs: el tunnel debe levantarse usando key de Infisical
journalctl -u os-gestion.service --since '20 sec ago' | grep -E "SSH tunnel listo|SSH error"

# Si arrancó OK = SSH key viene de Infisical (memoria pura) ✓
# Si falló = todavía intenta filesystem

# Restaurar key
mv ~/.ssh/id_ed25519.BAK_TEST ~/.ssh/id_ed25519
```

### 4.5 Resultado esperado de Fase 4

Tabla:

| Servicio | `.env` renombrado | Arranca OK | Funciona OK | Conclusión |
|---|---|---|---|---|
| ia-service | sí | sí/no | sí/no | ✓ Infisical / ✗ aún depende |
| os-gestion | sí | ... | ... | ... |
| os-inventario-api | sí | ... | ... | ... |
| os-produccion-api | sí | ... | ... | ... |
| os-telegram-bot | (no tiene .env propio) | n/a | sí | ✓ usa scripts/.env del ia-service |
| wa-bridge | (no tiene .env crítico) | n/a | sí | ... |
| effi-webhook | (no tiene .env crítico) | n/a | sí | ... |
| os-erp-frontend (VPS) | sí | ... | ... | ... |

---

## FASE 5 — Tests de cache + fallback

### 5.1 Cache TTL respeta el límite

```python
import time
from lib.infisical import get, clear_cache

# Primera llamada va a red
t1 = time.time()
v = get('DB_LOCAL_USER', '/shared')
t1_dur = time.time() - t1

# Segunda llamada (debería ser cache, <50ms)
t2 = time.time()
v = get('DB_LOCAL_USER', '/shared')
t2_dur = time.time() - t2

assert t2_dur < 0.05, f'Cache no funciona: {t2_dur*1000}ms'
assert t1_dur > 0.05, f'Primera llamada sospechosamente rápida: {t1_dur*1000}ms'
print(f'✓ Cache OK: 1ra={t1_dur*1000:.1f}ms, 2da={t2_dur*1000:.1f}ms')
```

### 5.2 Cache se invalida tras TTL

Para esto necesitamos un TTL corto:

```python
from lib.infisical import get, clear_cache
import time

clear_cache()
get('DB_LOCAL_USER', '/shared', ttl_s=2)
time.sleep(3)
# 3ra llamada debería ir a red de nuevo (cache expiró)
t = time.time()
get('DB_LOCAL_USER', '/shared', ttl_s=2)
print(f'Post-expire: {(time.time()-t)*1000:.1f}ms')  # Esperado: >50ms
```

### 5.3 Fallback al `.env` cuando Infisical no responde

Simular Infisical caído:

```bash
# Bloquear acceso a Infisical (modificar hosts temporalmente)
echo "127.0.0.1 vps-contabo.tail44c420.ts.net" | sudo tee -a /etc/hosts

# Restart servicio
sudo systemctl restart os-gestion.service
sleep 8
systemctl is-active os-gestion.service

# Verificar logs: debe mostrar "Infisical no disponible, usando .env"
journalctl -u os-gestion.service --since '20 sec ago' | grep -E "Infisical|fallback"

# Test funcional: el servicio debe seguir funcionando
curl -sS http://localhost:9300/ -o /dev/null -w "HTTP %{http_code}\n"

# Restaurar /etc/hosts
sudo sed -i '/vps-contabo.tail44c420.ts.net/d' /etc/hosts
sudo systemctl restart os-gestion.service
```

---

## FASE 6 — Tests de resiliencia

### 6.1 Infisical container reiniciando

```bash
# Reiniciar el backend de Infisical
ssh root@vps-contabo "cd /opt/infisical && docker compose restart backend"

# Mientras se reinicia, intentar consultar
for i in {1..10}; do
  echo "Intento $i:"
  curl -sS -o /dev/null -w "HTTP %{http_code} en %{time_total}s\n" \
    https://vps-contabo.tail44c420.ts.net/api/status --max-time 10
  sleep 1
done

# Verificar que los servicios siguen funcionando gracias al cache
curl -sS -o /dev/null -w "gestion HTTP %{http_code}\n" http://localhost:9300/
```

### 6.2 Tailnet down

```bash
# Apagar tailscale temporalmente
sudo tailscale down

# Intentar conectar a Infisical (debe fallar)
curl -sS --max-time 5 https://vps-contabo.tail44c420.ts.net/api/status 2>&1 | head -3

# Verificar que los servicios YA cacheados siguen funcionando
curl -sS -o /dev/null -w "gestion HTTP %{http_code}\n" http://localhost:9300/

# Restart un servicio cuando tailnet está down — debe usar fallback .env
sudo systemctl restart effi-webhook.service
sleep 5
systemctl is-active effi-webhook.service

# Restaurar tailnet
sudo tailscale up
```

---

## FASE 7 — Auditoría de seguridad

### 7.1 Logs sin secrets

```bash
# Buscar leaks en logs recientes (debe devolver 0)
journalctl --since '1 hour ago' | grep -iE "AAG1Ctrf|st\.[a-z0-9]{50,}|sk-ant-|sk-proj-|AIzaSy|gsk_|Pepe2467\.|82d13e9a"
```

### 7.2 Permisos de archivos

```bash
# Bootstrap file: 600
ls -la /home/osserver/tempoclv/

# .env de cada servicio: 600 idealmente, mínimo 644
ls -la sistema_gestion/api/.env
ls -la scripts/.env
ls -la integracion_conexionesbd.env

# SSH keys: 600
ls -la ~/.ssh/id_ed25519 ~/.ssh/sos_erp
```

### 7.3 No hay archivos /tmp con SSH keys leak

```bash
# Verificar que el helper NO escribió SSH keys a /tmp
find /tmp -name '*ssh*' -o -name '*key*' 2>/dev/null
find /dev/shm -name '*ssh*' 2>/dev/null

# Procesos abiertos no tienen FDs a key files de Infisical
lsof | grep -iE '\.ssh.*\(deleted\)|tempoclv' | head -5
```

### 7.4 git status — nada de secrets nuevos para commitear

```bash
git status
git diff | grep -iE "BEGIN OPENSSH|password=|api_key=|^\+.*[A-Za-z0-9]{50,}"
```

---

## Output esperado del plan completo

Al final tendré:

1. **Reporte de Fase 1 (revisión de código)**: lista de issues encontrados con severidad
2. **Reporte de Fase 2 (unit tests)**: ✓/✗ por test, total pass/fail
3. **Reporte de Fase 3 (functional)**: 8 servicios × 4-7 tests cada uno
4. **Tabla de Fase 4 (origen del secret)**: confirmación empírica por servicio
5. **Reporte de Fase 5 (cache+fallback)**: ✓/✗
6. **Reporte de Fase 6 (resiliencia)**: comportamiento ante fallas
7. **Reporte de Fase 7 (security audit)**: ✓/✗

Todo se guarda en `.agent/informes/testeo_infisical_2026-05-11.md`.

---

## Riesgos del testing

| Riesgo | Mitigación |
|---|---|
| Renombrar `.env` rompe el servicio y no puedo recuperar | Backup ANTES, restaurar SIEMPRE al final. Hago un solo `.env` a la vez. |
| Apagar Tailscale me deja sin acceso al VPS para los tests | Tengo SSH a VPS por IP pública 94.72.115.156 como fallback |
| Bloquear DNS de Infisical rompe servicios live | Hago en horario tranquilo, restauro inmediato |
| Cache mantiene credenciales viejas tras rotación | Documento que post-rotación hay que `clear_cache()` o restart |
| Tests muy largos quitan tiempo a Fase B | Estimo 3h. Si me extiendo, paro y continuo otro día. |

---

## ¿Cuándo NO hacer todos los tests?

Si Santi quiere validación rápida (~30 min), correr solo:
- Fase 3 (tests funcionales por servicio): 60 min → reducible a 20 min con curl básicos
- Fase 4.1 (logs muestran "Secrets cargados desde Infisical"): 5 min
- Fase 7.1-7.2 (logs limpios + permisos): 5 min

Eso da un piso de confianza razonable. El "all-in" (3h) es para máxima rigurosidad.
