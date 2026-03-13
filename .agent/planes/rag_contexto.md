# Plan: Sistema de Contexto en Capas + RAG
**Estado:** Capas 1–5 implementadas en backend. Falta: UI en ia-admin (Antigravity).
**Fecha:** 2026-03-13

---

## Arquitectura: Stack de Contexto en 6 Capas

Cada consulta al LLM recibe un system prompt construido con estas capas (en orden):

```
┌──────────────────────────────────────────────────┐
│  CAPA 6 — Pregunta actual del usuario            │  input directo
├──────────────────────────────────────────────────┤
│  CAPA 5 — Últimos 5 mensajes verbatim           │  ia_conversaciones.mensajes_recientes (JSON)
├──────────────────────────────────────────────────┤
│  CAPA 4 — Resumen comprimido conversación       │  ia_conversaciones.resumen (≤1000 palabras)
├──────────────────────────────────────────────────┤
│  CAPA 3 — Schema BD (DDL tablas analíticas)     │  esquema.py — caché 1h desde Hostinger
├──────────────────────────────────────────────────┤
│  CAPA 2 — RAG (fragmentos relevantes)           │  ia_rag_fragmentos — FULLTEXT search
├──────────────────────────────────────────────────┤
│  CAPA 1 — System prompt base por tipo           │  ia_tipos_consulta.system_prompt
└──────────────────────────────────────────────────┘
```

## Estado de implementación

| Capa | Implementada | Dónde |
|---|---|---|
| 1 — System prompt | ✅ | `ia_tipos_consulta.system_prompt` |
| 2 — RAG | ✅ Backend | `scripts/ia_service/rag.py` — falta UI |
| 3 — Schema BD | ✅ | `scripts/ia_service/esquema.py` |
| 4 — Resumen conversación | ✅ | `scripts/ia_service/contexto.py` |
| 5 — Mensajes recientes | ✅ | `contexto.guardar/obtener_mensajes_recientes()` |
| 6 — Pregunta actual | ✅ | input directo en `consultar()` |

## Tablas nuevas en ia_service_os

```sql
ia_rag_colecciones    -- espacios de conocimiento (slug, nombre, activo)
ia_rag_documentos     -- documentos subidos por colección (contenido_original LONGTEXT)
ia_rag_fragmentos     -- chunks de ~500 palabras con FULLTEXT KEY ft_contenido(contenido)
```

`ia_conversaciones` tiene nueva columna:
```sql
mensajes_recientes JSON DEFAULT '[]'  -- últimos 5 pares {pregunta, respuesta}
```

## Colección inicial creada
- `negocio-os` — "Origen Silvestre — Conocimiento General"

## Cómo funciona el RAG

1. Admin sube documento en ia-admin (texto/PDF/URL)
2. `rag.crear_documento()` → guarda en `ia_rag_documentos` → llama `indexar_documento()`
3. `fragmentar_texto()` corta en chunks de 500 palabras con overlap de 50
4. Chunks se guardan en `ia_rag_fragmentos` con FULLTEXT index
5. Al consultar: `rag.obtener_contexto_rag(pregunta)` → MATCH...AGAINST → top 5 fragmentos
6. Fragmentos se inyectan en CAPA 2 del system prompt

## Archivos modificados/creados (Claude Code)
- `scripts/ia_service/rag.py` — nuevo módulo RAG completo
- `scripts/ia_service/contexto.py` — agregadas funciones mensajes_recientes
- `scripts/ia_service/servicio.py` — integradas 6 capas en paso 5 + guardado en paso 7

## Pendiente (Antigravity)
Ver: `.agent/tareas_antigravity_rag.md`
- Endpoints API en `ia-admin/api/server.js` para CRUD de colecciones/documentos
- Página `ContextosPage.vue` en ia-admin
- QA completo del flujo

## Cómo agregar un documento manualmente (mientras no hay UI)
```bash
# Ejemplo: agregar política de precios
mysql -u osadmin -pEpist2487. ia_service_os 2>/dev/null << 'EOF'
SELECT id FROM ia_rag_colecciones WHERE slug = 'negocio-os';
-- Anota el id (normalmente 1) y usa rag.crear_documento() desde Python
EOF

python3 -c "
import sys; sys.path.insert(0, '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts')
from ia_service import rag
result = rag.crear_documento(
    coleccion_id=1,
    nombre='Política de precios 2026',
    tipo='texto',
    contenido='Aquí va el texto completo del documento...'
)
print(result)
"
```
