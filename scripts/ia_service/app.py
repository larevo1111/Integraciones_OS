"""
Flask API — Servicio Central de IA
Puerto: 5100
Endpoints:
  POST /ia/consultar  — consulta principal
  GET  /ia/agentes    — lista agentes disponibles
  GET  /ia/tipos      — lista tipos de consulta
  GET  /ia/health     — health check
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
    return jsonify({'ok': True, 'servicio': 'ia_service_os', 'version': '1.0'})


@app.route('/ia/consultar', methods=['POST'])
def endpoint_consultar():
    """
    Body JSON esperado:
    {
        "pregunta":        "¿Cuánto vendimos ayer?",   -- requerido
        "tipo":            "analisis_datos",            -- opcional
        "agente":          "gemini-flash",              -- opcional
        "usuario_id":      "santi",                     -- opcional (default: "anonimo")
        "canal":           "telegram",                  -- opcional (default: "api")
        "conversacion_id": 42,                          -- opcional
        "nombre_usuario":  "Santiago",                  -- opcional
        "contexto_extra":  "..."                        -- opcional
    }
    """
    data = request.get_json(silent=True) or {}

    pregunta = data.get('pregunta', '').strip()
    if not pregunta:
        return jsonify({'ok': False, 'error': 'El campo "pregunta" es requerido.'}), 400

    resultado = consultar(
        pregunta        = pregunta,
        tipo            = data.get('tipo'),
        agente          = data.get('agente'),
        usuario_id      = data.get('usuario_id', 'anonimo'),
        canal           = data.get('canal', 'api'),
        conversacion_id = data.get('conversacion_id'),
        nombre_usuario  = data.get('nombre_usuario'),
        contexto_extra  = data.get('contexto_extra', ''),
    )
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


if __name__ == '__main__':
    print("Iniciando IA Service OS en puerto 5100...")
    app.run(host='0.0.0.0', port=5100, debug=False)
