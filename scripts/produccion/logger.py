"""
logger.py — Sistema de logs centralizado para el módulo Producción.

Escribe simultáneamente a:
  - Archivo: /home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/produccion.log
  - BD: os_produccion.produccion_logs

Uso:
    from logger import log
    log("sugerir_inicio", cod="241", cantidad=50, ventana=5)
    log("sugerir_fin", cod="241", agente="claude", estado="sugerencia",
        confianza="alta", duracion_ms=12500, detalle={...})
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local

LOG_DIR = Path("/home/osserver/Proyectos_Antigravity/Integraciones_OS/logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "produccion.log"

# Logger a archivo
_file_logger = logging.getLogger("produccion")
if not _file_logger.handlers:
    _file_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
                                            datefmt="%Y-%m-%d %H:%M:%S"))
    _file_logger.addHandler(handler)


def log(evento: str,
        cod: str = None,
        cantidad: float = None,
        ventana: int = None,
        agente: str = None,
        estado: str = None,
        confianza: str = None,
        duracion_ms: int = None,
        detalle=None,
        error: str = None):
    """Escribe un evento de log a archivo + BD."""

    # Serializar detalle a JSON si es dict/list
    detalle_str = json.dumps(detalle, ensure_ascii=False, default=str) if detalle is not None else None

    # 1) Archivo (siempre, aunque la BD falle)
    parts = [f"evt={evento}"]
    if cod: parts.append(f"cod={cod}")
    if cantidad is not None: parts.append(f"cant={cantidad}")
    if ventana is not None: parts.append(f"ventana={ventana}")
    if agente: parts.append(f"agente={agente}")
    if estado: parts.append(f"estado={estado}")
    if confianza: parts.append(f"conf={confianza}")
    if duracion_ms is not None: parts.append(f"dur_ms={duracion_ms}")
    if error: parts.append(f"error={error[:200]}")
    msg = " | ".join(parts)
    if detalle_str:
        msg += f" | detalle={detalle_str[:500]}"
    _file_logger.info(msg)

    # 2) BD (best-effort, no romper si falla)
    try:
        conn = pymysql.connect(**cfg_local(), database="os_produccion")
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO produccion_logs
                   (evento, cod_articulo, cantidad, ventana_op, agente,
                    estado_resultado, confianza, duracion_ms, detalle, error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (evento, cod, cantidad, ventana, agente, estado, confianza,
                 duracion_ms, detalle_str, error[:1000] if error else None)
            )
            conn.commit()
        conn.close()
    except Exception as e:
        _file_logger.warning(f"log_a_bd_fallo: {e}")


def cronometro():
    """Helper para medir duración. Uso:
        with cronometro() as c:
            ...
        c.ms  # duración en ms
    """
    class _Cron:
        def __enter__(self):
            self.t0 = datetime.now()
            return self
        def __exit__(self, *a):
            self.ms = int((datetime.now() - self.t0).total_seconds() * 1000)
    return _Cron()
