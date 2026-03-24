# Plan: Claude Code CLI como Agente Casi-Humano del Sistema IA

**Creado**: 2026-03-23
**Módulo**: ia_service + telegram_bot
**Estado**: En diseño — pendiente implementación

---

## Visión

Claude Code CLI (`claude -p`) opera AL LADO del sistema como un agente autónomo con acceso total al sistema: lee archivos, ejecuta queries MySQL, corre comandos, analiza resultados y toma decisiones. **NO es un proveedor LLM más dentro de `ia_service`** — es una capa externa que orquesta todo el sistema.

---

## Los 3 roles definidos

### Rol 1 — Agente directo en el Bot Telegram (bypass ia_service)

Cuando Santi o Jen eligen "Claude Code" en el bot, el bot ejecuta `claude -p` directamente con la pregunta + contexto. Claude Code decide por sí solo qué consultar, genera y ejecuta el SQL, redacta la respuesta.

**Decisiones tomadas:**
- Acceso: Santi (nivel 7) y Jen (nivel 5) — **igual para ambos**. No tiene sentido limitar a Jen si ella es quien más necesita respuestas precisas.
- Contador de uso diario con alerta Telegram cuando supera X llamadas (sin bloquear)
- El bot NO pasa por `ia_service` Flask para este agente — llama `claude -p` directamente

### Rol 2 — Entrenador del sistema (análisis → propuestas)

Script `scripts/claude_trainer.sh` que:
1. Lee `logs/pipeline.log` + `logs/mejora_continua.log`
2. Lee registros de `ia_feedback WHERE procesado=0`
3. Identifica problemas reales con causa raíz (no síntomas)
4. Genera reporte en `/tmp/reporte_mejoras_<YYYYMMDD>.md` con propuestas numeradas

**Importante**: Solo propone, no aplica. Santi revisa y marca con ✅ los cambios aprobados.

### Rol 3 — Aplicador de mejoras (ejecuta cambios aprobados)

Script `scripts/claude_aplicar.sh` que:
1. Lee el reporte del día (`/tmp/reporte_mejoras_<hoy>.md`)
2. Aplica SOLO los cambios marcados con ✅ por Santi
3. **SOLO toca BD**: `ia_logica_negocio`, `ia_ejemplos_sql`, `ia_tipos_consulta`
4. Hace backup del valor anterior antes de cada cambio
5. Notifica a Telegram qué se aplicó y por qué

---

## Reglas anti-parches (modo autónomo)

Documentadas en `CLAUDE.md` del proyecto y en `.agent/MANIFESTO.md` sección de reglas.

**Resumen crítico:**
- NUNCA modifica código Python, JS o archivos de configuración
- NUNCA aplica workarounds o parches superficiales
- NUNCA hardcodea valores para "resolver" un bug
- Si no identifica causa raíz → solo documenta, nunca "arregla" el síntoma
- Cada cambio en BD → backup anterior + log de qué cambió y por qué

---

## Git y ramas

**Sin ramas de git para cambios del entrenador.** Los cambios son en BD (reversibles con DELETE/UPDATE). Los cambios de código Python solo suceden en sesión interactiva con Santi — se manejan con el flujo git normal.

---

## Flujo completo

```
1. Santi lanza: bash scripts/claude_trainer.sh
   └── Claude analiza logs + ia_feedback
   └── Genera: /tmp/reporte_mejoras_<fecha>.md

2. Santi lee el reporte (5-10 min)
   └── Marca con ✅ los cambios que aprueba
   └── Marca con ❌ los que rechaza

3. Santi lanza: bash scripts/claude_aplicar.sh
   └── Claude aplica solo los ✅
   └── Backup de valores anteriores
   └── Notifica a Telegram: qué cambió y por qué

4. Si el problema requería cambio de código:
   └── Santi abre sesión interactiva con Claude Code
   └── Lo hacen juntos (como siempre)
```

---

## Tareas

### Parte A — Infraestructura y reglas
- [x] Agregar reglas modo autónomo a `CLAUDE.md` del proyecto — 2026-03-23
- [x] Agregar estructura multi-contexto al MANIFESTO — 2026-03-23
- [x] Crear directorios `planes/actuales/` y `planes/completados/` — 2026-03-23

### Parte B — Scripts del entrenador
- [ ] Crear `scripts/claude_trainer.sh` — leer logs + ia_feedback → reporte en /tmp/
- [ ] Crear `scripts/claude_aplicar.sh` — leer reporte aprobado → aplicar cambios en BD

### Parte C — Bot Telegram
- [ ] Agregar opción "Claude Code" en el menú de agentes del bot
- [ ] Implementar bypass: cuando agente=claude_code → llamar `claude -p` en lugar de `ia_service`
- [ ] Agregar contador de uso diario en `ia_sesiones` o tabla nueva
- [ ] Alerta Telegram cuando supera N llamadas diarias (configurable, sin bloquear)

### Parte D — Verificación
- [ ] Probar claude_trainer.sh con empresa=ori_sil_2
- [ ] Verificar que claude_aplicar.sh solo toca BD (no archivos)
- [ ] Probar "Claude Code" en el bot con pregunta de análisis de datos
- [ ] Verificar que el contador diario funciona y notifica correctamente

---

## Qué NO se hace

- No integrar Claude Code como proveedor dentro de `ia_service` (no es un LLM más)
- No usar ramas de git para cambios del entrenador
- No permitir que el entrenador modifique código Python en automático
- No limitar el acceso de Jen — acceso igual que Santi
