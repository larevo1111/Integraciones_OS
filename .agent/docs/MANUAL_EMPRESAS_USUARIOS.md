# Manual: Gestión de Empresas y Usuarios — ia_service_os

**Aplica a**: Panel de administración `ia.oscomunidad.com` y servicio `ia_service_os`
**Referencia técnica**: `.agent/planes/actuales/PLAN_MULTITENANT_IA.md`
**Patrón de origen**: SOS_ERP (`sys_empresa`, `sys_usuarios`, `sys_usuarios_empresas`)

---

## 1. ¿Qué es una Empresa en el sistema?

Una **empresa** es el eje central de seguridad y organización. Todo dato en el sistema pertenece a una empresa:
- Conversaciones, logs, consumo de IA
- Temas RAG y documentos de contexto
- Tipos de consulta personalizados

Esto permite que **múltiples empresas compartan la misma infraestructura** (mismo servicio IA, mismos modelos de LLM) sin que sus datos se mezclen.

### Empresa actual
| uid | Nombre | Siglas |
|---|---|---|
| `ori_sil_2` | Origen Silvestre | OS |

---

## 2. Modelo de datos

```
ia_empresas (1)
    │ uid = "ori_sil_2"
    │
    └─── ia_usuarios_empresas (N)
         │ usuario_email + empresa_uid + rol
         │
         └─── ia_usuarios (1)
              email = PK del usuario
```

Un usuario puede pertenecer a **múltiples empresas** con roles distintos en cada una.

### Roles disponibles

| Rol | Puede hacer |
|---|---|
| `admin` | Todo: ver logs, editar agentes, gestionar contextos RAG, administrar usuarios |
| `editor` | Editar contextos RAG, ver logs propios, usar playground |
| `viewer` | Solo ver dashboards y logs (sin modificar nada) |

---

## 3. Cómo funciona el login (flujo de 2 pasos)

### Paso 1: Autenticación con Google
1. Usuario hace clic en "Continuar con Google"
2. Google valida la identidad → devuelve `id_token`
3. El sistema verifica que el email exista en `ia_usuarios`
4. Consulta `ia_usuarios_empresas` para saber a qué empresas tiene acceso
5. **Si tiene 1 sola empresa** → selección automática → token final → dashboard
6. **Si tiene múltiples** → token temporal (30 min) → pasa a Paso 2

### Paso 2: Selección de empresa (solo si tiene varias)
1. Se muestra una pantalla con las empresas disponibles
2. Usuario hace clic en la empresa que quiere usar
3. Sistema emite token final (7 días) con `empresa_activa`
4. Usuario entra al dashboard de esa empresa

### Cambiar de empresa (dentro de la app)
- Header superior → botón de empresa → selector de empresas
- Al cambiar, se emite un nuevo token final y se recarga la app

---

## 4. Estructura del JWT

### Token temporal (solo para selección de empresa)
```json
{
  "tipo": "temporal",
  "email": "larevo1111@gmail.com",
  "nombre": "Santiago",
  "empresas": [
    { "uid": "ori_sil_2", "nombre": "Origen Silvestre", "siglas": "OS", "rol": "admin" },
    { "uid": "otra_emp", "nombre": "Otra Empresa", "siglas": "OE", "rol": "viewer" }
  ],
  "exp": "15 minutos"
}
```

### Token final (sesión activa)
```json
{
  "tipo": "final",
  "email": "larevo1111@gmail.com",
  "nombre": "Santiago",
  "empresa_activa": "ori_sil_2",
  "empresa_nombre": "Origen Silvestre",
  "empresa_siglas": "OS",
  "rol_empresa": "admin",
  "exp": "7 días"
}
```

---

## 5. Cómo agregar una nueva empresa

### Paso 1: Insertar en `ia_empresas`
```sql
INSERT INTO ia_service_os.ia_empresas
  (uid, nombre, siglas, estado, usuario_creacion, usuario_ult_mod)
VALUES
  ('nueva_emp_1', 'Nombre de la Empresa', 'NE', 'activo',
   'larevo1111@gmail.com', 'larevo1111@gmail.com');
```

**Convención de uid**: lowercase, guiones bajos, máx 50 chars. Ej: `la_tierra_3`, `farmacia_os_1`.

### Paso 2: Crear tipos de consulta para la empresa (opcional)
Si la empresa necesita tipos de consulta diferentes a los globales:
```sql
INSERT INTO ia_service_os.ia_tipos_consulta
  (slug, nombre, descripcion, pasos, empresa, usuario_creacion, usuario_ult_mod)
VALUES
  ('analisis_datos', 'Análisis de datos', '...', '["enrutar","generar_sql","ejecutar","redactar"]',
   'nueva_emp_1', 'larevo1111@gmail.com', 'larevo1111@gmail.com');
```

### Paso 3: Crear temas RAG para la empresa (desde ia-admin)
1. Ir a `ia.oscomunidad.com/#/contextos`
2. Seleccionar la empresa en el filtro
3. Crear los temas necesarios (comercial, finanzas, etc.)

---

## 6. Cómo agregar un usuario a una empresa

### Paso 1: El usuario debe existir en `ia_usuarios`
Si no existe:
```sql
INSERT INTO ia_service_os.ia_usuarios
  (email, nombre, rol, activo, ultima_empresa, usuario_creacion, usuario_ult_mod)
VALUES
  ('nuevo@email.com', 'Nombre Completo', 'viewer', 1,
   'ori_sil_2', 'larevo1111@gmail.com', 'larevo1111@gmail.com');
```

**Nota**: El campo `rol` en `ia_usuarios` es el rol del sistema (admin global / viewer). El rol real dentro de cada empresa está en `ia_usuarios_empresas.rol`.

### Paso 2: Asignar a la empresa
```sql
INSERT INTO ia_service_os.ia_usuarios_empresas
  (usuario_email, empresa_uid, rol, activo, usuario_creacion, usuario_ult_mod)
VALUES
  ('nuevo@email.com', 'ori_sil_2', 'editor', 1,
   'larevo1111@gmail.com', 'larevo1111@gmail.com');
```

### Paso 3: Verificar acceso
El usuario podrá iniciar sesión con Google usando el email registrado y verá la empresa asignada.

---

## 7. Cómo cambiar el rol de un usuario en una empresa

```sql
UPDATE ia_service_os.ia_usuarios_empresas
SET rol = 'admin',
    usuario_ult_mod = 'larevo1111@gmail.com'
WHERE usuario_email = 'usuario@email.com'
  AND empresa_uid = 'ori_sil_2';
```

---

## 8. Cómo desactivar acceso de un usuario a una empresa

```sql
UPDATE ia_service_os.ia_usuarios_empresas
SET activo = 0,
    usuario_ult_mod = 'larevo1111@gmail.com'
WHERE usuario_email = 'usuario@email.com'
  AND empresa_uid = 'ori_sil_2';
```

El usuario podrá autenticarse con Google pero NO verá esa empresa en su lista.

---

## 9. Seguridad — reglas no negociables

### Para desarrolladores y agentes IA

1. **`empresa` NUNCA viene del cliente** — siempre se inyecta del JWT en el servidor.
   ```js
   // ❌ MAL — nunca hacer esto:
   const empresa = req.body.empresa

   // ✅ BIEN — siempre así:
   const empresa = req.empresa  // viene del middleware que decodifica el JWT
   ```

2. **Todo SELECT en tabla por-empresa** debe incluir filtro:
   ```sql
   -- ❌ MAL:
   SELECT * FROM ia_temas WHERE slug = 'comercial'

   -- ✅ BIEN:
   SELECT * FROM ia_temas WHERE slug = 'comercial' AND empresa = :empresa
   ```

3. **Todo INSERT** debe incluir empresa + auditoría:
   ```sql
   INSERT INTO ia_temas (empresa, slug, nombre, usuario_creacion, usuario_ult_mod, ...)
   VALUES (:empresa, :slug, :nombre, :usuario_email, :usuario_email, ...)
   ```

4. **Todo UPDATE/DELETE** debe incluir empresa como segundo filtro:
   ```sql
   UPDATE ia_temas SET nombre = :nombre, usuario_ult_mod = :email
   WHERE id = :id AND empresa = :empresa

   DELETE FROM ia_temas WHERE id = :id AND empresa = :empresa
   ```

5. **`ia_agentes`** es la ÚNICA tabla sin filtro empresa — es configuración global del sistema.

---

## 10. Tablas globales vs. tablas por empresa

| Tabla | Alcance | Filtro empresa |
|---|---|---|
| `ia_agentes` | 🌐 Global | NO — es infraestructura compartida |
| `ia_tipos_consulta` | 🌐 Global / 🏢 Por empresa | empresa IS NULL = global; empresa = X = custom |
| `ia_empresas` | 🌐 Global | NO — es el catálogo de empresas |
| `ia_usuarios` | 🌐 Global | NO — usuarios del sistema |
| `ia_usuarios_empresas` | 🏢 Por empresa | Siempre filtrar por empresa_uid |
| `ia_conversaciones` | 🏢 Por empresa | SÍ |
| `ia_logs` | 🏢 Por empresa | SÍ |
| `ia_consumo_diario` | 🏢 Por empresa | SÍ |
| `ia_temas` | 🏢 Por empresa | SÍ |
| `ia_rag_documentos` | 🏢 Por empresa | SÍ |
| `ia_rag_fragmentos` | 🏢 Por empresa | SÍ |

---

## 11. Campos de auditoría obligatorios

Toda tabla por-empresa (y la mayoría de globales) debe tener:

| Campo | Tipo | Valor |
|---|---|---|
| `empresa` | VARCHAR(50) | uid de la empresa (del JWT) |
| `usuario_creacion` | VARCHAR(150) | email del creador (del JWT, en INSERT) |
| `usuario_ult_mod` | VARCHAR(150) | email del último modificador (del JWT, en UPDATE) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

---

## 12. Usuario actual del sistema

| Email | Nombre | Empresa | Rol |
|---|---|---|---|
| `larevo1111@gmail.com` | Santiago | ori_sil_2 | admin |
| `jen@origensilvestre.com` | Jennifer | ori_sil_2 | viewer |

*Actualizar este documento al agregar nuevos usuarios o empresas.*
