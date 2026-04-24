-- =====================================================================
-- Migración: Módulo "Órdenes de Producción" en Sistema Gestión
-- Fecha: 2026-04-24
-- Plan: .agent/planes/activos/PLAN_MODULO_OP_GESTION_2026-04-24.md
-- BD: os_gestion (VPS Contabo)
-- =====================================================================
-- Ejecutar POR PARTES (ver comentarios). Cada bloque es independiente
-- para permitir rollback parcial en caso de error.
-- =====================================================================

-- =====================================================================
-- PARTE 1/7 — Catálogo fijo de categorías de producción (12 seeds)
-- =====================================================================
CREATE TABLE IF NOT EXISTS g_categorias_produccion (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE,
  orden  INT NOT NULL DEFAULT 0,
  activa TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO g_categorias_produccion (nombre, orden) VALUES
  ('Alistamiento',   1),
  ('Templado',       2),
  ('Enmoldado',      3),
  ('Empaque',        4),
  ('Etiquetado',     5),
  ('Sellado',        6),
  ('Esterilización', 7),
  ('Pasteurización', 8),
  ('Encordonado',    9),
  ('Loteado',       10),
  ('Limpieza',      11),
  ('Otra',          99);


-- =====================================================================
-- PARTE 2/7 — Líneas de materiales + productos (consolidadas por OP)
-- =====================================================================
CREATE TABLE IF NOT EXISTS g_op_lineas (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  id_op            VARCHAR(50) NOT NULL,
  empresa          VARCHAR(64) NOT NULL,
  tipo             ENUM('material','producto') NOT NULL,
  cod_articulo     VARCHAR(50) NOT NULL,
  descripcion      VARCHAR(500),
  unidad           VARCHAR(20),
  cantidad_teorica DECIMAL(12,3),
  cantidad_real    DECIMAL(12,3),
  costo_unit       DECIMAL(14,2),
  precio_unit      DECIMAL(14,2),
  es_no_previsto   TINYINT(1) DEFAULT 0,
  usuario_ult_modificacion VARCHAR(255),
  fecha_ult_modificacion   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unq_op_tipo_cod (id_op, empresa, tipo, cod_articulo),
  INDEX idx_op (id_op, empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- PARTE 3/7 — Tiempos consolidados (snapshot al validar la OP)
-- =====================================================================
CREATE TABLE IF NOT EXISTS g_op_tiempos (
  id_op                    VARCHAR(50) NOT NULL,
  empresa                  VARCHAR(64) NOT NULL,
  categoria_produccion_id  INT NOT NULL,
  segundos_totales         INT NOT NULL DEFAULT 0,
  fecha_totalizacion       DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_op, empresa, categoria_produccion_id),
  INDEX idx_cat (categoria_produccion_id),
  FOREIGN KEY (categoria_produccion_id) REFERENCES g_categorias_produccion(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- PARTE 4/7 — Detalle OP (1 fila por OP; lo que Effi NO tiene)
-- =====================================================================
CREATE TABLE IF NOT EXISTS g_op_detalle (
  id_op                   VARCHAR(50) NOT NULL,
  empresa                 VARCHAR(64) NOT NULL,
  observaciones_lote      TEXT NULL,
  procesado_por           VARCHAR(255) NULL,
  procesado_en            DATETIME NULL,
  validado_por            VARCHAR(255) NULL,
  validado_en             DATETIME NULL,
  op_anterior             VARCHAR(50) NULL,
  responsable_validado    VARCHAR(255) NULL,
  fecha_creacion_detalle  DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_modificacion  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id_op, empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- PARTE 5/7 — ALTER g_tareas: +categoria_produccion_id
-- =====================================================================
ALTER TABLE g_tareas ADD COLUMN categoria_produccion_id INT NULL;
ALTER TABLE g_tareas ADD INDEX idx_categoria_produccion (categoria_produccion_id);


-- =====================================================================
-- PARTE 6/7 — ALTER g_tareas: -columnas obsoletas
-- (ejecutar SOLO después de verificar que 5/7 no rompió nada)
-- =====================================================================
ALTER TABLE g_tareas DROP COLUMN tiempo_alistamiento_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_produccion_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_empaque_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_limpieza_min;
ALTER TABLE g_tareas DROP COLUMN id_op_original;


-- =====================================================================
-- PARTE 7/7 — DROP tabla vieja g_tarea_produccion_lineas
-- (Q13: Santi confirmó descartar datos viejos; 26 filas se pierden)
-- =====================================================================
DROP TABLE g_tarea_produccion_lineas;
