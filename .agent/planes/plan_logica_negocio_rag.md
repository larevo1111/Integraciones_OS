# Plan: Lógica de Negocio — Capa 0 del Contexto IA

> Diseñado 2026-03-17. Pendiente de implementación.

## Problema

La IA conoce el schema de las tablas pero no la semántica del negocio.
Conceptos como "tarifas de precios", "canales de marketing", "estados de consignación"
no están en ningún schema — son conocimiento humano que hoy solo vive en el system_prompt,
editado manualmente por Claude Code cuando hay un problema.

El usuario no puede enseñarle directamente a la IA sin pasar por Claude Code.

## Solución

Una **Capa 0 de lógica de negocio** que:
1. Se inyecta en CADA consulta (no depende de búsqueda semántica)
2. El usuario la alimenta directamente desde el bot de Telegram, con un protocolo ordenado
3. Un bot depurador la mantiene compacta automáticamente cuando crece demasiado

## Arquitectura del contexto (nuevo orden)

```
Capa 0 — Lógica de negocio OS        ← NUEVA (máx 800 palabras, siempre presente)
Capa 1 — System prompt base          ← ya existe (tablas, campos, reglas SQL)
Capa 2 — RAG documental              ← ya existe (manuales, catálogos)
Capa 3 — Schema BD / DDL             ← ya existe
Capa 4 — Resumen conversación        ← ya existe
Capa 5 — Últimos mensajes            ← ya existe
Capa 6 — Pregunta actual             ← ya existe
```

## Activación de fragmentos — Por keywords

La lógica de negocio NO se fragmenta por tema (los conceptos de OS cruzan todos los temas:
tarifas tocan comercial + inventario + facturación; OPs tocan producción + compras + inventario).

Cada concepto guardado tiene **keywords** asociadas.
Si la pregunta del usuario activa alguna keyword → se inyecta ese concepto.
Sin embeddings, sin búsqueda semántica. Simple y predecible.

## Bot depurador automático

- **Límite**: 800 palabras
- **Disparador**: cuando el documento supera 800 palabras
- **Acción**: llama a Groq con instrucción de comprimir a 600 palabras
- **Regla crítica para Groq**: "comprimir volumen, NUNCA perder precisión numérica ni reglas exactas"
- **Modelo**: mismo patrón que `_generar_resumen_groq()` en servicio.py

## Protocolo de enseñanza (flujo desde Telegram)

### Activación
- El usuario dice algo y la IA no entiende el concepto de negocio
- O el usuario escribe explícitamente: "quiero enseñarte algo" / "enséñate sobre X"

### Flujo
```
1. IA detecta que no entiende → pregunta: "¿Quieres explicarme cómo funciona esto?"
2. Usuario acepta → IA entra en modo enseñanza
3. IA hace preguntas hasta tener el concepto claro (cuántas sean necesarias)
4. IA propone el texto que va a guardar → pide confirmación al usuario
5. Usuario confirma → se guarda en BD con keywords extraídas automáticamente
6. IA hace una pregunta de verificación para confirmar que ahora sí puede responder
```

### Distinción importante
- "No tengo datos" (SQL correcto, BD devuelve 0 filas) → NO activa modo enseñanza
- "No entiendo el concepto" (no sé qué tabla ni cómo relacionar) → SÍ activa modo enseñanza

## BD — tabla nueva propuesta

```sql
CREATE TABLE ia_logica_negocio (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  empresa     VARCHAR(50) NOT NULL DEFAULT 'ori_sil_2',
  concepto    VARCHAR(100) NOT NULL,       -- nombre corto ("Tarifas de precios")
  explicacion TEXT NOT NULL,               -- el texto que se inyecta
  keywords    VARCHAR(500),               -- palabras clave separadas por coma
  palabras    INT,                         -- conteo actual de palabras
  activo      TINYINT(1) DEFAULT 1,
  creado_por  VARCHAR(100),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Dónde se inyecta en servicio.py

En la función `consultar()`, antes de armar el system_prompt:
```python
# Capa 0: lógica de negocio
logica = _obtener_logica_negocio(empresa, pregunta)  # filtra por keywords
if logica:
    system_prompt = f"<logica_negocio>\n{logica}\n</logica_negocio>\n\n" + system_prompt
```

## Casos de uso iniciales (cuando se implemente)

- Tarifas de precios: cómo se asignan a clientes, cuántas hay, qué significa cada una
- Canales de marketing: qué es cada canal, cómo se clasifican los clientes
- Proceso de consignación: flujo completo, estados, diferencia con venta normal
- Producción: qué es una OP, cómo se relaciona con inventario y ventas

## Estado
- [ ] Pendiente — diseño aprobado 2026-03-17
- [ ] Crear tabla `ia_logica_negocio` en BD
- [ ] Implementar `_obtener_logica_negocio()` en servicio.py
- [ ] Implementar modo enseñanza en bot Telegram
- [ ] Implementar bot depurador (compactador automático)
- [ ] Primer seed: tarifas de precios (con Santi)
