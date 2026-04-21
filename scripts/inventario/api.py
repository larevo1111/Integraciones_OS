"""
API FastAPI para inventario físico OS.
Puerto 9401. Sirve datos de os_inventario + effi_data + frontend estático.
"""
import os, re, json, jwt, uuid, shutil, subprocess
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form, BackgroundTasks
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

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib import cfg_local
DB_INV  = dict(**cfg_local(), database='os_inventario')
DB_EFFI = dict(**cfg_local(), database='effi_data')


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
               c.costo_manual, c.estado, c.contado_por, c.fecha_conteo, c.notas, c.foto,
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

    sin_grupo = []
    for r in rows:
        r['inventario_teorico'] = float(r['inventario_teorico']) if r['inventario_teorico'] is not None else None
        r['inventario_fisico'] = float(r['inventario_fisico']) if r['inventario_fisico'] is not None else None
        r['diferencia'] = float(r['diferencia']) if r['diferencia'] is not None else None
        r['costo_manual'] = float(r['costo_manual']) if r['costo_manual'] is not None else 0
        r['fecha_conteo'] = str(r['fecha_conteo']) if r['fecha_conteo'] else None
        r['rango_min'] = float(r['rango_min']) if r['rango_min'] is not None else None
        r['rango_max'] = float(r['rango_max']) if r['rango_max'] is not None else None
        r['factor_error'] = int(r['factor_error']) if r['factor_error'] else None
        # Artículos sin entrada en inv_rangos: detectar grupo y unidad al vuelo
        if not r.get('grupo'):
            sin_grupo.append(r)
            r['unidad'] = detectar_unidad(r.get('nombre') or '')

    # Para los que no tienen grupo, cargar IDs producidos (para detectar PP)
    if sin_grupo:
        ids_producidos = set()
        try:
            prods = db_query(DB_EFFI, "SELECT DISTINCT cod_articulo FROM zeffi_articulos_producidos WHERE vigencia = 'Orden vigente'")
            ids_producidos = {str(p['cod_articulo']) for p in prods}
        except Exception:
            pass

        for r in sin_grupo:
            if r.get('id_effi', '').startswith('NM-'):
                r['grupo'] = 'NM'
            else:
                cat = (r.get('categoria') or '').upper()
                nom = (r.get('nombre') or '').upper()
                if 'DESPERDICIO' in nom or 'DESPERDI' in nom:
                    r['grupo'] = 'DES'
                elif cat.startswith('NO MATRICULADO'):
                    r['grupo'] = 'NM'
                elif cat.startswith('TPT'):
                    r['grupo'] = 'PT'
                elif cat.startswith('T03'):
                    r['grupo'] = 'INS'
                elif 'DESARROLLO' in cat:
                    r['grupo'] = 'DS'
                elif str(r.get('id_effi', '')) in ids_producidos:
                    r['grupo'] = 'PP'
                else:
                    r['grupo'] = 'MP'

    return rows


class ConteoUpdate(BaseModel):
    inventario_fisico: float
    contado_por: str


def verificar_bloqueo(fecha_inventario, accion='conteo'):
    """Verifica si una acción está permitida según el estado de cierre.
    accion: 'conteo' (bloqueado por cerrar-conteo) o 'gestion' (bloqueado por cerrar-inventario).
    Lanza HTTPException 423 si está bloqueado.
    """
    rows = db_query(DB_INV, "SELECT conteo_cerrado_en, inventario_cerrado_en FROM inv_fechas WHERE fecha_inventario = %s", (fecha_inventario,))
    if not rows:
        return  # Sin registro = abierto
    r = rows[0]
    if r['inventario_cerrado_en']:
        raise HTTPException(423, "Inventario cerrado completamente — no se pueden hacer cambios")
    if accion == 'conteo' and r['conteo_cerrado_en']:
        raise HTTPException(423, "Conteo físico cerrado — no se pueden modificar conteos")


@app.put("/api/inventario/articulos/{id}/conteo")
def registrar_conteo(id: int, data: ConteoUpdate):
    """Registra el conteo físico de un artículo."""
    rows = db_query(DB_INV, "SELECT inventario_teorico, inventario_fisico, contado_por, fecha_inventario FROM inv_conteos WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    verificar_bloqueo(rows[0]['fecha_inventario'], 'conteo')

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
               CAST(REPLACE(COALESCE(costo_manual,'0'), ',', '.') AS DECIMAL(12,2)) AS costo_manual
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
             excluido, inventario_teorico, costo_manual, estado)
        VALUES (%s, %s, %s, %s, %s, %s, 0, 0, %s, 'pendiente')
    """, (data.fecha_inventario, data.bodega, data.id_effi,
          art['cod_barras'], art['nombre'], art['categoria'], art['costo_manual']))

    return {"ok": True, "nombre": art['nombre']}


@app.get("/api/inventario/excluidos")
def listar_excluidos(fecha: str):
    """Lista artículos excluidos de un inventario."""
    rows = db_query(DB_INV, """
        SELECT id, id_effi, nombre, categoria, razon_exclusion
        FROM inv_conteos
        WHERE fecha_inventario = %s AND excluido = 1
        ORDER BY nombre
    """, (fecha,))
    return rows


class ReactivarArticulo(BaseModel):
    usuario: str


@app.put("/api/inventario/articulos/{id}/reactivar")
def reactivar_articulo(id: int, data: ReactivarArticulo):
    """Reactiva un artículo excluido (lo pone inventariable)."""
    db_execute(DB_INV, """
        UPDATE inv_conteos
        SET excluido = 0, razon_exclusion = NULL, inventario_teorico = 0,
            bodega = COALESCE(NULLIF(bodega, '—'), 'Principal')
        WHERE id = %s
    """, (id,))
    registrar_auditoria(id, 'reactivar', data.usuario, 'excluido', 'inventariable')
    return {"ok": True}


@app.post("/api/inventario/articulos/no-matriculado")
async def agregar_no_matriculado(
    fecha_inventario: str = Form(...),
    bodega: str = Form(...),
    nombre: str = Form(...),
    unidad: str = Form(...),
    cantidad: float = Form(...),
    costo: float = Form(0),
    notas: str = Form(''),
    usuario: str = Form(...),
    foto: Optional[UploadFile] = File(None)
):
    """Agrega un artículo no matriculado en Effi."""
    foto_nombre = None
    if foto:
        ext = os.path.splitext(foto.filename)[1] or '.jpg'
        foto_nombre = f"nm_{uuid.uuid4().hex[:8]}{ext}"
        ruta = os.path.join(FOTOS_DIR, foto_nombre)
        with open(ruta, 'wb') as f:
            shutil.copyfileobj(foto.file, f)

    conn = pymysql.connect(**DB_INV)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO inv_conteos
                (fecha_inventario, bodega, id_effi, nombre, categoria,
                 excluido, inventario_teorico, inventario_fisico, diferencia,
                 costo_manual, estado, contado_por, fecha_conteo, notas, foto)
            VALUES (%s, %s, %s, %s, %s, 0, 0, %s, %s, %s, 'contado', %s, NOW(), %s, %s)
        """, (fecha_inventario, bodega, f'NM-{uuid.uuid4().hex[:6]}', nombre,
              f'NO MATRICULADO ({unidad})', cantidad, cantidad, costo,
              usuario, notas or f'Artículo no matriculado. Unidad: {unidad}', foto_nombre))
        new_id = cur.lastrowid
        conn.commit()
    conn.close()

    registrar_auditoria(new_id, 'no_matriculado', usuario, None, f'{nombre} ({cantidad} {unidad})',
                        f'Artículo no matriculado en Effi')
    return {"ok": True, "id": new_id}


def detectar_unidad(nombre):
    """Detecta unidad de medida del nombre del artículo (misma lógica que calcular_rangos.py)."""
    n = (nombre or '').upper()
    if re.search(r'\bX\s*KG\b|\bKG\b|\bX\s*KILO\b|\bKILO\b|\bKL\b', n):
        return 'KG'
    if re.search(r'\bGRS?\b|\bGRAMOS?\b|\b\d+\s*GRS?\b|\b\d+\s*G\b', n):
        return 'GRS'
    if re.search(r'\bLT\b|\bLITRO\b|\bLTS\b|\bX\s*LT\b', n):
        return 'LT'
    if re.search(r'\bML\b|\bMILILITROS?\b', n):
        return 'ML'
    return 'UND'


@app.get("/api/inventario/articulos/buscar")
def buscar_articulos_effi(q: str):
    """Busca artículos en inv_catalogo_articulos (local, con unidad y grupo precalculados)."""
    rows = db_query(DB_EFFI, """
        SELECT id_effi AS id, cod_barras, nombre, categoria, unidad, grupo
        FROM inv_catalogo_articulos
        WHERE (nombre LIKE %s OR id_effi LIKE %s OR cod_barras LIKE %s)
        ORDER BY nombre
        LIMIT 20
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    return rows


class AsignarArticulo(BaseModel):
    conteo_id: int
    id_effi_nuevo: str
    nombre_effi: str
    categoria_effi: str = ''
    cod_barras: str = ''
    usuario: str


@app.post("/api/inventario/articulos/asignar")
def asignar_no_matriculado(data: AsignarArticulo):
    """Vincula un artículo NM con un artículo real de Effi."""
    conn = pymysql.connect(**DB_INV, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        # Verificar que el conteo existe y es NM
        cur.execute("SELECT id, id_effi, nombre, categoria, notas FROM inv_conteos WHERE id = %s", (data.conteo_id,))
        conteo = cur.fetchone()
        if not conteo:
            conn.close()
            raise HTTPException(404, 'Conteo no encontrado')
        if not conteo['id_effi'].startswith('NM-'):
            conn.close()
            raise HTTPException(400, 'Solo se pueden asignar artículos no matriculados')

        nombre_anterior = conteo['nombre']
        id_anterior = conteo['id_effi']
        unidad_anterior = detectar_unidad(nombre_anterior)
        unidad_effi = detectar_unidad(data.nombre_effi)

        # Nota de asignación
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M')
        nota = (
            f"[Asignación {ahora} por {data.usuario}]\n"
            f"Antes: {id_anterior} — {nombre_anterior} ({unidad_anterior})\n"
            f"Asignado a: {data.id_effi_nuevo} — {data.nombre_effi} ({unidad_effi})\n"
            f"Categoría Effi: {data.categoria_effi or '—'}"
        )
        # Preservar nota existente si la hay
        nota_final = f"{conteo['notas']}\n\n{nota}" if conteo.get('notas') else nota

        # Actualizar el conteo con los datos del artículo Effi + nota
        cur.execute("""
            UPDATE inv_conteos
            SET id_effi = %s, nombre = %s, categoria = %s, cod_barras = %s, notas = %s
            WHERE id = %s
        """, (data.id_effi_nuevo, data.nombre_effi, data.categoria_effi, data.cod_barras, nota_final, data.conteo_id))
        conn.commit()

    conn.close()

    registrar_auditoria(data.conteo_id, 'asignacion', data.usuario,
                        f'{id_anterior} — {nombre_anterior}',
                        f'{data.id_effi_nuevo} — {data.nombre_effi}',
                        'Artículo no matriculado asignado a artículo Effi')
    return {"ok": True}


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


class GestionInventario(BaseModel):
    fecha_inventario: str
    usuario: str


# === INVENTARIO TEÓRICO ===

@app.post("/api/inventario/calcular-teorico")
def calcular_teorico(data: GestionInventario):
    """Calcula inventario teórico a fecha de corte (nivel >= 5)."""
    import subprocess
    result = subprocess.run(
        ['python3', os.path.join(BASE_DIR, 'scripts/inventario/calcular_inventario_teorico.py'),
         '--fecha', data.fecha_inventario],
        capture_output=True, text=True, cwd=BASE_DIR, timeout=120
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or 'Error al calcular teórico')

    registrar_auditoria(0, 'calcular_teorico', data.usuario, None, data.fecha_inventario,
                        f'Inventario teórico calculado para {data.fecha_inventario}')
    return {"ok": True, "output": result.stdout}


@app.get("/api/inventario/teorico/estado")
def estado_teorico(fecha: str):
    """Retorna info del último cálculo teórico para una fecha."""
    rows = db_query(DB_INV, """
        SELECT calculado_en, ops_generadas_count,
               COUNT(*) as articulos
        FROM inv_teorico
        WHERE fecha_corte = %s
        GROUP BY calculado_en, ops_generadas_count
    """, (fecha,))
    if not rows:
        return {"calculado": False}
    r = rows[0]
    r['calculado'] = True
    r['calculado_en'] = str(r['calculado_en']) if r['calculado_en'] else None
    return r


# === GESTIÓN DE INVENTARIOS (nivel >= 5) ===

class NuevoInventario(BaseModel):
    fecha_inventario: str
    usuario: str
    tipo: str = 'completo'  # 'completo' o 'parcial'
    articulos: Optional[list] = None  # lista de id_effi para parcial


@app.get("/api/inventario/sugerir-articulos")
def sugerir_articulos(cantidad: int = 15):
    """Sugiere artículos para inventario parcial con criterios inteligentes."""
    import random

    # 1. Artículos con mayor diferencia en el último inventario
    ultima_fecha = db_query(DB_INV, "SELECT MAX(fecha_inventario) AS f FROM inv_conteos")[0]['f']
    con_diferencia = []
    if ultima_fecha:
        con_diferencia = db_query(DB_INV, """
            SELECT c.id_effi, c.nombre, c.categoria, c.bodega, c.costo_manual,
                   c.inventario_fisico, c.inventario_teorico, c.diferencia,
                   COALESCE(r.grupo,'') AS grupo
            FROM inv_conteos c
            LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
            WHERE c.fecha_inventario = %s AND c.excluido = 0 AND c.bodega = 'Principal'
              AND c.diferencia IS NOT NULL AND ROUND(c.diferencia, 2) != 0
            ORDER BY ABS(c.diferencia * COALESCE(c.costo_manual, 0)) DESC
        """, (ultima_fecha,))

    # 2. Artículos con mayor valor de stock (alto riesgo económico)
    alto_valor = db_query(DB_INV, """
        SELECT c.id_effi, c.nombre, c.categoria, c.bodega, c.costo_manual,
               c.inventario_fisico, c.inventario_teorico, c.diferencia,
               COALESCE(r.grupo,'') AS grupo
        FROM inv_conteos c
        LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
        WHERE c.fecha_inventario = %s AND c.excluido = 0 AND c.bodega = 'Principal'
          AND c.inventario_fisico IS NOT NULL AND c.inventario_fisico > 0
        ORDER BY c.inventario_fisico * COALESCE(c.costo_manual, 0) DESC
    """, (ultima_fecha,)) if ultima_fecha else []

    # Construir lista priorizada sin duplicados
    seleccionados = {}
    def agregar(art, razon, prioridad):
        eid = art['id_effi']
        if eid not in seleccionados or prioridad < seleccionados[eid]['prioridad']:
            seleccionados[eid] = {
                'id_effi': eid, 'nombre': art['nombre'], 'categoria': art['categoria'] or '',
                'grupo': art['grupo'], 'costo_manual': float(art['costo_manual'] or 0),
                'razon': razon, 'prioridad': prioridad, 'seleccionado': True
            }

    # Criterio 1: top diferencias (40% del cupo)
    cupo_dif = max(1, int(cantidad * 0.4))
    for a in con_diferencia[:cupo_dif]:
        dif = float(a['diferencia'] or 0)
        imp = abs(dif * float(a['costo_manual'] or 0))
        agregar(a, f'Diferencia alta: {dif:+.1f} (${imp:,.0f})', 1)

    # Criterio 2: alto valor económico (30% del cupo)
    cupo_val = max(1, int(cantidad * 0.3))
    added = 0
    for a in alto_valor:
        if a['id_effi'] not in seleccionados and added < cupo_val:
            val = float(a['inventario_fisico'] or 0) * float(a['costo_manual'] or 0)
            agregar(a, f'Alto valor: ${val:,.0f}', 2)
            added += 1

    # Criterio 3: aleatorios para completar (30% restante), distribuidos por grupo
    if ultima_fecha:
        todos = db_query(DB_INV, """
            SELECT c.id_effi, c.nombre, c.categoria, c.bodega, c.costo_manual,
                   c.inventario_fisico, c.inventario_teorico, c.diferencia,
                   COALESCE(r.grupo,'') AS grupo
            FROM inv_conteos c
            LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
            WHERE c.fecha_inventario = %s AND c.excluido = 0 AND c.bodega = 'Principal'
              AND c.inventario_fisico IS NOT NULL
        """, (ultima_fecha,))
        disponibles = [a for a in todos if a['id_effi'] not in seleccionados]
        random.shuffle(disponibles)
        faltantes = cantidad - len(seleccionados)
        for a in disponibles[:max(0, faltantes)]:
            agregar(a, 'Verificación aleatoria', 3)

    result = sorted(seleccionados.values(), key=lambda x: x['prioridad'])
    return result[:cantidad]


@app.post("/api/inventario/nuevo")
def crear_inventario(data: NuevoInventario):
    """Crea un nuevo evento de inventario (completo o parcial)."""
    if data.tipo == 'completo':
        import subprocess
        result = subprocess.run(
            ['python3', os.path.join(BASE_DIR, 'scripts/inventario/depurar_inventario.py'),
             '--fecha', data.fecha_inventario],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr or 'Error al crear inventario')
        registrar_auditoria(0, 'nuevo_inventario', data.usuario, None, data.fecha_inventario,
                            f'Inventario COMPLETO creado para {data.fecha_inventario}')
        return {"ok": True, "output": result.stdout}

    # Parcial: crear solo los artículos seleccionados
    if not data.articulos or len(data.articulos) == 0:
        raise HTTPException(400, 'Debe seleccionar al menos un artículo para inventario parcial')

    placeholders = ','.join(['%s'] * len(data.articulos))
    arts = db_query(DB_EFFI, f"""
        SELECT id, cod_barras, nombre, categoria,
               CAST(REPLACE(COALESCE(costo_manual,'0'),',','.') AS DECIMAL(12,2)) AS costo_manual,
               CAST(REPLACE(COALESCE(stock_bodega_principal_sucursal_principal,'0'),',','.') AS DECIMAL(12,2)) AS stock
        FROM zeffi_inventario WHERE id IN ({placeholders}) AND vigencia = 'Vigente'
    """, data.articulos)

    if not arts:
        raise HTTPException(404, 'No se encontraron artículos válidos')

    # Limpiar filas previas de esta fecha (si se re-crea)
    db_execute(DB_INV, "DELETE FROM inv_conteos WHERE fecha_inventario = %s", (data.fecha_inventario,))

    for a in arts:
        stock = float(a['stock'] or 0)
        db_execute(DB_INV, """
            INSERT INTO inv_conteos
                (fecha_inventario, bodega, id_effi, cod_barras, nombre, categoria,
                 excluido, inventario_teorico, costo_manual, estado)
            VALUES (%s, 'Principal', %s, %s, %s, %s, 0, %s, %s, 'pendiente')
        """, (data.fecha_inventario, a['id'], a['cod_barras'], a['nombre'],
              a['categoria'], stock, a['costo_manual']))

    registrar_auditoria(0, 'nuevo_inventario', data.usuario, None, data.fecha_inventario,
                        f'Inventario PARCIAL creado: {len(arts)} artículos')
    return {"ok": True, "articulos": len(arts)}


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


@app.post("/api/inventario/cerrar-conteo")
def cerrar_conteo(data: GestionInventario):
    """Cierra el conteo físico. Bloquea la edición de cantidades pero permite gestión."""
    # Verificar que no esté ya cerrado
    rows = db_query(DB_INV, "SELECT conteo_cerrado_en FROM inv_fechas WHERE fecha_inventario = %s", (data.fecha_inventario,))
    if rows and rows[0]['conteo_cerrado_en']:
        raise HTTPException(409, "El conteo ya está cerrado")

    # Marcar conteos como verificados
    affected = db_execute(DB_INV, """
        UPDATE inv_conteos
        SET estado = 'verificado'
        WHERE fecha_inventario = %s AND excluido = 0 AND estado = 'contado'
    """, (data.fecha_inventario,))

    # Crear o actualizar registro en inv_fechas
    db_execute(DB_INV, """
        INSERT INTO inv_fechas (fecha_inventario, conteo_cerrado_en, conteo_cerrado_por)
        VALUES (%s, NOW(), %s)
        ON DUPLICATE KEY UPDATE conteo_cerrado_en = NOW(), conteo_cerrado_por = %s
    """, (data.fecha_inventario, data.usuario, data.usuario))

    registrar_auditoria(0, 'cerrar_conteo', data.usuario, None, data.fecha_inventario,
                        f'{affected} conteos verificados — conteo físico bloqueado')
    return {"ok": True, "cerrados": affected}


@app.post("/api/inventario/cerrar-inventario")
def cerrar_inventario_completo(data: GestionInventario):
    """Cierra el inventario completo. Bloquea TODO (incluso la gestión)."""
    rows = db_query(DB_INV, "SELECT conteo_cerrado_en, inventario_cerrado_en FROM inv_fechas WHERE fecha_inventario = %s", (data.fecha_inventario,))
    if not rows or not rows[0]['conteo_cerrado_en']:
        raise HTTPException(400, "Debe cerrar primero el conteo físico antes de cerrar el inventario completo")
    if rows[0]['inventario_cerrado_en']:
        raise HTTPException(409, "El inventario ya está cerrado")

    db_execute(DB_INV, """
        UPDATE inv_fechas
        SET inventario_cerrado_en = NOW(), inventario_cerrado_por = %s
        WHERE fecha_inventario = %s
    """, (data.usuario, data.fecha_inventario))

    registrar_auditoria(0, 'cerrar_inventario', data.usuario, None, data.fecha_inventario,
                        'Inventario cerrado completamente')
    return {"ok": True}


@app.post("/api/inventario/reabrir-conteo")
def reabrir_conteo(data: GestionInventario):
    """Reabre el conteo físico (solo si el inventario completo no está cerrado)."""
    rows = db_query(DB_INV, "SELECT conteo_cerrado_en, inventario_cerrado_en FROM inv_fechas WHERE fecha_inventario = %s", (data.fecha_inventario,))
    if not rows or not rows[0]['conteo_cerrado_en']:
        raise HTTPException(409, "El conteo no está cerrado")
    if rows[0]['inventario_cerrado_en']:
        raise HTTPException(400, "No se puede reabrir el conteo porque el inventario completo está cerrado")

    # Borrar el flag de cierre
    db_execute(DB_INV, """
        UPDATE inv_fechas
        SET conteo_cerrado_en = NULL, conteo_cerrado_por = NULL
        WHERE fecha_inventario = %s
    """, (data.fecha_inventario,))

    # Restaurar estado: los que están 'verificado' vuelven a 'contado' (solo si tienen valor físico)
    affected = db_execute(DB_INV, """
        UPDATE inv_conteos
        SET estado = 'contado'
        WHERE fecha_inventario = %s AND excluido = 0 AND estado = 'verificado' AND inventario_fisico IS NOT NULL
    """, (data.fecha_inventario,))

    registrar_auditoria(0, 'reabrir_conteo', data.usuario, None, data.fecha_inventario,
                        f'Conteo físico reabierto — {affected} conteos restaurados a contado')
    return {"ok": True, "restaurados": affected}


@app.get("/api/inventario/estado-cierre")
def estado_cierre(fecha: str):
    """Devuelve el estado de cierres del inventario."""
    rows = db_query(DB_INV, "SELECT * FROM inv_fechas WHERE fecha_inventario = %s", (fecha,))
    if not rows:
        return {"conteo_cerrado": False, "inventario_cerrado": False}
    r = rows[0]
    return {
        "conteo_cerrado": r['conteo_cerrado_en'] is not None,
        "conteo_cerrado_en": str(r['conteo_cerrado_en']) if r['conteo_cerrado_en'] else None,
        "conteo_cerrado_por": r['conteo_cerrado_por'],
        "inventario_cerrado": r['inventario_cerrado_en'] is not None,
        "inventario_cerrado_en": str(r['inventario_cerrado_en']) if r['inventario_cerrado_en'] else None,
        "inventario_cerrado_por": r['inventario_cerrado_por'],
    }


# Endpoint legacy (redirige al nuevo)
@app.post("/api/inventario/cerrar")
def cerrar_inventario_legacy(data: GestionInventario):
    """DEPRECATED: usar /cerrar-conteo. Mantenido por compatibilidad."""
    return cerrar_conteo(data)


# ── Gestión de inconsistencias ──

CAUSAS_PREDEFINIDAS = [
    'Faltó remisionar o facturar',
    'OP no ejecutada',
    'Error unidades en OP',
    'Error unidades en compra',
    'Faltó registrar compra',
    'Valores incorrectos en OP',
    'Valores incorrectos en despacho',
    'Valores incorrectos en compra',
    'Producto dañado',
    'Obsoleto',
    'Artículo redundante',
    'Otro',
]


class GestionCalcular(BaseModel):
    fecha_inventario: str
    usuario: str


@app.post("/api/inventario/gestion/calcular")
def calcular_gestion(data: GestionCalcular):
    """Pobla/recalcula inv_gestion agregando conteos por artículo para la fecha."""
    # 1. Agregar conteos por artículo (sum de bodegas)
    rows = db_query(DB_INV, """
        SELECT c.id_effi,
               c.nombre,
               GROUP_CONCAT(DISTINCT c.bodega ORDER BY c.bodega) AS bodegas,
               MAX(COALESCE(c.inventario_teorico, 0)) AS total_teorico,
               SUM(COALESCE(c.inventario_fisico, 0)) AS total_fisico,
               SUM(COALESCE(c.inventario_fisico, 0)) - MAX(COALESCE(c.inventario_teorico, 0)) AS total_diferencia,
               MAX(COALESCE(c.costo_manual, 0)) AS costo_manual,
               r.grupo, r.unidad
        FROM inv_conteos c
        LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
        WHERE c.fecha_inventario = %s AND c.excluido = 0 AND c.estado IN ('contado', 'verificado')
        GROUP BY c.id_effi
    """, (data.fecha_inventario,))

    if not rows:
        return {"ok": False, "mensaje": "No hay conteos para esa fecha"}

    # 2. Calcular valor total del inventario (para umbrales de severidad)
    valor_total = sum(abs(float(r['total_teorico'] or 0) * float(r['costo_manual'] or 0)) for r in rows)
    if valor_total == 0:
        valor_total = 1  # evitar division por cero

    # 3. Calcular impacto y severidad por artículo
    conn = pymysql.connect(**DB_INV)
    insertados = 0
    with conn.cursor() as cur:
        cur.execute("DELETE FROM inv_gestion WHERE fecha_inventario = %s", (data.fecha_inventario,))
        for r in rows:
            dif = float(r['total_diferencia'] or 0)
            costo = float(r['costo_manual'] or 0)
            impacto = dif * costo
            pct = abs(impacto) / valor_total * 100 if valor_total > 0 else 0

            if dif == 0:
                severidad = 'ok'
            elif pct >= 2.0:
                severidad = 'critica'
            elif pct >= 0.5:
                severidad = 'significativa'
            else:
                severidad = 'menor'

            # Detectar grupo/unidad al vuelo si no viene de inv_rangos
            grupo = r.get('grupo') or ''
            unidad = r.get('unidad') or detectar_unidad(r['nombre'] or '')
            if not grupo:
                cat_rows = db_query(DB_EFFI, "SELECT categoria FROM inv_catalogo_articulos WHERE id_effi = %s", (r['id_effi'],))
                cat = (cat_rows[0]['categoria'] if cat_rows else '') or ''
                cat_up = cat.upper()
                nom_up = (r['nombre'] or '').upper()
                if 'DESPERDICIO' in nom_up:
                    grupo = 'DES'
                elif r['id_effi'].startswith('NM-'):
                    grupo = 'NM'
                elif cat_up.startswith('TPT'):
                    grupo = 'PT'
                elif cat_up.startswith('T03'):
                    grupo = 'INS'
                elif 'DESARROLLO' in cat_up:
                    grupo = 'DS'
                else:
                    grupo = 'MP'

            bodegas_json = json.dumps(r['bodegas'].split(',')) if r.get('bodegas') else '["—"]'

            cur.execute("""
                INSERT INTO inv_gestion
                    (fecha_inventario, id_effi, nombre, grupo, unidad, bodegas,
                     total_teorico, total_fisico, total_diferencia, costo_manual,
                     impacto_economico, severidad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.fecha_inventario, r['id_effi'], r['nombre'], grupo, unidad, bodegas_json,
                  r['total_teorico'], r['total_fisico'], r['total_diferencia'], costo,
                  round(impacto, 2), severidad))
            insertados += 1

        conn.commit()
    conn.close()

    registrar_auditoria(0, 'gestion_calcular', data.usuario, None, data.fecha_inventario,
                        f'{insertados} artículos procesados, valor total ${valor_total:,.0f}')
    return {"ok": True, "articulos": insertados, "valor_total": round(valor_total, 2)}


@app.get("/api/inventario/gestion/dashboard")
def gestion_dashboard(fecha: str):
    """KPIs + valorización por grupo para el dashboard de gestión."""
    rows = db_query(DB_INV, "SELECT * FROM inv_gestion WHERE fecha_inventario = %s", (fecha,))
    if not rows:
        return {"vacio": True}

    valor_teorico = sum(float(r['total_teorico'] or 0) * float(r['costo_manual'] or 0) for r in rows)
    valor_fisico = sum(float(r['total_fisico'] or 0) * float(r['costo_manual'] or 0) for r in rows)
    impacto_total = sum(float(r['impacto_economico'] or 0) for r in rows)

    con_dif = [r for r in rows if float(r['total_diferencia'] or 0) != 0]
    faltantes = len([r for r in con_dif if float(r['total_diferencia'] or 0) < 0])
    sobrantes = len([r for r in con_dif if float(r['total_diferencia'] or 0) > 0])
    exactos = len(rows) - len(con_dif)

    # Por severidad
    por_severidad = {}
    for sev in ['ok', 'menor', 'significativa', 'critica']:
        items = [r for r in rows if r['severidad'] == sev]
        por_severidad[sev] = {
            'count': len(items),
            'impacto': round(sum(float(r['impacto_economico'] or 0) for r in items), 2)
        }

    # Por grupo
    grupos = {}
    for r in rows:
        g = r['grupo'] or 'SIN'
        if g not in grupos:
            grupos[g] = {'grupo': g, 'total': 0, 'exactos': 0, 'valor_teorico': 0, 'valor_fisico': 0, 'impacto': 0}
        grupos[g]['total'] += 1
        if float(r['total_diferencia'] or 0) == 0:
            grupos[g]['exactos'] += 1
        grupos[g]['valor_teorico'] += float(r['total_teorico'] or 0) * float(r['costo_manual'] or 0)
        grupos[g]['valor_fisico'] += float(r['total_fisico'] or 0) * float(r['costo_manual'] or 0)
        grupos[g]['impacto'] += float(r['impacto_economico'] or 0)

    for g in grupos.values():
        g['valor_teorico'] = round(g['valor_teorico'], 2)
        g['valor_fisico'] = round(g['valor_fisico'], 2)
        g['impacto'] = round(g['impacto'], 2)
        g['pct_exactitud'] = round(g['exactos'] / g['total'] * 100, 1) if g['total'] > 0 else 0

    # Por estado
    por_estado = {}
    for est in ['pendiente', 'analizado', 'justificada', 'requiere_ajuste', 'ajustada']:
        por_estado[est] = len([r for r in rows if r['estado'] == est])

    # Orden de grupos para el informe
    orden_grupos = ['MP', 'INS', 'PP', 'PT', 'DS', 'DES', 'NM', 'SIN']
    grupos_ordenados = sorted(grupos.values(), key=lambda g: orden_grupos.index(g['grupo']) if g['grupo'] in orden_grupos else 99)

    return {
        "valor_teorico": round(valor_teorico, 2),
        "valor_fisico": round(valor_fisico, 2),
        "impacto_total": round(impacto_total, 2),
        "total_articulos": len(rows),
        "con_diferencia": len(con_dif),
        "faltantes": faltantes,
        "sobrantes": sobrantes,
        "exactos": exactos,
        "por_severidad": por_severidad,
        "por_grupo": grupos_ordenados,
        "por_estado": por_estado
    }


# ── Observaciones ──────────────────────────────────

class ObservacionInput(BaseModel):
    fecha_inventario: str
    tipo: str = 'manual'
    descripcion: str
    detalle: Optional[str] = None
    usuario: str = 'sistema'

@app.get("/api/inventario/observaciones")
def listar_observaciones(fecha: str):
    rows = db_query(DB_INV, """
        SELECT id, tipo, descripcion, detalle, registrado_por, created_at
        FROM inv_observaciones WHERE fecha_inventario = %s ORDER BY created_at DESC
    """, (fecha,))
    for r in rows:
        r['created_at'] = str(r['created_at']) if r['created_at'] else None
    return rows

@app.post("/api/inventario/observaciones")
def agregar_observacion(data: ObservacionInput):
    db_execute(DB_INV, """
        INSERT INTO inv_observaciones (fecha_inventario, tipo, descripcion, detalle, registrado_por)
        VALUES (%s, %s, %s, %s, %s)
    """, (data.fecha_inventario, data.tipo, data.descripcion, data.detalle, data.usuario))
    return {"ok": True}

@app.delete("/api/inventario/observaciones/{obs_id}")
def eliminar_observacion(obs_id: int):
    db_execute(DB_INV, "DELETE FROM inv_observaciones WHERE id = %s", (obs_id,))
    return {"ok": True}

def registrar_observacion(fecha, tipo, descripcion, detalle=None, usuario='sistema'):
    """Helper para registrar observaciones automáticas."""
    db_execute(DB_INV, """
        INSERT INTO inv_observaciones (fecha_inventario, tipo, descripcion, detalle, registrado_por)
        VALUES (%s, %s, %s, %s, %s)
    """, (fecha, tipo, descripcion, detalle, usuario))


@app.get("/api/inventario/analisis-ia")
def generar_analisis_ia(fecha: str):
    """Genera análisis ejecutivo IA del inventario y descarga PDF."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("analisis_ia",
        os.path.join(os.path.dirname(__file__), 'analisis_ia_inventario.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        output_path, _ = mod.generar_analisis(fecha)
    except Exception as e:
        raise HTTPException(500, f'Error generando análisis IA: {e}')
    return FileResponse(output_path, media_type='application/pdf',
                        filename=f'Analisis_IA_Inventario_{fecha}.pdf')


@app.get("/api/inventario/informe")
def generar_informe(fecha: str):
    """Genera y descarga el informe PDF del inventario."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("generar_informe",
        os.path.join(os.path.dirname(__file__), 'generar_informe.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    generar_pdf = mod.generar_pdf
    output_dir = os.path.join(BASE_DIR, 'inventario', 'informes')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'informe_inventario_{fecha}.pdf')
    try:
        generar_pdf(fecha, output_path)
    except Exception as e:
        raise HTTPException(500, f'Error generando informe: {e}')
    return FileResponse(output_path, media_type='application/pdf',
                        filename=f'Informe_Inventario_OS_{fecha}.pdf')


@app.get("/api/inventario/costos")
def listar_costos(fecha: str):
    """Datos de valorización para la pestaña Costos — usa costo_manual."""
    rows = db_query(DB_INV, """
        SELECT c.id_effi, c.nombre, c.categoria, c.bodega,
               COALESCE(r.grupo, '') AS grupo,
               COALESCE(r.unidad, '') AS unidad,
               COALESCE(c.inventario_teorico, 0) AS teorico,
               COALESCE(c.inventario_fisico, 0) AS fisico,
               COALESCE(c.diferencia, 0) AS diferencia,
               COALESCE(c.costo_manual, 0) AS costo_manual
        FROM inv_conteos c
        LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
        WHERE c.fecha_inventario = %s AND c.excluido = 0
        ORDER BY c.categoria, c.nombre
    """, (fecha,))

    result = []
    for r in rows:
        teorico = float(r['teorico'] or 0)
        fisico = float(r['fisico']) if r['fisico'] is not None else None
        dif = float(r['diferencia'] or 0)
        costo = float(r['costo_manual'] or 0)
        result.append({
            'id_effi': r['id_effi'],
            'nombre': r['nombre'],
            'categoria': r['categoria'] or '',
            'grupo': r['grupo'],
            'unidad': r['unidad'],
            'bodega': r['bodega'],
            'costo_manual': round(costo, 2),
            'teorico': round(teorico, 2),
            'fisico': round(fisico, 2) if fisico is not None else None,
            'diferencia': round(dif, 2),
            'valor_teorico': round(teorico * costo, 2),
            'valor_fisico': round(fisico * costo, 2) if fisico is not None else None,
            'impacto': round(dif * costo, 2),
        })

    return result


@app.get("/api/inventario/gestion")
def listar_gestion(fecha: str, severidad: Optional[str] = None, estado: Optional[str] = None,
                   grupo: Optional[str] = None, bodega: Optional[str] = None, solo_diferencias: bool = True):
    """Lista artículos de gestión con filtros. Por defecto solo los que tienen diferencia."""
    sql = "SELECT * FROM inv_gestion WHERE fecha_inventario = %s"
    params = [fecha]

    if solo_diferencias:
        sql += " AND total_diferencia != 0"
    if severidad:
        sql += " AND severidad = %s"
        params.append(severidad)
    if estado:
        sql += " AND estado = %s"
        params.append(estado)
    if grupo:
        sql += " AND grupo = %s"
        params.append(grupo)
    if bodega:
        sql += " AND bodegas LIKE %s"
        params.append(f'%{bodega}%')

    sql += " ORDER BY ABS(impacto_economico) DESC"
    rows = db_query(DB_INV, sql, params)

    for r in rows:
        for campo in ['total_teorico', 'total_fisico', 'total_diferencia', 'costo_manual', 'impacto_economico']:
            r[campo] = float(r[campo]) if r[campo] is not None else 0
        r['fecha_revision'] = str(r['fecha_revision']) if r['fecha_revision'] else None
        r['analizado_en'] = str(r['analizado_en']) if r['analizado_en'] else None
        r['bodegas'] = json.loads(r['bodegas']) if r['bodegas'] else []
    return rows


@app.get("/api/inventario/gestion/{gestion_id}/detalle")
def detalle_gestion(gestion_id: int):
    """Detalle de un artículo: conteos por bodega + datos de gestión."""
    rows = db_query(DB_INV, "SELECT * FROM inv_gestion WHERE id = %s", (gestion_id,))
    if not rows:
        raise HTTPException(404, "No encontrado")
    g = rows[0]

    # Conteos por bodega
    conteos = db_query(DB_INV, """
        SELECT bodega, inventario_teorico, inventario_fisico, diferencia, contado_por, fecha_conteo
        FROM inv_conteos
        WHERE fecha_inventario = %s AND id_effi = %s AND excluido = 0
        ORDER BY bodega
    """, (g['fecha_inventario'], g['id_effi']))

    for c in conteos:
        for campo in ['inventario_teorico', 'inventario_fisico', 'diferencia']:
            c[campo] = float(c[campo]) if c[campo] is not None else None
        c['fecha_conteo'] = str(c['fecha_conteo']) if c['fecha_conteo'] else None

    for campo in ['total_teorico', 'total_fisico', 'total_diferencia', 'costo_manual', 'impacto_economico']:
        g[campo] = float(g[campo]) if g[campo] is not None else 0
    g['fecha_revision'] = str(g['fecha_revision']) if g['fecha_revision'] else None
    g['analizado_en'] = str(g['analizado_en']) if g['analizado_en'] else None
    g['bodegas'] = json.loads(g['bodegas']) if g['bodegas'] else []

    return {"gestion": g, "conteos": conteos, "causas_disponibles": CAUSAS_PREDEFINIDAS}


class GestionUpdate(BaseModel):
    estado: str
    causa_final: Optional[str] = None
    observaciones: Optional[str] = None
    usuario: str


@app.put("/api/inventario/gestion/{gestion_id}")
def actualizar_gestion(gestion_id: int, data: GestionUpdate):
    """Actualiza estado, causa y observaciones de un artículo en gestión."""
    fecha_rows = db_query(DB_INV, "SELECT fecha_inventario FROM inv_gestion WHERE id = %s", (gestion_id,))
    if fecha_rows:
        verificar_bloqueo(fecha_rows[0]['fecha_inventario'], 'gestion')
    TRANSICIONES = {
        'pendiente': ['analizado', 'en_revision', 'justificada', 'requiere_ajuste'],
        'analizado': ['justificada', 'requiere_ajuste', 'en_revision'],
        'en_revision': ['justificada', 'requiere_ajuste', 'pendiente'],
        'justificada': ['en_revision', 'requiere_ajuste'],
        'requiere_ajuste': ['ajustada', 'en_revision', 'justificada'],
        'ajustada': ['en_revision'],
    }

    rows = db_query(DB_INV, "SELECT estado FROM inv_gestion WHERE id = %s", (gestion_id,))
    if not rows:
        raise HTTPException(404, "No encontrado")

    estado_actual = rows[0]['estado']
    if data.estado not in TRANSICIONES.get(estado_actual, []):
        raise HTTPException(400, f"Transición no permitida: {estado_actual} → {data.estado}")

    if data.estado == 'justificada' and not data.causa_final:
        raise HTTPException(400, "Se requiere causa para justificar")

    db_execute(DB_INV, """
        UPDATE inv_gestion
        SET estado = %s, causa_final = %s, observaciones = %s,
            revisado_por = %s, fecha_revision = NOW()
        WHERE id = %s
    """, (data.estado, data.causa_final, data.observaciones, data.usuario, gestion_id))

    registrar_auditoria(gestion_id, 'gestion_estado', data.usuario,
                        estado_actual, data.estado,
                        f'Causa: {data.causa_final or "—"} | {data.observaciones or ""}')
    return {"ok": True}


# ── Análisis de inconsistencias ──

import sys
sys.path.insert(0, os.path.dirname(__file__))
from analisis_inconsistencias import analizar_todos as _analizar_todos

analisis_status = {"estado": "idle", "progreso": 0, "total": 0, "articulo": "", "resultado": None}


def _analisis_background(fecha, usuario, usar_ia):
    """Tarea en background para analizar todos los artículos."""
    analisis_status["estado"] = "analizando"
    analisis_status["progreso"] = 0

    def callback(progreso, total, articulo):
        analisis_status["progreso"] = progreso
        analisis_status["total"] = total
        analisis_status["articulo"] = articulo[:40]

    try:
        resultado = _analizar_todos(fecha, usar_ia=usar_ia, callback=callback)
        analisis_status["estado"] = "ok"
        analisis_status["resultado"] = resultado
        registrar_auditoria(0, 'gestion_analisis', usuario, None, fecha,
                            f'{resultado["analizados"]} analizados, {resultado["con_causa"]} con causa')
    except Exception as e:
        analisis_status["estado"] = "error"
        analisis_status["resultado"] = {"error": str(e)}


@app.post("/api/inventario/gestion/analizar")
def analizar_inconsistencias(data: GestionCalcular, background_tasks: BackgroundTasks):
    """Lanza análisis de inconsistencias en background (determinista + IA)."""
    if analisis_status["estado"] == "analizando":
        raise HTTPException(409, "Ya hay un análisis en curso")

    usar_ia = True  # Por defecto usa IA para los que no resuelve la capa determinista
    analisis_status["estado"] = "iniciando"
    analisis_status["progreso"] = 0
    analisis_status["total"] = 0
    analisis_status["articulo"] = ""
    analisis_status["resultado"] = None

    background_tasks.add_task(_analisis_background, data.fecha_inventario, data.usuario, usar_ia)
    return {"ok": True, "mensaje": "Análisis iniciado en background"}


@app.get("/api/inventario/gestion/analisis-estado")
def estado_analisis():
    """Estado del análisis en curso."""
    return analisis_status


# ── Auditoría de OPs (inv_ops_revisar) ──

@app.get("/api/inventario/ops-revisar")
def listar_ops_revisar(fecha: str, filtro_inclusion: Optional[str] = None,
                       filtro_sospecha: Optional[str] = None,
                       filtro_revision: Optional[str] = None):
    """Lista OPs en auditoría con filtros opcionales.

    filtro_inclusion: 'incluidas' | 'excluidas' | None (todas)
    filtro_sospecha: 'sospechosas' | 'normales' | None
    filtro_revision: 'revisadas' | 'pendientes' | None
    """
    sql = "SELECT * FROM inv_ops_revisar WHERE fecha_corte = %s"
    params = [fecha]

    if filtro_inclusion == 'incluidas':
        sql += " AND incluida_en_calculo = 1"
    elif filtro_inclusion == 'excluidas':
        sql += " AND incluida_en_calculo = 0"

    if filtro_sospecha == 'sospechosas':
        sql += " AND sospechosa = 1"
    elif filtro_sospecha == 'normales':
        sql += " AND sospechosa = 0"

    if filtro_revision == 'revisadas':
        sql += " AND revisada = 1"
    elif filtro_revision == 'pendientes':
        sql += " AND revisada = 0"

    sql += " ORDER BY sospechosa DESC, ABS(minutos_del_corte) ASC"
    rows = db_query(DB_INV, sql, params)

    for r in rows:
        for campo in ['fecha_creacion', 'fecha_anulacion', 'fecha_cambio_procesada',
                       'calculado_en', 'fecha_revision']:
            r[campo] = str(r[campo]) if r[campo] else None

    # Resumen para el header
    resumen_rows = db_query(DB_INV, """
        SELECT
          COUNT(*) AS total,
          SUM(incluida_en_calculo) AS incluidas,
          SUM(CASE WHEN incluida_en_calculo = 0 THEN 1 ELSE 0 END) AS excluidas,
          SUM(sospechosa) AS sospechosas,
          SUM(revisada) AS revisadas
        FROM inv_ops_revisar
        WHERE fecha_corte = %s
    """, (fecha,))

    return {
        "ops": rows,
        "resumen": resumen_rows[0] if resumen_rows else {}
    }


@app.get("/api/inventario/ops-revisar/{op_id}/detalle")
def detalle_op_revisar(op_id: int):
    """Detalle completo de una OP: cambios de estado + materiales + productos + trazabilidad."""
    rows = db_query(DB_INV, "SELECT * FROM inv_ops_revisar WHERE id = %s", (op_id,))
    if not rows:
        raise HTTPException(404, "OP no encontrada")
    op = rows[0]
    id_orden = op['id_orden']

    # Cambios de estado
    cambios = db_query(DB_EFFI, """
        SELECT nuevo_estado, f_cambio_de_estado, responsable_cambio_de_estado
        FROM zeffi_cambios_estado
        WHERE id_orden = %s
        ORDER BY f_cambio_de_estado
    """, (id_orden,))

    # Materiales
    materiales = db_query(DB_EFFI, """
        SELECT cod_material, descripcion_material, cantidad, vigencia
        FROM zeffi_materiales
        WHERE id_orden = %s
    """, (id_orden,))

    # Productos
    productos = db_query(DB_EFFI, """
        SELECT cod_articulo, descripcion_articulo_producido, cantidad, vigencia
        FROM zeffi_articulos_producidos
        WHERE id_orden = %s
    """, (id_orden,))

    # Trazabilidad relacionada con esta OP
    trazabilidad = db_query(DB_EFFI, """
        SELECT articulo, cantidad, fecha, tipo_de_movimiento
        FROM zeffi_trazabilidad
        WHERE transaccion LIKE %s OR transaccion LIKE %s
        ORDER BY fecha DESC
        LIMIT 50
    """, (f"%: {id_orden}", f"%: {id_orden} %"))

    # Convertir fechas a string
    for r in cambios:
        r['f_cambio_de_estado'] = str(r['f_cambio_de_estado']) if r['f_cambio_de_estado'] else None
    for r in trazabilidad:
        r['fecha'] = str(r['fecha']) if r['fecha'] else None
    for campo in ['fecha_creacion', 'fecha_anulacion', 'fecha_cambio_procesada',
                   'calculado_en', 'fecha_revision']:
        op[campo] = str(op[campo]) if op[campo] else None

    return {
        "op": op,
        "cambios_estado": cambios,
        "materiales": materiales,
        "productos": productos,
        "trazabilidad": trazabilidad
    }


class OpRevisarUpdate(BaseModel):
    revisada: bool
    nota: Optional[str] = None
    usuario: str


@app.put("/api/inventario/ops-revisar/{op_id}")
def actualizar_op_revisar(op_id: int, data: OpRevisarUpdate):
    """Marca una OP como revisada (o desmarca) con nota."""
    rows = db_query(DB_INV, "SELECT id_orden, fecha_corte FROM inv_ops_revisar WHERE id = %s", (op_id,))
    if not rows:
        raise HTTPException(404, "OP no encontrada")

    if data.revisada:
        db_execute(DB_INV, """
            UPDATE inv_ops_revisar
            SET revisada = 1, nota_revision = %s,
                revisada_por = %s, fecha_revision = NOW()
            WHERE id = %s
        """, (data.nota, data.usuario, op_id))
        accion = 'op_revisada'
    else:
        db_execute(DB_INV, """
            UPDATE inv_ops_revisar
            SET revisada = 0, nota_revision = NULL,
                revisada_por = NULL, fecha_revision = NULL
            WHERE id = %s
        """, (op_id,))
        accion = 'op_desmarcada'

    registrar_auditoria(0, accion, data.usuario,
                        f"OP {rows[0]['id_orden']}", str(data.revisada),
                        data.nota or '')
    return {"ok": True}


# ── Sync Effi ──

EXPORT_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'export_inventario.js')
IMPORT_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'import_all.js')
SYNC_CATALOGO_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'sync_inventario_catalogo.py')
sync_effi_status = {"estado": "idle", "mensaje": "", "timestamp": None}


def _sync_effi_task():
    """Tarea en background: export Playwright + import + sync catálogo."""
    sync_effi_status["estado"] = "exportando"
    sync_effi_status["mensaje"] = "Descargando inventario de Effi..."
    sync_effi_status["timestamp"] = datetime.now().isoformat()

    try:
        # 1. Export: descargar Excel de Effi
        result = subprocess.run(
            ['node', EXPORT_SCRIPT],
            capture_output=True, text=True, timeout=300,
            cwd=BASE_DIR
        )
        if result.returncode != 0:
            sync_effi_status["estado"] = "error"
            sync_effi_status["mensaje"] = f"Export falló: {result.stderr[-200:]}"
            return

        # 2. Import: Excel → effi_data.zeffi_inventario
        sync_effi_status["estado"] = "importando"
        sync_effi_status["mensaje"] = "Importando a base de datos..."

        result = subprocess.run(
            ['node', IMPORT_SCRIPT],
            capture_output=True, text=True, timeout=300,
            cwd=BASE_DIR
        )
        if result.returncode != 0:
            sync_effi_status["estado"] = "error"
            sync_effi_status["mensaje"] = f"Import falló: {result.stderr[-200:]}"
            return

        # 3. Sync catálogo: generar inv_catalogo_articulos con unidad y grupo
        sync_effi_status["mensaje"] = "Generando catálogo con unidades y grupos..."

        result = subprocess.run(
            ['python3', SYNC_CATALOGO_SCRIPT],
            capture_output=True, text=True, timeout=120,
            cwd=BASE_DIR
        )
        if result.returncode != 0:
            sync_effi_status["estado"] = "error"
            sync_effi_status["mensaje"] = f"Catálogo falló: {result.stderr[-200:]}"
            return

        # Extraer cantidad del output
        linea = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ''
        sync_effi_status["estado"] = "ok"
        sync_effi_status["mensaje"] = linea or "Catálogo actualizado"
        sync_effi_status["timestamp"] = datetime.now().isoformat()

    except subprocess.TimeoutExpired:
        sync_effi_status["estado"] = "error"
        sync_effi_status["mensaje"] = "Proceso tardó más de 5 minutos — timeout"
    except Exception as e:
        sync_effi_status["estado"] = "error"
        sync_effi_status["mensaje"] = str(e)[:300]


@app.post("/api/inventario/sync-effi")
def sync_effi(background_tasks: BackgroundTasks):
    """Lanza export + import de artículos Effi en background."""
    if sync_effi_status["estado"] in ("exportando", "importando"):
        raise HTTPException(409, "Ya hay una sincronización en curso")
    sync_effi_status["estado"] = "iniciando"
    sync_effi_status["mensaje"] = "Iniciando sincronización..."
    sync_effi_status["timestamp"] = datetime.now().isoformat()
    background_tasks.add_task(_sync_effi_task)
    return {"ok": True, "mensaje": "Sincronización iniciada"}


@app.get("/api/inventario/sync-effi/estado")
def sync_effi_estado():
    """Estado actual de la sincronización."""
    return sync_effi_status


# Servir frontend estático (después de todas las rutas /api/)
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """SPA fallback — sirve archivo estático si existe, si no index.html."""
        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9401)
