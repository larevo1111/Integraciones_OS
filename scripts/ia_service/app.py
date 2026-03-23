"""
Flask API — Servicio Central de IA
Puerto: 5100
Endpoints:
  POST /ia/consultar           — consulta principal
  GET  /ia/agentes             — lista agentes disponibles
  GET  /ia/tipos               — lista tipos de consulta
  GET  /ia/health              — health check
  GET  /ia/consumo             — consumo real por agente (hoy/ayer/semana/mes)
  GET  /ia/consumo/historico   — consumo día a día últimos N días
"""
import sys
import os

# Permitir importar ia_service desde scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from ia_service import consultar
from ia_service.config import get_local_conn

app = Flask(__name__)


@app.route('/ia/health', methods=['GET'])
def health():
    # Limpieza periódica de rate limit windows inactivos
    from ia_service.seguridad import limpiar_rate_windows
    limpiar_rate_windows()
    return jsonify({'ok': True, 'servicio': 'ia_service_os', 'version': '1.0'})


@app.route('/ia/consultar', methods=['POST'])
def endpoint_consultar():
    """
    Body JSON:
    {
        "pregunta":        "¿Cuánto vendimos ayer?",   -- REQUERIDO
        "usuario_id":      "santi",                     -- opcional (default: "anonimo")
        "canal":           "telegram",                  -- opcional (default: "api")
        "empresa":         "ori_sil_2",                 -- opcional (default: "ori_sil_2")
        "tema":            "comercial",                 -- opcional (el enrutador lo detecta si no viene)
        "tipo":            "analisis_datos",            -- opcional (el enrutador lo detecta si no viene)
        "agente":          "gemini-flash",              -- opcional
        "conversacion_id": 42,                          -- opcional
        "nombre_usuario":  "Santiago",                  -- opcional
        "contexto_extra":  "Vista: Resumen Ventas..."   -- opcional (contexto de pantalla del ERP)
        "cliente": {                                    -- opcional (para atención al cliente)
            "nombre":         "Juan Pérez",             -- nombre del cliente
            "identificacion": "12345678",               -- cédula o NIT
            "tipo_id":        "CC",                     -- CC, NIT, CE... (default: "ID")
            "telefono":       "3001234567",             -- opcional
            "email":          "juan@email.com"          -- opcional
        }
    }
    """
    data = request.get_json(silent=True) or {}

    pregunta = data.get('pregunta', '').strip()
    imagen_b64 = data.get('imagen_base64')
    # Con imagen, pregunta puede venir vacía (el usuario solo mandó foto)
    if not pregunta and not imagen_b64:
        return jsonify({'ok': False, 'error': 'El campo "pregunta" o "imagen_base64" es requerido.'}), 400

    resultado = consultar(
        pregunta        = pregunta,
        tipo            = data.get('tipo'),
        agente          = data.get('agente'),
        usuario_id      = data.get('usuario_id', 'anonimo'),
        canal           = data.get('canal', 'api'),
        empresa         = data.get('empresa', 'ori_sil_2'),
        tema            = data.get('tema'),
        conversacion_id = data.get('conversacion_id'),
        nombre_usuario  = data.get('nombre_usuario'),
        contexto_extra  = data.get('contexto_extra', ''),
        cliente         = data.get('cliente'),
        imagen_b64      = imagen_b64,
        imagen_mime     = data.get('imagen_mime', 'image/jpeg'),
    )
    # Si fue bloqueado por rate limit, devolver 429 con Retry-After header
    if not resultado.get('ok') and resultado.get('retry_after'):
        resp = jsonify(resultado)
        resp.status_code = 429
        resp.headers['Retry-After'] = str(resultado['retry_after'])
        return resp
    return jsonify(resultado)


@app.route('/ia/agentes', methods=['GET'])
def endpoint_agentes():
    """Lista todos los agentes activos (sin exponer la api_key)."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, nombre, proveedor, tipo, capacidades, "
                "max_tokens_entrada, rate_limit_rpm, rate_limit_rpd, activo, orden, notas "
                "FROM ia_agentes ORDER BY orden"
            )
            agentes = cur.fetchall()
        return jsonify({'ok': True, 'agentes': agentes})
    finally:
        conn.close()


@app.route('/ia/tipos', methods=['GET'])
def endpoint_tipos():
    """Lista todos los tipos de consulta activos."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, nombre, descripcion, formato_salida, "
                "requiere_estructura, requiere_ejecucion, agente_preferido, temperatura "
                "FROM ia_tipos_consulta WHERE activo = 1 ORDER BY id"
            )
            tipos = cur.fetchall()
        return jsonify({'ok': True, 'tipos': tipos})
    finally:
        conn.close()


@app.route('/ia/consumo', methods=['GET'])
def endpoint_consumo():
    """
    Consumo real por agente con % del límite diario usado.
    Query params:
      ?periodo=hoy|ayer|semana|mes|todo  (default: hoy)
      ?agente=gemini-pro                 (opcional, filtra por agente)
      ?empresa=ori_sil_2                 (opcional, filtra por empresa)
    """
    periodo = request.args.get('periodo', 'hoy')
    agente_filtro = request.args.get('agente')
    empresa_filtro = request.args.get('empresa')

    filtros_fecha = {
        'hoy':    "c.fecha = CURDATE()",
        'ayer':   "c.fecha = CURDATE() - INTERVAL 1 DAY",
        'semana': "c.fecha >= CURDATE() - INTERVAL 6 DAY",
        'mes':    "c.fecha >= DATE_FORMAT(CURDATE(), '%Y-%m-01')",
        'todo':   "1=1",
    }
    cond_fecha = filtros_fecha.get(periodo, "c.fecha = CURDATE()")

    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            params = []
            cond_agente = ""
            cond_empresa = ""
            if agente_filtro:
                cond_agente = " AND c.agente_slug = %s"
                params.append(agente_filtro)
            if empresa_filtro:
                cond_empresa = " AND c.empresa = %s"
                params.append(empresa_filtro)

            cur.execute(f"""
                SELECT
                    c.agente_slug,
                    a.nombre              AS agente_nombre,
                    a.modelo_id,
                    a.tipo,
                    SUM(c.llamadas)       AS llamadas,
                    SUM(c.errores)        AS errores,
                    ROUND(SUM(c.errores) * 100.0 / GREATEST(SUM(c.llamadas), 1), 1) AS pct_error,
                    SUM(c.tokens_in)      AS tokens_in,
                    SUM(c.tokens_out)     AS tokens_out,
                    SUM(c.tokens_total)   AS tokens_total,
                    ROUND(SUM(c.costo_usd), 6)   AS costo_usd,
                    ROUND(AVG(c.latencia_prom_ms)) AS latencia_prom_ms,
                    a.rate_limit_rpd      AS limite_rpd_diario,
                    CASE
                        WHEN a.rate_limit_rpd IS NULL OR a.rate_limit_rpd = 0 THEN NULL
                        WHEN a.rate_limit_rpd >= 999999 THEN 0.0
                        ELSE ROUND(SUM(c.llamadas) * 100.0 / a.rate_limit_rpd, 1)
                    END AS pct_limite_hoy,
                    CASE
                        WHEN a.rate_limit_rpd IS NULL OR a.rate_limit_rpd = 0 THEN 'sin_limite'
                        WHEN a.rate_limit_rpd >= 999999 THEN 'ilimitado'
                        WHEN SUM(c.llamadas) * 100.0 / a.rate_limit_rpd >= 90 THEN 'critico'
                        WHEN SUM(c.llamadas) * 100.0 / a.rate_limit_rpd >= 70 THEN 'advertencia'
                        ELSE 'ok'
                    END AS estado
                FROM ia_consumo_diario c
                JOIN ia_agentes a ON a.slug = c.agente_slug
                WHERE {cond_fecha}{cond_agente}{cond_empresa}
                GROUP BY c.agente_slug, a.nombre, a.modelo_id, a.tipo, a.rate_limit_rpd
                ORDER BY llamadas DESC
            """, params)
            filas = cur.fetchall()

            totales = {
                'llamadas':     sum(int(f['llamadas'] or 0) for f in filas),
                'tokens_total': sum(int(f['tokens_total'] or 0) for f in filas),
                'costo_usd':    round(sum(float(f['costo_usd'] or 0) for f in filas), 6),
                'errores':      sum(int(f['errores'] or 0) for f in filas),
            }

            alertas = [
                {
                    'agente':   f['agente_slug'],
                    'estado':   f['estado'],
                    'pct':      f['pct_limite_hoy'],
                    'llamadas': f['llamadas'],
                    'limite':   f['limite_rpd_diario'],
                }
                for f in filas if f['estado'] in ('critico', 'advertencia')
            ]

        return jsonify({
            'ok':        True,
            'periodo':   periodo,
            'totales':   totales,
            'por_agente': filas,
            'alertas':   alertas,
        })
    finally:
        conn.close()


@app.route('/ia/consumo/historico', methods=['GET'])
def endpoint_consumo_historico():
    """
    Consumo histórico día a día.
    Query params:
      ?dias=30              (default: 30, max: 365)
      ?agente=gemini-pro    (opcional)
      ?empresa=ori_sil_2    (opcional, filtra por empresa)
    """
    dias = min(int(request.args.get('dias', 30)), 365)
    agente_filtro = request.args.get('agente')
    empresa_filtro = request.args.get('empresa')

    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            params = [dias]
            cond_agente = ""
            cond_empresa = ""
            if agente_filtro:
                cond_agente = " AND c.agente_slug = %s"
                params.append(agente_filtro)
            if empresa_filtro:
                cond_empresa = " AND c.empresa = %s"
                params.append(empresa_filtro)

            cur.execute(f"""
                SELECT
                    c.fecha,
                    c.agente_slug,
                    a.nombre        AS agente_nombre,
                    a.modelo_id,
                    c.llamadas,
                    c.errores,
                    c.tokens_in,
                    c.tokens_out,
                    c.tokens_total,
                    c.costo_usd,
                    c.latencia_prom_ms
                FROM ia_consumo_diario c
                JOIN ia_agentes a ON a.slug = c.agente_slug
                WHERE c.fecha >= CURDATE() - INTERVAL %s DAY{cond_agente}{cond_empresa}
                ORDER BY c.fecha DESC, c.llamadas DESC
            """, params)
            filas = cur.fetchall()

        return jsonify({'ok': True, 'dias': dias, 'historico': filas, 'registros': filas})
    finally:
        conn.close()


@app.route('/ia/conexion/test', methods=['POST'])
def endpoint_test_conexion():
    """Prueba una conexión externa. Body: {conexion_id}"""
    from ia_service.conector import test_conexion
    data = request.get_json(silent=True) or {}
    conexion_id = data.get('conexion_id')
    if not conexion_id:
        return jsonify({'ok': False, 'mensaje': 'conexion_id requerido'}), 400
    resultado = test_conexion(int(conexion_id))
    return jsonify(resultado)


@app.route('/ia/conexion/test-params', methods=['POST'])
def endpoint_test_conexion_params():
    """Prueba conexión con parámetros crudos (sin guardar). Body: {tipo, host, puerto, usuario, password, base_datos}"""
    from ia_service.conector import get_conexion_externa
    data = request.get_json(silent=True) or {}
    cfg = {
        'tipo':       data.get('tipo', 'mariadb'),
        'host':       data.get('host', ''),
        'puerto':     int(data.get('puerto', 3306)),
        'usuario':    data.get('usuario', ''),
        'password':   data.get('password', ''),
        'base_datos': data.get('base_datos', ''),
    }
    if not cfg['host'] or not cfg['usuario'] or not cfg['base_datos']:
        return jsonify({'ok': False, 'mensaje': 'host, usuario y base_datos son obligatorios'}), 400
    conn_ext = None
    try:
        conn_ext = get_conexion_externa(cfg)
        tipo = cfg['tipo']
        with conn_ext.cursor() as cur:
            if tipo in ('mysql', 'mariadb'):
                cur.execute("SHOW TABLES")
                filas = cur.fetchall()
                tablas = [list(f.values())[0] for f in filas]
            else:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
                tablas = [r['table_name'] for r in cur.fetchall()]
        return jsonify({'ok': True, 'mensaje': f'Conexión exitosa. {len(tablas)} tablas.', 'tablas_disponibles': tablas})
    except Exception as e:
        return jsonify({'ok': False, 'mensaje': str(e), 'tablas_disponibles': []})
    finally:
        if conn_ext:
            conn_ext.close()


@app.route('/ia/esquema/sync', methods=['POST'])
def endpoint_sync_esquema():
    """Sincroniza el schema de un tema. Body: {tema_id, empresa}"""
    from ia_service.conector import sincronizar_schema
    data = request.get_json(silent=True) or {}
    tema_id = data.get('tema_id')
    empresa = data.get('empresa', 'ori_sil_2')
    if not tema_id:
        return jsonify({'ok': False, 'mensaje': 'tema_id requerido'}), 400
    resultado = sincronizar_schema(int(tema_id), empresa)
    return jsonify(resultado)


@app.route('/ia/logica-negocio', methods=['GET'])
def endpoint_logica_negocio_list():
    """Lista todos los fragmentos de lógica de negocio activos."""
    empresa = request.args.get('empresa', 'ori_sil_2')
    conn = get_local_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, concepto, palabras, siempre_presente, keywords, created_at "
            "FROM ia_logica_negocio WHERE empresa=%s AND activo=1 ORDER BY siempre_presente DESC, id",
            (empresa,)
        )
        rows = cur.fetchall()
    conn.close()
    return jsonify({'ok': True, 'fragmentos': rows})


@app.route('/ia/logica-negocio', methods=['POST'])
def endpoint_logica_negocio_crear():
    """
    Crea o actualiza un fragmento de lógica de negocio.
    Body: {concepto, explicacion, keywords, siempre_presente, empresa}
    Después de guardar, dispara el depurador si supera 800 palabras.
    """
    import threading
    from ia_service.aprendizaje import depurar_logica_negocio
    data = request.get_json(silent=True) or {}
    empresa   = data.get('empresa', 'ori_sil_2')
    concepto  = data.get('concepto', '').strip()
    explicacion = data.get('explicacion', '').strip()
    keywords  = data.get('keywords', '')
    siempre   = int(data.get('siempre_presente', 0))

    if not concepto or not explicacion:
        return jsonify({'ok': False, 'mensaje': 'concepto y explicacion son requeridos'}), 400

    palabras = len(explicacion.split())
    conn = get_local_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM ia_logica_negocio WHERE empresa=%s AND concepto=%s AND activo=1",
            (empresa, concepto)
        )
        existente = cur.fetchone()
        if existente:
            cur.execute(
                "UPDATE ia_logica_negocio SET explicacion=%s, keywords=%s, palabras=%s, updated_at=NOW() WHERE id=%s",
                (explicacion, keywords, palabras, existente['id'])
            )
            nuevo_id = existente['id']
        else:
            cur.execute(
                "INSERT INTO ia_logica_negocio (empresa, concepto, explicacion, keywords, siempre_presente, palabras) VALUES (%s,%s,%s,%s,%s,%s)",
                (empresa, concepto, explicacion, keywords, siempre, palabras)
            )
            nuevo_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Depurar en background si es necesario
    threading.Thread(target=depurar_logica_negocio, args=(empresa,), daemon=True).start()

    return jsonify({'ok': True, 'id': nuevo_id, 'palabras': palabras})


if __name__ == '__main__':
    print("Iniciando IA Service OS en puerto 5100...")
    app.run(host='0.0.0.0', port=5100, debug=False)
