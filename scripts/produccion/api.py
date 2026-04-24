"""API FastAPI — Programación de Producción + Inventario unificado. Puerto 9600."""
import os, sys, jwt
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timedelta
import pymysql
import urllib.request, urllib.parse, json as _json

# Cargar .env del mismo directorio si existe (secrets: GOOGLE_CLIENT_ID, JWT_SECRET)
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_ENV_FILE):
    for line in open(_ENV_FILE):
        line = line.strip()
        if not line or line.startswith('#'): continue
        if '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_integracion, cfg_inventario

app = FastAPI(title="Producción OS", version="1.0")

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
STATIC_DIR = os.path.join(BASE_DIR, 'produccion', 'dist')

# Conexión a BD remota inventario_produccion_effi (VPS, vía tunnel SSH automático)
# cfg_inventario() abre el tunnel 1 vez por proceso y devuelve dict listo para pymysql.connect
DB_INVPROD = cfg_inventario(dict_cursor=True)
DB_PROD = DB_INVPROD  # tablas prod_*
DB_INV  = DB_INVPROD  # tablas inv_*
# DB_EFFI apunta a os_integracion en VPS Contabo (fuente de verdad).
# effi_data local es SOLO intermediaria del pipeline — ver MANIFESTO §8.
DB_EFFI = cfg_integracion(dict_cursor=True)

JWT_SECRET = os.environ.get('JWT_SECRET', 'os_secret_dev_change_me')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── AUTH: Google OAuth + JWT ───────────────────────────────────────

def _validar_token_google(id_token: str) -> dict:
    """Valida el id_token con Google y devuelve el payload."""
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = _json.loads(resp.read())
    except Exception as e:
        raise HTTPException(401, f"Token de Google inválido: {e}")
    if data.get('error'):
        raise HTTPException(401, "Token de Google inválido o expirado")
    if GOOGLE_CLIENT_ID and data.get('aud') != GOOGLE_CLIENT_ID:
        raise HTTPException(401, "Token no corresponde a esta aplicación")
    if not data.get('email'):
        raise HTTPException(401, "No se obtuvo email de Google")
    return data


def _buscar_usuario_os(email: str) -> Optional[dict]:
    """Busca el usuario en sys_usuarios (Hostinger os_comunidad) vía helper remoto."""
    from lib import comunidad
    with comunidad(dict_cursor=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Email AS email, Nombre_Usuario AS nombre, Nivel_Acceso AS nivel, "
                "estado, foto_url FROM sys_usuarios WHERE Email = %s",
                (email,)
            )
            return cur.fetchone()


class GoogleAuthRequest(BaseModel):
    id_token: str


@app.post("/api/auth/google")
def api_auth_google(req: GoogleAuthRequest):
    """Login con Google: valida id_token, busca usuario en sys_usuarios, devuelve JWT."""
    payload = _validar_token_google(req.id_token)
    email = payload['email']
    usuario = _buscar_usuario_os(email)
    if not usuario:
        raise HTTPException(403, "No tienes acceso. Contacta al administrador.")
    if usuario.get('estado') != 'Activo':
        raise HTTPException(403, "Usuario inactivo. Contacta al administrador.")

    token = jwt.encode({
        'email': usuario['email'],
        'nombre': usuario['nombre'],
        'nivel': usuario['nivel'],
        'foto': payload.get('picture') or usuario.get('foto_url') or '',
        'exp': datetime.utcnow() + timedelta(days=7),
    }, JWT_SECRET, algorithm='HS256')

    return {
        'ok': True,
        'token': token,
        'usuario': {
            'email': usuario['email'],
            'nombre': usuario['nombre'],
            'nivel': usuario['nivel'],
            'foto': payload.get('picture') or usuario.get('foto_url') or '',
        }
    }


def require_auth(request: Request):
    """Dependency de FastAPI — valida JWT en header Authorization: Bearer."""
    header = request.headers.get('authorization', '')
    token = header[7:] if header.startswith('Bearer ') else None
    if not token:
        raise HTTPException(401, "No autenticado")
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except Exception:
        raise HTTPException(401, "Token inválido")
    return decoded


@app.get("/api/auth/me")
def api_auth_me(usuario=Depends(require_auth)):
    """Devuelve datos del usuario autenticado (verifica que el JWT sigue válido)."""
    return {'ok': True, 'usuario': usuario}


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


# ── Sugerencia de receta ───────────────────────────────────

import importlib.util as _ilu
def _cargar_modulo(nombre, archivo):
    spec = _ilu.spec_from_file_location(nombre,
        os.path.join(os.path.dirname(__file__), archivo))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@app.get("/api/produccion/sugerir-receta")
def api_sugerir_receta(cod: str, cantidad: float, n_ops: int = 10,
                        iterativo: bool = True, fallback_agente: bool = True):
    """Sugiere receta para producir 'cantidad' unidades del artículo 'cod'.
    Si iterativo=True (default), intenta con 5/10/15/20 OPs con thresholds 3/5/7/9.
    Si las 4 ventanas fallan y fallback_agente=True, invoca al agente IA (Claude Code).
    """
    mod = _cargar_modulo("sugerir_receta", "sugerir_receta.py")
    if iterativo:
        return mod.sugerir_iterativo(cod, cantidad, fallback_agente=fallback_agente)
    return mod.sugerir_receta(cod, cantidad, n_ops)


# ── Compatibilidad y grupos de OP ─────────────────────────

class CompatRequest(BaseModel):
    cods: list[str]


@app.post("/api/produccion/compatibilidad")
def api_compatibilidad(req: CompatRequest):
    """Evalúa si una lista de productos puede programarse en una sola OP.
    Devuelve {compatible, mp_granel_comun, productos[], razon}."""
    mod = _cargar_modulo("grupo_helper", "grupo_helper.py")
    return mod.evaluar_compatibilidad(req.cods)


class GrupoCreate(BaseModel):
    solicitudes_ids: list[int]
    creado_por: str
    observaciones: Optional[str] = None
    fecha_programada: Optional[str] = None


@app.post("/api/produccion/grupos")
def api_crear_grupo(data: GrupoCreate):
    """Crea un grupo de OP con varias solicitudes.
    Valida compatibilidad antes de crear. Devuelve el grupo creado."""
    if not data.solicitudes_ids:
        raise HTTPException(400, "Debe incluir al menos 1 solicitud")

    # 1) Cargar solicitudes y verificar que existen + están en estado 'solicitado'
    placeholders = ','.join(['%s'] * len(data.solicitudes_ids))
    sols = q(DB_PROD, f"""
        SELECT id, cod_articulo, nombre_articulo, cantidad, estado, op_grupo_id
        FROM prod_solicitudes WHERE id IN ({placeholders})
    """, tuple(data.solicitudes_ids))

    if len(sols) != len(data.solicitudes_ids):
        raise HTTPException(404, f"Algunas solicitudes no existen")

    for s in sols:
        if s['estado'] != 'solicitado':
            raise HTTPException(400, f"Solicitud {s['id']} está en estado '{s['estado']}', no se puede agrupar")
        if s['op_grupo_id']:
            raise HTTPException(400, f"Solicitud {s['id']} ya pertenece al grupo {s['op_grupo_id']}")

    # 2) Validar compatibilidad
    cods = [s['cod_articulo'] for s in sols]
    mod = _cargar_modulo("grupo_helper", "grupo_helper.py")
    compat = mod.evaluar_compatibilidad(cods)
    if not compat['compatible']:
        raise HTTPException(400, f"Productos no compatibles: {compat['razon']}")

    # 3) Crear grupo
    grupo_id = exe(DB_PROD, """
        INSERT INTO prod_grupos (creado_por, observaciones, fecha_programada, mp_granel_principal)
        VALUES (%s, %s, %s, %s)
    """, (data.creado_por, data.observaciones, data.fecha_programada, compat['mp_granel_comun']))

    # 4) Asociar solicitudes al grupo
    exe(DB_PROD, f"""
        UPDATE prod_solicitudes SET op_grupo_id = %s
        WHERE id IN ({placeholders})
    """, tuple([grupo_id] + data.solicitudes_ids))

    # 5) Devolver el grupo con sus solicitudes
    return api_obtener_grupo(grupo_id)


@app.get("/api/produccion/grupos/{id}")
def api_obtener_grupo(id: int):
    rows = q(DB_PROD, "SELECT * FROM prod_grupos WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(404, "Grupo no encontrado")
    g = rows[0]
    g['fecha_creacion'] = str(g['fecha_creacion']) if g.get('fecha_creacion') else None
    g['fecha_programada'] = str(g['fecha_programada']) if g.get('fecha_programada') else None
    g['solicitudes'] = q(DB_PROD, """
        SELECT id, cod_articulo, nombre_articulo, cantidad, estado
        FROM prod_solicitudes WHERE op_grupo_id = %s
    """, (id,))
    for s in g['solicitudes']:
        s['cantidad'] = float(s['cantidad']) if s['cantidad'] else 0
    return g


@app.get("/api/produccion/grupos")
def api_listar_grupos(estado: Optional[str] = None):
    sql = "SELECT * FROM prod_grupos WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado = %s"
        params.append(estado)
    sql += " ORDER BY fecha_creacion DESC LIMIT 200"
    rows = q(DB_PROD, sql, params)
    for r in rows:
        r['fecha_creacion'] = str(r['fecha_creacion']) if r.get('fecha_creacion') else None
        r['fecha_programada'] = str(r['fecha_programada']) if r.get('fecha_programada') else None
    return rows


@app.delete("/api/produccion/grupos/{id}")
def api_eliminar_grupo(id: int):
    """Elimina un grupo y libera las solicitudes asociadas (vuelven a estado 'solicitado'
    sin op_grupo_id). Solo si el grupo está en 'borrador'."""
    rows = q(DB_PROD, "SELECT estado FROM prod_grupos WHERE id = %s", (id,))
    if not rows:
        raise HTTPException(404, "Grupo no encontrado")
    if rows[0]['estado'] != 'borrador':
        raise HTTPException(400, f"Solo se pueden eliminar grupos en borrador (este: {rows[0]['estado']})")
    exe(DB_PROD, "UPDATE prod_solicitudes SET op_grupo_id = NULL WHERE op_grupo_id = %s", (id,))
    exe(DB_PROD, "DELETE FROM prod_grupos WHERE id = %s", (id,))
    return {"ok": True}


@app.post("/api/produccion/grupos/{id}/sugerir-receta")
def api_sugerir_receta_grupo(id: int):
    """Sugiere receta combinada para un grupo: suma materiales granel + envases/etiquetas
    específicos por formato. Internamente llama sugerir_iterativo para cada solicitud."""
    grupo = api_obtener_grupo(id)
    sols = grupo.get('solicitudes', [])
    if not sols:
        raise HTTPException(400, "El grupo no tiene solicitudes")

    mod = _cargar_modulo("sugerir_receta", "sugerir_receta.py")

    # Obtener receta individual de cada solicitud
    recetas_ind = []
    for s in sols:
        r = mod.sugerir_iterativo(s['cod_articulo'], float(s['cantidad']))
        recetas_ind.append({
            'solicitud_id': s['id'],
            'cod_articulo': s['cod_articulo'],
            'cantidad': float(s['cantidad']),
            'receta': r,
        })

    # Combinar materiales: sumar por cod_material
    materiales_combinados = {}
    costos_combinados = {}
    for ri in recetas_ind:
        for mat in ri['receta'].get('materiales', []):
            cod = mat['cod']
            if cod not in materiales_combinados:
                materiales_combinados[cod] = {'cod': cod, 'desc': mat.get('desc', mat.get('nombre', '')),
                                                'cantidad': 0, 'fuentes': []}
            materiales_combinados[cod]['cantidad'] += float(mat.get('cantidad', 0))
            materiales_combinados[cod]['fuentes'].append({
                'solicitud_id': ri['solicitud_id'],
                'cod_articulo': ri['cod_articulo'],
                'aporta': float(mat.get('cantidad', 0)),
            })
        for c in ri['receta'].get('costos', []):
            key = c.get('cp', c.get('nombre', ''))
            if key not in costos_combinados:
                costos_combinados[key] = {'cp': key, 'cantidad': 0, 'costo_ud': c.get('costo_ud', 0)}
            costos_combinados[key]['cantidad'] += float(c.get('cantidad', 0))

    return {
        'grupo_id': id,
        'mp_granel_principal': grupo.get('mp_granel_principal'),
        'solicitudes': sols,
        'recetas_individuales': recetas_ind,
        'materiales_combinados': sorted(materiales_combinados.values(), key=lambda x: -x['cantidad']),
        'costos_combinados': list(costos_combinados.values()),
    }


# ── Logs de producción (lectura) ───────────────────────────

@app.get("/api/produccion/logs")
def api_logs(limit: int = 100, evento: Optional[str] = None, cod: Optional[str] = None):
    sql = "SELECT * FROM prod_logs WHERE 1=1"
    params = []
    if evento:
        sql += " AND evento = %s"
        params.append(evento)
    if cod:
        sql += " AND cod_articulo = %s"
        params.append(cod)
    sql += " ORDER BY id DESC LIMIT %s"
    params.append(limit)
    rows = q(DB_PROD, sql, params)
    for r in rows:
        r['ts'] = str(r['ts']) if r.get('ts') else None
        if r.get('cantidad'): r['cantidad'] = float(r['cantidad'])
    return rows


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


# ── Artículos (os_integracion VPS + inv_rangos en inventario_produccion_effi VPS) ──

@app.get("/api/articulos")
def listar_articulos(tipo: Optional[str] = None, q_str: Optional[str] = None):
    """Lista artículos de Effi vigentes con tipo (MP/PP/PT/INS/etc) desde inv_rangos.
    os_integracion e inv_rangos están ambas en VPS (BDs distintas), se hace merge en Python.
    tipo: filtro opcional (PT, PP, MP). Si se omite, devuelve todos.
    q: filtro de búsqueda por nombre o código.
    """
    # 1) Traer el mapa cod → {grupo, unidad} desde inv_rangos remoto (VPS)
    rangos_rows = q(DB_INV, "SELECT id_effi AS cod, grupo, unidad FROM inv_rangos")
    rangos_map = {r['cod']: r for r in rangos_rows}

    # 2) Traer artículos de os_integracion VPS
    sql = """
        SELECT e.id AS cod, e.nombre,
               CAST(REPLACE(e.stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,2)) AS stock
        FROM zeffi_inventario e
        WHERE e.vigencia = 'Vigente'
    """
    params = []
    if q_str:
        sql += " AND (e.nombre LIKE %s OR e.id LIKE %s)"
        params += [f'%{q_str}%', f'%{q_str}%']
    sql += " ORDER BY e.nombre LIMIT 500"

    rows = q(DB_EFFI, sql, params)

    # 3) Merge en Python
    out = []
    for r in rows:
        info = rangos_map.get(r['cod'], {})
        tipo_art = info.get('grupo') or ''
        if tipo and tipo_art != tipo:
            continue
        out.append({
            'cod': r['cod'], 'nombre': r['nombre'],
            'tipo': tipo_art, 'unidad': info.get('unidad') or '',
            'stock': float(r['stock']) if r['stock'] is not None else 0,
        })
    return out


# ── Solicitudes CRUD ──────────────────────────────────────

@app.get("/api/solicitudes")
def listar_solicitudes(estado: Optional[str] = None, _start: int = 0, _end: int = 100,
                        _sort: Optional[str] = None, _order: Optional[str] = None):
    sql = "SELECT * FROM prod_solicitudes WHERE 1=1"
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
    total_row = q(DB_PROD, "SELECT COUNT(*) AS n FROM prod_solicitudes" + (" WHERE estado = %s" if estado else ""),
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
    rows = q(DB_PROD, "SELECT * FROM prod_solicitudes WHERE id = %s", (id,))
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
        INSERT INTO prod_solicitudes
            (cod_articulo, nombre_articulo, tipo_articulo, cantidad, observaciones, fecha_necesidad, fecha_programada, solicitado_por, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'solicitado')
    """, (data.cod_articulo, data.nombre_articulo, data.tipo_articulo, data.cantidad,
          data.observaciones, data.fecha_necesidad, data.fecha_programada, data.solicitado_por))
    return obtener_solicitud(new_id)


@app.patch("/api/solicitudes/{id}")
def actualizar_solicitud(id: int, data: SolicitudUpdate):
    # Validar que existe
    existing = q(DB_PROD, "SELECT estado FROM prod_solicitudes WHERE id = %s", (id,))
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
    exe(DB_PROD, f"UPDATE prod_solicitudes SET {', '.join(campos)} WHERE id = %s", valores)
    return obtener_solicitud(id)


@app.delete("/api/solicitudes/{id}")
def eliminar_solicitud(id: int):
    exe(DB_PROD, "DELETE FROM prod_solicitudes WHERE id = %s", (id,))
    return {"ok": True}


# ── Métricas ──────────────────────────────────────────────

@app.get("/api/solicitudes/stats/resumen")
def stats_resumen():
    rows = q(DB_PROD, """
        SELECT estado, COUNT(*) AS n FROM prod_solicitudes GROUP BY estado
    """)
    return {r['estado']: r['n'] for r in rows}


# ── Libro de recetas ───────────────────────────────────────

@app.get("/api/recetas")
def listar_recetas(familia: Optional[str] = None, estado: Optional[str] = None,
                   confianza: Optional[str] = None, q_str: Optional[str] = None):
    """Lista las recetas del libro maestro con filtros opcionales."""
    sql = """
        SELECT r.id, r.cod_articulo, r.nombre, r.familia, r.patron,
               r.cantidad_lote_std, r.unidad_producto, r.confianza, r.estado,
               r.n_ops_analizadas, r.updated_at,
               (SELECT COUNT(*) FROM prod_recetas_materiales WHERE receta_id=r.id) AS n_materiales,
               (SELECT COUNT(*) FROM prod_recetas_costos WHERE receta_id=r.id) AS n_costos
        FROM prod_recetas r
        WHERE 1=1
    """
    params = []
    if familia:
        sql += " AND r.familia = %s"
        params.append(familia)
    if estado:
        sql += " AND r.estado = %s"
        params.append(estado)
    if confianza:
        sql += " AND r.confianza = %s"
        params.append(confianza)
    if q_str:
        sql += " AND (r.cod_articulo LIKE %s OR r.nombre LIKE %s)"
        params.extend([f"%{q_str}%", f"%{q_str}%"])
    sql += " ORDER BY r.familia, r.cod_articulo"
    return q(DB_PROD, sql, params)


@app.get("/api/recetas/{cod}")
def obtener_receta(cod: str):
    """Devuelve la receta completa con materiales, productos y costos."""
    rec = q(DB_PROD, "SELECT * FROM prod_recetas WHERE cod_articulo=%s", (cod,))
    if not rec:
        raise HTTPException(404, f"Receta no encontrada para cod={cod}")
    r = rec[0]
    rid = r['id']
    r['materiales'] = q(DB_PROD,
        "SELECT * FROM prod_recetas_materiales WHERE receta_id=%s ORDER BY cantidad_por_lote DESC", (rid,))
    r['productos'] = q(DB_PROD,
        "SELECT * FROM prod_recetas_productos WHERE receta_id=%s ORDER BY es_principal DESC", (rid,))
    r['costos'] = q(DB_PROD,
        "SELECT * FROM prod_recetas_costos WHERE receta_id=%s", (rid,))
    return r


@app.get("/api/recetas/stats/resumen")
def recetas_stats():
    """Resumen por familia: total / con receta / validadas."""
    rows = q(DB_PROD, """
        SELECT familia,
               COUNT(*) AS total,
               SUM(CASE WHEN estado='validada' THEN 1 ELSE 0 END) AS validadas,
               SUM(CASE WHEN confianza='alta' THEN 1 ELSE 0 END) AS conf_alta
        FROM prod_recetas
        GROUP BY familia
        ORDER BY total DESC
    """)
    return rows


class RecetaPatch(BaseModel):
    estado: Optional[str] = None
    confianza: Optional[str] = None
    notas_analisis: Optional[str] = None


@app.patch("/api/recetas/{cod}")
def actualizar_receta(cod: str, data: RecetaPatch, usuario=Depends(require_auth)):
    """Permite actualizar estado/confianza/notas desde la UI."""
    sets = []
    params = []
    if data.estado:
        sets.append("estado=%s")
        params.append(data.estado)
        if data.estado == 'validada':
            sets.append("validated_at=NOW()")
    if data.confianza:
        sets.append("confianza=%s")
        params.append(data.confianza)
    if data.notas_analisis is not None:
        sets.append("notas_analisis=%s")
        params.append(data.notas_analisis)
    if not sets:
        raise HTTPException(400, "Sin campos para actualizar")
    params.append(cod)
    exe(DB_PROD, f"UPDATE prod_recetas SET {', '.join(sets)} WHERE cod_articulo=%s", params)
    return {"ok": True}


# ── Proxy al API de inventario (puerto 9401) ──────────────
# Temporal: mientras la UI está aquí pero los endpoints viven en el servicio os-inventario-api.
# Cuando fusionemos backends (Fase 10), este proxy se elimina.

import httpx

INVENTARIO_API_BASE = os.environ.get('INVENTARIO_API_BASE', 'http://localhost:9401')
_http_client = httpx.Client(timeout=60.0)

@app.api_route("/api/inventario/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_inventario(path: str, request: Request):
    """Proxy transparente hacia el servicio os-inventario-api."""
    url = f"{INVENTARIO_API_BASE}/api/inventario/{path}"
    # Copiar query string
    if request.url.query:
        url += "?" + request.url.query
    # Copiar headers excepto host
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ('host', 'content-length')}
    body = await request.body()
    try:
        resp = _http_client.request(request.method, url, headers=headers, content=body)
        from fastapi.responses import Response as FResp
        return FResp(
            content=resp.content,
            status_code=resp.status_code,
            headers={k: v for k, v in resp.headers.items() if k.lower() not in ('content-encoding', 'transfer-encoding')},
            media_type=resp.headers.get('content-type')
        )
    except Exception as e:
        raise HTTPException(502, f"Error proxy a inventario: {e}")


# ── Servir frontend ───────────────────────────────────────

@app.get("/")
@app.get("/{path:path}")
def serve_frontend(path: str = ""):
    if not os.path.exists(STATIC_DIR):
        return {"ok": True, "msg": "API corriendo. Frontend no compilado aún."}
    # Intentar archivo estático primero (assets con hash → cache larga)
    if path and os.path.exists(os.path.join(STATIC_DIR, path)):
        is_hashed_asset = path.startswith('assets/') and any(c in path for c in '-')
        headers = {'Cache-Control': 'public, max-age=31536000, immutable'} if is_hashed_asset else {}
        return FileResponse(os.path.join(STATIC_DIR, path), headers=headers)
    # Fallback a index.html (SPA) — NO cache para que cada deploy invalide
    return FileResponse(
        os.path.join(STATIC_DIR, 'index.html'),
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0'}
    )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9600)
