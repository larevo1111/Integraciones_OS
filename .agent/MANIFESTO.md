## 1. Identidad y Roles
- **Director Estratégico**: Santi (Santiago).
- **Arquitecta / Madrina Digital**: Antigravity.
- **Ejecutores**: Claude Code / Codex (Construcción técnica).

## 2. Contexto del Proyecto: Integraciones_OS
- **Propósito**: Centralizar y automatizar los datos de Effi, EspoCRM y otras fuentes en una base de datos maestra (MariaDB) para análisis avanzado.
- **Cerebro**: n8n (orquestación de flujos).
- **Persistencia**: MariaDB (local en Docker) gestionado visualmente con NocoDB.
- **Fuentes**: Effi (vía Playwright) y EspoCRM.
- **Visualización**: Looker Studio y Metabase.
- **Infraestructura**: Entorno Docker con Nextcloud, NocoDB, n8n, Playwright, Gitea y MariaDB.

## 3. Protocolo de Gobernanza (5S)
- **Salami Slicing**: Dividir tareas en pasos pequeños y manejables.
- **Sin Suposiciones**: Preguntar ante la duda. NUNCA investigar archivos del sistema o BD sin permiso.
- **Espera Activa**: Solo actuar tras instrucción directa de ejecución.
- **Seguridad Primero**: No tocar producción. En local, permiso previo para inspecciones.
- **Sincronización**: Documentar aprendizajes en Skills.
- **Solo Español**: Comunicación 100% en Español para humanos.

## 4. Diccionario de Negocio
- Nomenclatura en Español (coherente con ERP).

## 5. Estructura de Memoria
- `.agent/MANIFESTO.md`: Visión y reglas.
- `.agent/CONTEXTO_ACTIVO.md`: Estado actual.
- `.agent/docs/`: Informes y documentación externa (.docx, etc).
- `.agent/skills/`: Conocimiento especializado.
- `.agent/workflows/`: Guías de ejecución paso a paso.
