"""
API FastAPI para inventario físico OS.
Puerto 9401. Sirve datos de os_inventario + effi_data + frontend estático.
"""
import os, jwt, uuid, shutil
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import pymysql

app = FastAPI(title="Inventario OS", version="1.0")

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
STATIC_DIR = os.path.join(BASE_DIR, 'inventario', 'static')
FOTOS_DIR = os.path.join(BASE_DIR, 'inventario', 'fotos')
POLITICAS_PATH = os.path.join(BASE_DIR, 'inventario', 'politicas.json')
JWT_SECRET = '30e4cfa02643f4f05b846aab50974c7a5df85b1f05c990b3fe64e297538adbc2'


def verificar_jwt(request: Request):
    """Valida el JWT del header Authorization."""
    auth = request.headers.get('authorization', '')
    token = auth[7:] if auth.startswith('Bearer ') else None
    if not token:
        raise HTTPException(status_code=401, detail='No autenticado')
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expirado')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Token inválido')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_INV = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')
DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')


def db_query(db_config, sql, params=None):
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
    conn.close()
    return rows


def db_execute(db_config, sql, params=None):
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        conn.commit()
        affected = cur.rowcount
    conn.close()
    return affected


def registrar_auditoria(conteo_id, accion, usuario, valor_anterior=None, valor_nuevo=None, detalle=None):
    db_execute(DB_INV, """
        INSERT INTO inv_auditorias (conteo_id, accion, usuario, valor_anterior, valor_nuevo, detalle)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (conteo_id, accion, usuario, str(valor_anterior) if valor_anterior is not None else None,
          str(valor_nuevo) if valor_nuevo is not None else None, detalle))


# === ENDPOINTS ===

@app.get("/api/inventario/politicas")
def obtener_politicas():
    """Retorna las políticas de acceso."""
    import json as _json
    with open(POLITICAS_PATH, 'r') as f:
        return _json.load(f)


@app.get("/api/inventario/fechas")
def listar_fechas():
    """Lista las fechas de inventario disponibles."""
    rows = db_query(DB_INV, """
        SELECT fecha_inventario,
               COUNT(*) as total,
               SUM(CASE WHEN excluido=0 THEN 1 ELSE 0 END) as inventariables,
               SUM(CASE WHEN estado='contado' THEN 1 ELSE 0 END) as contados,
               SUM(CASE WHEN estado='contado' AND diferencia != 0 THEN 1 ELSE 0 END) as con_diferencia
        FROM inv_conteos
        GROUP BY fecha_inventario
        ORDER BY fecha_inventario DESC
    """)
    for r in rows:
        r['fecha_inventario'] = str(r['fecha_inventario'])
    return rows


@app.get("/api/inventario/bodegas")
def listar_bodegas(fecha: str):
    """Lista bodegas con conteo de artículos para una fecha de inventario."""
    rows = db_query(DB_INV, """
        SELECT bodega,
               COUNT(*) as total,
               SUM(CASE WHEN estado='contado' THEN 1 ELSE 0 END) as contados,
               SUM(CASE WHEN estado='contado' AND diferencia != 0 THEN 1 ELSE 0 END) as con_diferencia
        FROM inv_conteos
        WHERE fecha_inventario = %s AND excluido = 0
        GROUP BY bodega
        ORDER BY total DESC
    """, (fecha,))
    return rows


BODEGAS_TODAS = [
    'Principal', 'Jenifer', 'Santiago', 'Ricardo', 'Mercado Libre',
    'Villa de Aburra', 'Apica', 'El Salvador', 'Feria Santa Elena',
    'Don Luis San Miguel', 'La Tierrita', 'Reginaldo',
    'Desarrollo de Producto', 'Productos No Conformes', 'Feria Campesina San Carlos'
]


@app.get("/api/inventario/bodegas/todas")
def listar_todas_bodegas(fecha: str):
    """Lista TODAS las bodegas (con y sin artículos) para una fecha."""
    rows = db_query(DB_INV, """
        SELECT bodega,
               COUNT(*) as total,
               SUM(CASE WHEN estado='contado' THEN 1 ELSE 0 END) as contados,
               SUM(CASE WHEN estado='contado' AND diferencia != 0 THEN 1 ELSE 0 END) as con_diferencia
        FROM inv_conteos
        WHERE fecha_inventario = %s AND excluido = 0
        GROUP BY bodega
    """, (fecha,))

    bodegas_con_data = {r['bodega']: r for r in rows}
    resultado = []
    for nombre in BODEGAS_TODAS:
        if nombre in bodegas_con_data:
            resultado.append(bodegas_con_data[nombre])
        else:
            resultado.append({'bodega': nombre, 'total': 0, 'contados': 0, 'con_diferencia': 0})
    return resultado


@app.get("/api/inventario/articulos")
def listar_articulos(fecha: str, bodega: Optional[str] = None, filtro: Optional[str] = None, busqueda: Optional[str] = None):
    """Lista artículos para contar en una bodega/fecha. Sin bodega = todas."""
    sql = """
        SELECT c.id, c.id_effi, c.cod_barras, c.nombre, c.categoria, c.bodega,
               c.inventario_teorico, c.inventario_fisico, c.diferencia,
               c.costo_promedio, c.estado, c.contado_por, c.fecha_conteo, c.notas, c.foto,
               r.grupo, r.unidad, r.rango_min, r.rango_max, r.factor_error
        FROM inv_conteos c
        LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
        WHERE c.fecha_inventario = %s AND c.excluido = 0
    """
    params = [fecha]

    if bodega:
        sql += " AND c.bodega = %s"
        params.append(bodega)

    if filtro == 'pendientes':
        sql += " AND c.estado = 'pendiente'"
    elif filtro == 'contados':
        sql += " AND c.estado = 'contado'"
    elif filtro == 'diferencias':
        sql += " AND c.estado = 'contado' AND c.diferencia != 0"

    if busqueda:
        sql += " AND (c.nombre LIKE %s OR c.id_effi LIKE %s OR c.cod_barras LIKE %s)"
        like = f"%{busqueda}%"
        params.extend([like, like, like])

    sql += " ORDER BY c.categoria, c.nombre"
    rows = db_query(DB_INV, sql, params)

    for r in rows:
        r['inventario_teorico'] = float(r['inventario_teorico']) if r['inventario_teorico'] is not None else None
        r['inventario_fisico'] = float(r['inventario_fisico']) if r['inventario_fisico'] is not None else None
        r['diferencia'] = float(r['diferencia']) if r['diferencia'] is not None else None
        r['costo_promedio'] = float(r['costo_promedio']) if r['costo_promedio'] is not None else 0
        r['fecha_conteo'] = str(r['fecha_conteo']) if r['fecha_conteo'] else None
        r['rango_min'] = float(r['rango_min']) if r['rango_min'] is not None else None
        r['rango_max'] = float(r['rango_max']) if r['rango_max'] is not None else None
        r['factor_error'] = int(r['factor_error']) if r['factor_error'] else None
    return rows


class ConteoUpdate(BaseModel):
    inventario_fisico: float
    contado_por: str


@app.put("/api/inventario/articulos/{id}/conteo")
def registrar_conteo(id: int, data: ConteoUpdate):
    """Registra el conteo físico de un artículo."""
    rows = db_query(DB_INV, "SELECT inventario_teorico, inventario_fisico, contado_por FROM inv_conteos WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    anterior = rows[0]
    teorico = float(anterior['inventario_teorico'] or 0)
    fisico_anterior = anterior['inventario_fisico']
    diferencia = data.inventario_fisico - teorico

    accion = 'edicion' if fisico_anterior is not None else 'conteo'
    registrar_auditoria(id, accion, data.contado_por, fisico_anterior, data.inventario_fisico,
                        f"Contado por {anterior['contado_por']}" if accion == 'edicion' and anterior['contado_por'] else None)

    db_execute(DB_INV, """
        UPDATE inv_conteos
        SET inventario_fisico = %s,
            diferencia = %s,
            estado = 'contado',
            contado_por = %s,
            fecha_conteo = NOW()
        WHERE id = %s
    """, (data.inventario_fisico, diferencia, data.contado_por, id))

    return {"ok": True, "diferencia": diferencia}


class NotaUpdate(BaseModel):
    notas: str
    usuario: Optional[str] = 'sistema'


@app.put("/api/inventario/articulos/{id}/nota")
def actualizar_nota(id: int, data: NotaUpdate):
    """Agrega o actualiza nota de un artículo."""
    rows = db_query(DB_INV, "SELECT notas FROM inv_conteos WHERE id = %s", (id,))
    anterior = rows[0]['notas'] if rows else None
    db_execute(DB_INV, "UPDATE inv_conteos SET notas = %s WHERE id = %s", (data.notas, id))
    registrar_auditoria(id, 'nota', data.usuario, anterior, data.notas)
    return {"ok": True}


@app.post("/api/inventario/articulos/{id}/foto")
async def subir_foto(id: int, usuario: str = Form(...), file: UploadFile = File(...)):
    """Sube una foto para un artículo."""
    ext = os.path.splitext(file.filename)[1] or '.jpg'
    nombre = f"{id}_{uuid.uuid4().hex[:8]}{ext}"
    ruta = os.path.join(FOTOS_DIR, nombre)

    with open(ruta, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    db_execute(DB_INV, "UPDATE inv_conteos SET foto = %s WHERE id = %s", (nombre, id))
    registrar_auditoria(id, 'foto', usuario, None, nombre)
    return {"ok": True, "foto": nombre}


@app.get("/api/inventario/fotos/{nombre}")
def obtener_foto(nombre: str):
    """Sirve una foto."""
    ruta = os.path.join(FOTOS_DIR, nombre)
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    return FileResponse(ruta)


class ArticuloAgregar(BaseModel):
    fecha_inventario: str
    bodega: str
    id_effi: str
    contado_por: str


@app.post("/api/inventario/articulos/agregar")
def agregar_articulo(data: ArticuloAgregar):
    """Agrega un artículo a una bodega (hallazgo durante conteo)."""
    # Buscar datos del artículo en effi_data
    rows = db_query(DB_EFFI, """
        SELECT id, cod_barras, nombre, categoria,
               CAST(REPLACE(COALESCE(costo_promedio,'0'), ',', '.') AS DECIMAL(12,2)) AS costo_promedio
        FROM zeffi_inventario
        WHERE id = %s AND vigencia = 'Vigente'
    """, (data.id_effi,))

    if not rows:
        raise HTTPException(status_code=404, detail="Artículo no encontrado en Effi")

    art = rows[0]

    # Verificar que no exista ya
    existing = db_query(DB_INV, """
        SELECT id FROM inv_conteos
        WHERE fecha_inventario = %s AND bodega = %s AND id_effi = %s
    """, (data.fecha_inventario, data.bodega, data.id_effi))

    if existing:
        raise HTTPException(status_code=409, detail="El artículo ya existe en esta bodega")

    db_execute(DB_INV, """
        INSERT INTO inv_conteos
            (fecha_inventario, bodega, id_effi, cod_barras, nombre, categoria,
             excluido, inventario_teorico, costo_promedio, estado)
        VALUES (%s, %s, %s, %s, %s, %s, 0, 0, %s, 'pendiente')
    """, (data.fecha_inventario, data.bodega, data.id_effi,
          art['cod_barras'], art['nombre'], art['categoria'], art['costo_promedio']))

    return {"ok": True, "nombre": art['nombre']}


@app.get("/api/inventario/articulos/buscar")
def buscar_articulos_effi(q: str):
    """Busca artículos en el catálogo de Effi (para agregar a bodega)."""
    rows = db_query(DB_EFFI, """
        SELECT id, cod_barras, nombre, categoria
        FROM zeffi_inventario
        WHERE vigencia = 'Vigente'
          AND (nombre LIKE %s OR id LIKE %s OR cod_barras LIKE %s)
        ORDER BY nombre
        LIMIT 20
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    return rows


@app.get("/api/inventario/resumen")
def resumen_inventario(fecha: str, bodega: Optional[str] = None):
    """Resumen de progreso. Sin bodega = todas."""
    sql = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN estado='contado' THEN 1 ELSE 0 END) as contados,
            SUM(CASE WHEN estado='pendiente' THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN estado='contado' AND diferencia = 0 THEN 1 ELSE 0 END) as ok,
            SUM(CASE WHEN estado='contado' AND diferencia != 0 THEN 1 ELSE 0 END) as con_diferencia
        FROM inv_conteos
        WHERE fecha_inventario = %s AND excluido = 0
    """
    params = [fecha]
    if bodega:
        sql += " AND bodega = %s"
        params.append(bodega)
    rows = db_query(DB_INV, sql, params)
    return rows[0] if rows else {}


# === GESTIÓN DE INVENTARIOS (nivel >= 5) ===

class NuevoInventario(BaseModel):
    fecha_inventario: str
    usuario: str


@app.post("/api/inventario/nuevo")
def crear_inventario(data: NuevoInventario):
    """Crea un nuevo evento de inventario ejecutando el depurador."""
    import subprocess
    result = subprocess.run(
        ['python3', os.path.join(BASE_DIR, 'scripts/inventario/depurar_inventario.py'),
         '--fecha', data.fecha_inventario],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or 'Error al crear inventario')

    registrar_auditoria(0, 'nuevo_inventario', data.usuario, None, data.fecha_inventario,
                        f'Inventario creado para {data.fecha_inventario}')
    return {"ok": True, "output": result.stdout}


class GestionInventario(BaseModel):
    fecha_inventario: str
    usuario: str


@app.post("/api/inventario/reiniciar")
def reiniciar_inventario(data: GestionInventario):
    """Reinicia conteos de un inventario (borra conteos, mantiene artículos)."""
    affected = db_execute(DB_INV, """
        UPDATE inv_conteos
        SET inventario_fisico = NULL, diferencia = NULL, estado = 'pendiente',
            contado_por = NULL, fecha_conteo = NULL, notas = NULL, foto = NULL
        WHERE fecha_inventario = %s AND excluido = 0
    """, (data.fecha_inventario,))
    registrar_auditoria(0, 'reiniciar_inventario', data.usuario, None, data.fecha_inventario,
                        f'{affected} conteos reiniciados')
    return {"ok": True, "reiniciados": affected}


@app.post("/api/inventario/eliminar")
def eliminar_inventario(data: GestionInventario):
    """Elimina un inventario completo (todas las filas de esa fecha)."""
    affected = db_execute(DB_INV, "DELETE FROM inv_conteos WHERE fecha_inventario = %s", (data.fecha_inventario,))
    registrar_auditoria(0, 'eliminar_inventario', data.usuario, None, data.fecha_inventario,
                        f'{affected} filas eliminadas')
    return {"ok": True, "eliminados": affected}


@app.post("/api/inventario/cerrar")
def cerrar_inventario(data: GestionInventario):
    """Cierra un inventario (marca estado = 'cerrado' en pendientes)."""
    affected = db_execute(DB_INV, """
        UPDATE inv_conteos
        SET estado = 'verificado'
        WHERE fecha_inventario = %s AND excluido = 0 AND estado = 'contado'
    """, (data.fecha_inventario,))
    registrar_auditoria(0, 'cerrar_inventario', data.usuario, None, data.fecha_inventario,
                        f'{affected} conteos verificados/cerrados')
    return {"ok": True, "cerrados": affected}


# Servir frontend estático (después de todas las rutas /api/)
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """SPA fallback — sirve index.html para cualquier ruta no-API."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9401)
