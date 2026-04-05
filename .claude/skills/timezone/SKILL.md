---
name: timezone
description: >
  Manejo de zona horaria del sistema. Triggers: timezone, hora, UTC, zona horaria, NOW(), fecha, timestamp, horario.
---

# Skill: Manejo de Zona Horaria — Integraciones OS

> Este documento es la fuente de verdad sobre cómo se maneja el tiempo en todo el sistema.
> Actualizado: 2026-04-05 tras la corrección definitiva del problema UTC vs Colombia.

---

## Principio fundamental

**El sistema opera en hora Colombia (UTC-5). Todas las fechas y horas que ve el usuario, se guardan en BD o se comparan en queries deben estar en UTC-5.**

La zona horaria se configura en un solo lugar: `APP_TIMEZONE` en el `.env` del módulo correspondiente. No está hardcodeada en código.

---

## Arquitectura actual

### Servidor local (osserver)

| Elemento | Timezone | Cómo verificar |
|---|---|---|
| OS (Linux) | `America/Bogota` (-05) | `timedatectl` |
| MariaDB local | SYSTEM (= Colombia) | `SELECT NOW(), @@session.time_zone` |
| Node.js | Hereda del OS (Colombia) | `new Date().toString()` |
| Python | Hereda del OS (Colombia) | `date.today()` |

### Hostinger (MySQL remoto)

| Elemento | Timezone nativo | Timezone con pool |
|---|---|---|
| MySQL Hostinger | **UTC** (NOW() = UTC) | **Colombia** gracias a `SET time_zone` |

**Clave**: Hostinger opera en UTC puro. Sin el `SET time_zone = '-05:00'` en cada conexión, `NOW()` devuelve UTC.

---

## Implementación — Sistema Gestión OS

### Archivo `.env`

```
# sistema_gestion/api/.env
APP_TIMEZONE=-05:00
```

### Archivo `db.js`

```javascript
// Lee APP_TIMEZONE del .env
const APP_TIMEZONE = process.env.APP_TIMEZONE || '-05:00'

// Pool config
const base = {
  timezone: APP_TIMEZONE,   // mysql2 convierte Date de JS al offset indicado
  dateStrings: true          // retorna fechas como strings, sin reconversión
}

// En cada conexión nueva del pool:
pool.pool.on('connection', conn => {
  conn.query(`SET time_zone = '${APP_TIMEZONE}'`)
})
```

### Efecto

| Operación | Antes (bug) | Ahora (correcto) |
|---|---|---|
| `NOW()` en query | 15:33 (UTC) | 10:33 (Colombia) |
| `new Date()` pasado a mysql2 | Se guardaba UTC crudo | mysql2 lo convierte a -05:00 |
| `dateStrings: true` lectura | Devolvía "15:33" (UTC) | Devuelve "10:33" (Colombia) |

---

## Reglas por capa

### SQL (queries en server.js)

| Patrón | Estado | Notas |
|---|---|---|
| `NOW()` | **CORRECTO** | Devuelve Colombia gracias al SET time_zone del pool |
| `CURRENT_TIMESTAMP` | **CORRECTO** | Idem |
| `UTC_TIMESTAMP()` | **PROHIBIDO** | Devuelve UTC — solo usar si explícitamente se necesita UTC |
| `CURDATE()` | **CORRECTO** en pool | Pero PROHIBIDO en queries SSH directas a Hostinger |

### Backend Node.js (server.js)

| Patrón | Estado | Notas |
|---|---|---|
| `new Date()` pasado a query mysql2 | **CORRECTO** | mysql2 lo convierte con `timezone: '-05:00'` |
| `new Date().toISOString()` | **PROHIBIDO** | Devuelve UTC (ej: `2026-04-05T16:33:00Z`) |
| `new Date().toISOString().slice(0,10)` | **PROHIBIDO** | Después de 7pm Colombia = día siguiente UTC |
| `localDateCO()` | **CORRECTO** | Para obtener fecha YYYY-MM-DD en Colombia |

### Frontend (Vue/JS)

| Patrón | Estado | Notas |
|---|---|---|
| `hoyLocal()` | **CORRECTO** | De `src/services/fecha.js` |
| `new Date().toISOString().slice(0,10)` | **PROHIBIDO** | Git hook lo bloquea |
| Mostrar fecha de BD | **CORRECTO** | `dateStrings: true` → llega como string Colombia |

### Python (scripts/)

| Patrón | Estado | Notas |
|---|---|---|
| `date.today()` | **CORRECTO** | Server local = Colombia |
| `datetime.utcnow()` | **PROHIBIDO** | Devuelve UTC |
| `datetime.now()` | **CORRECTO** | Server local = Colombia |

---

## Git hook de protección

`.githooks/pre-commit` bloquea commits que contengan:
- `toISOString().slice(0, 10)`
- `UTC_TIMESTAMP()` (sin comentario `// ok-utc`)

Para saltarse el hook en un caso legítimo de UTC, agregar `// ok-utc` al final de la línea.

---

## Cómo cambiar la zona horaria

### Paso 1: Editar `.env`

```bash
# sistema_gestion/api/.env
APP_TIMEZONE=-03:00   # Ejemplo: Argentina
```

### Paso 2: Reiniciar el servicio

```bash
sudo systemctl restart os-gestion.service
```

### Paso 3: Verificar

```bash
# Debe mostrar la hora local correcta
journalctl -u os-gestion -n 5  # Ver "[db] Pools creados — timezone: -03:00"
```

### Paso 4: Corregir datos existentes (si hay)

```sql
-- Si se cambia de -05:00 a -03:00, restar 2 horas (nueva - vieja = +2h, restar para corregir)
-- O sumar, dependiendo de la dirección del cambio
UPDATE g_tareas SET fecha_inicio_real = DATE_ADD(fecha_inicio_real, INTERVAL 2 HOUR) WHERE fecha_inicio_real IS NOT NULL;
-- Repetir para todas las tablas con timestamps
```

---

## Plan futuro: timezone por empresa

Cuando se implemente:

1. Agregar columna `timezone VARCHAR(10) DEFAULT '-05:00'` a `sys_empresas` en `os_comunidad`
2. Al autenticar (`requireAuth` middleware), leer el timezone de la empresa
3. Ejecutar `SET time_zone = ?` con el timezone de la empresa en cada query
4. Almacenar en `req.timezone` para usarlo en el middleware
5. Cambiar `APP_TIMEZONE` a un fallback por defecto

---

## Verificación rápida

```sql
-- Ejecutar desde cualquier pool del sistema:
SELECT NOW() AS hora_colombia, UTC_TIMESTAMP() AS hora_utc, @@session.time_zone AS tz;
-- Debe mostrar: hora_colombia = hora local, tz = -05:00
```

```bash
# Desde terminal del servidor:
date  # Debe mostrar -05
timedatectl | grep "Time zone"  # America/Bogota
```
