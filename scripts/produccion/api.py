"""API FastAPI — Programación de Producción. Puerto 9600."""
import os, sys, jwt
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local

app = FastAPI(title="Producción OS", version="1.0")

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
STATIC_DIR = os.path.join(BASE_DIR, 'produccion', 'dist')

DB_PROD = dict(**cfg_local(), database='os_produccion', cursorclass=pymysql.cursors.DictCursor)
DB_EFFI = dict(**cfg_local(), database='effi_data', cursorclass=pymysql.cursors.DictCursor)
DB_INV  = dict(**cfg_local(), database='os_inventario', cursorclass=pymysql.cursors.DictCursor)

JWT_SECRET = os.environ.get('JWT_SECRET', 'os_secret_dev_change_me')

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def q(db, sql, params=None):
    conn = pymysql.connect(**db)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def exe(db, sql, params=None):
    conn = pymysql.connect(**db)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.lastrowid or cur.rowcount
    finally:
        conn.close()


# ── Modelos ────────────────────────────────────────────────

class SolicitudCreate(BaseModel):
    cod_articulo: str
    nombre_articulo: str
    tipo_articulo: Optional[str] = None
    cantidad: float
    observaciones: Optional[str] = None
    fecha_necesidad: Optional[str] = None
    fecha_programada: Optional[str] = None
    solicitado_por: str


class SolicitudUpdate(BaseModel):
    cod_articulo: Optional[str] = None
    nombre_articulo: Optional[str] = None
    tipo_articulo: Optional[str] = None
    cantidad: Optional[float] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = None
    fecha_necesidad: Optional[str] = None
    fecha_programada: Optional[str] = None
    op_effi: Optional[str] = None


# ── Artículos (desde Effi + tipos desde os_inventario) ────

@app.get("/api/articulos")
def listar_articulos(tipo: Optional[str] = None, q_str: Optional[str] = None):
    """Lista artículos de Effi vigentes con tipo (MP/PP/PT/INS/etc) desde inv_rangos.
    tipo: filtro opcional (PT, PP, MP). Si se omite, devuelve todos.
    q: filtro de búsqueda por nombre o código.
    """
    sql = """
        SELECT e.id AS cod, e.nombre, COALESCE(r.grupo, '') AS tipo,
               COALESCE(r.unidad, '') AS unidad,
               CAST(REPLACE(e.stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,2)) AS stock
        FROM effi_data.zeffi_inventario e
        LEFT JOIN os_inventario.inv_rangos r ON r.id_effi COLLATE utf8mb4_unicode_ci = e.id COLLATE utf8mb4_unicode_ci
        WHERE e.vigencia = 'Vigente'
    """
    params = []
    if tipo:
        sql += " AND r.grupo = %s"
        params.append(tipo)
    if q_str:
        sql += " AND (e.nombre LIKE %s OR e.id LIKE %s)"
        params += [f'%{q_str}%', f'%{q_str}%']
    sql += " ORDER BY e.nombre LIMIT 500"

    rows = q(DB_EFFI, sql, params)
    for r in rows:
        r['stock'] = float(r['stock']) if r['stock'] is not None else 0
    return rows


# ── Solicitudes CRUD ──────────────────────────────────────

@app.get("/api/solicitudes")
def listar_solicitudes(estado: Optional[str] = None, _start: int = 0, _end: int = 100,
                        _sort: Optional[str] = None, _order: Optional[str] = None):
    sql = "SELECT * FROM solicitudes_produccion WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado = %s"
        params.append(estado)

    sort_col = _sort if _sort in ('fecha_solicitud', 'fecha_programada', 'estado', 'cantidad', 'id') else 'fecha_solicitud'
    sort_dir = 'ASC' if _order == 'asc' else 'DESC'
    sql += f" ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s"
    params += [_end - _start, _start]

    rows = q(DB_PROD, sql, params)
    # Conteo total
    total_row = q(DB_PROD, "SELECT COUNT(*) AS n FROM solicitudes_produccion" + (" WHERE estado = %s" if estado else ""),
                  [estado] if estado else [])
    total = total_row[0]['n']

    for r in rows:
        r['cantidad'] = float(r['cantidad']) if r['cantidad'] else 0
        for campo in ('fecha_solicitud', 'fecha_necesidad', 'fecha_programada', 'created_at', 'updated_at'):
            if r.get(campo):
                r[campo] = str(r[campo])

    from fastapi.responses import JSONResponse
    return JSONResponse(content=rows, headers={'X-Total-Count': str(total), 'Access-Control-Expose-Headers': 'X-Total-Count'})


@app.get("/api/solicitudes/{id}")
def obtener_solicitud(id: int):
    rows = q(DB_PROD, "SELECT * FROM solicitudes_produccion WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(404, "Solicitud no encontrada")
    r = rows[0]
    r['cantidad'] = float(r['cantidad']) if r['cantidad'] else 0
    for campo in ('fecha_solicitud', 'fecha_necesidad', 'fecha_programada', 'created_at', 'updated_at'):
        if r.get(campo):
            r[campo] = str(r[campo])
    return r


@app.post("/api/solicitudes")
def crear_solicitud(data: SolicitudCreate):
    new_id = exe(DB_PROD, """
        INSERT INTO solicitudes_produccion
            (cod_articulo, nombre_articulo, tipo_articulo, cantidad, observaciones, fecha_necesidad, fecha_programada, solicitado_por, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'solicitado')
    """, (data.cod_articulo, data.nombre_articulo, data.tipo_articulo, data.cantidad,
          data.observaciones, data.fecha_necesidad, data.fecha_programada, data.solicitado_por))
    return obtener_solicitud(new_id)


@app.patch("/api/solicitudes/{id}")
def actualizar_solicitud(id: int, data: SolicitudUpdate):
    # Validar que existe
    existing = q(DB_PROD, "SELECT estado FROM solicitudes_produccion WHERE id = %s", (id,))
    if not existing:
        raise HTTPException(404, "Solicitud no encontrada")
    estado_actual = existing[0]['estado']

    # Solo permitir editar producto y cantidad si está en 'solicitado'
    if (data.cod_articulo or data.cantidad is not None) and estado_actual != 'solicitado':
        raise HTTPException(400, f"No se puede editar producto/cantidad en estado '{estado_actual}'")

    campos = []
    valores = []
    for k, v in data.model_dump(exclude_none=True).items():
        campos.append(f"{k} = %s")
        valores.append(v)

    if not campos:
        return obtener_solicitud(id)

    valores.append(id)
    exe(DB_PROD, f"UPDATE solicitudes_produccion SET {', '.join(campos)} WHERE id = %s", valores)
    return obtener_solicitud(id)


@app.delete("/api/solicitudes/{id}")
def eliminar_solicitud(id: int):
    exe(DB_PROD, "DELETE FROM solicitudes_produccion WHERE id = %s", (id,))
    return {"ok": True}


# ── Métricas ──────────────────────────────────────────────

@app.get("/api/solicitudes/stats/resumen")
def stats_resumen():
    rows = q(DB_PROD, """
        SELECT estado, COUNT(*) AS n FROM solicitudes_produccion GROUP BY estado
    """)
    return {r['estado']: r['n'] for r in rows}


# ── Servir frontend ───────────────────────────────────────

@app.get("/")
@app.get("/{path:path}")
def serve_frontend(path: str = ""):
    if not os.path.exists(STATIC_DIR):
        return {"ok": True, "msg": "API corriendo. Frontend no compilado aún."}
    # Intentar archivo estático primero
    if path and os.path.exists(os.path.join(STATIC_DIR, path)):
        return FileResponse(os.path.join(STATIC_DIR, path))
    # Fallback a index.html (SPA)
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9600)
