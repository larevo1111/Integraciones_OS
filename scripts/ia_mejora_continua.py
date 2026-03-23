"""
Script de mejora continua del servicio de IA.
Procesa feedback acumulado → genera ejemplos SQL → detecta patrones → genera reglas.

Diseñado para eficiencia de tokens:
  - Correcciones ya resueltas (retry exitoso) → 0 tokens, solo guardar ejemplo
  - Errores sin resolver → agente barato (gemini-flash-lite) con DDL mínimo
  - Detección de patrones → regex/conteo, sin LLM

Uso:
  python3 scripts/ia_mejora_continua.py                    # procesar todo
  python3 scripts/ia_mejora_continua.py --max 5            # máximo 5 correcciones
  python3 scripts/ia_mejora_continua.py --solo-patrones    # solo detectar patrones
  python3 scripts/ia_mejora_continua.py --dry-run          # simular sin cambios
"""
import argparse
import json
import re
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ia_service.config import get_local_conn
from ia_service import ejecutor_sql, esquema
from ia_service.aprendizaje import guardar_ejemplo_sql, registrar_feedback
from ia_service.alertas import notificar


# ── Configuración ────────────────────────────────────────────────────────────

AGENTES_BARATOS = ['gemini-flash-lite', 'cerebras-llama', 'groq-llama']
MAX_TOKENS_CORRECCION = 1000
PATRON_MIN_OCURRENCIAS = 3  # mínimo errores iguales para generar regla


def log(msg: str):
    print(f"[mejora] {msg}")


# ── 1. Recolectar feedback pendiente ─────────────────────────────────────────

def recolectar_pendientes(empresa: str, limite: int = 50) -> dict:
    """
    Lee feedback no procesado, separado por tipo.
    Returns: {'correcciones': [...], 'errores': [...]}
    """
    conn = get_local_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM ia_feedback WHERE empresa=%s AND procesado=0 "
            "ORDER BY created_at ASC LIMIT %s",
            (empresa, limite)
        )
        filas = cur.fetchall()
    conn.close()

    correcciones = [f for f in filas if f['tipo'] == 'correccion']
    errores = [f for f in filas if f['tipo'] == 'sql_error']
    return {'correcciones': correcciones, 'errores': errores}


# ── 2. Incorporar correcciones ya resueltas (0 tokens) ──────────────────────

def incorporar_correcciones(correcciones: list, empresa: str, dry_run: bool = False) -> int:
    """
    Las correcciones ya tienen sql_correcto (el retry las resolvió).
    Solo hay que guardarlas como ejemplos Q→SQL y marcar procesado.
    Costo: 0 tokens LLM.
    """
    incorporadas = 0
    conn = get_local_conn()

    for c in correcciones:
        pregunta = c.get('pregunta', '')
        sql_ok = c.get('sql_correcto', '')
        if not pregunta or not sql_ok:
            # Marcar como procesado aunque no se pueda incorporar
            if not dry_run:
                _marcar_procesado(conn, c['id'], 'sin pregunta o sql_correcto')
            continue

        if dry_run:
            log(f"  [dry-run] Incorporaría corrección #{c['id']}: {pregunta[:60]}...")
        else:
            guardar_ejemplo_sql(empresa, pregunta, sql_ok)
            _marcar_procesado(conn, c['id'], 'incorporado como ejemplo')
            incorporadas += 1

    conn.close()
    return incorporadas


# ── 3. Corregir errores no resueltos (tokens mínimos) ───────────────────────

def _cargar_agente_barato():
    """Carga el primer agente barato disponible."""
    from ia_service.servicio import _cargar_agente
    for slug in AGENTES_BARATOS:
        agente = _cargar_agente(slug)
        if agente and agente.get('api_key'):
            return agente
    return None


def corregir_errores(errores: list, empresa: str, max_corr: int = 10,
                     dry_run: bool = False) -> dict:
    """
    Para cada error SQL no resuelto:
    1. Genera SQL corregido con agente barato + DDL mínimo
    2. Verifica contra BD real
    3. Si funciona → guarda como ejemplo
    Costo: ~200-500 tokens por error (DDL reducido + prompt corto).
    """
    from ia_service.servicio import _llamar_agente

    agente = _cargar_agente_barato()
    if not agente:
        log("No hay agente barato disponible — saltando correcciones")
        return {'corregidos': 0, 'fallidos': 0}

    # DDL reducido — solo tablas principales
    ddl = esquema.obtener_ddl()

    corregidos = 0
    fallidos = 0
    conn = get_local_conn()

    for err in errores[:max_corr]:
        pregunta = err.get('pregunta', '')
        sql_malo = err.get('sql_fallido', '')
        error_msg = err.get('error_original', '')

        if not pregunta or not sql_malo:
            if not dry_run:
                _marcar_procesado(conn, err['id'], 'sin datos suficientes')
            continue

        if dry_run:
            log(f"  [dry-run] Corregiría error #{err['id']}: {pregunta[:60]}...")
            continue

        # Prompt mínimo — eficiente en tokens
        msgs = [
            {'role': 'system', 'content': (
                f"Corriges SQL para MariaDB. Solo respondes con el SQL corregido "
                f"dentro de ```sql```, sin explicación.\n\n"
                f"Esquema disponible:\n{ddl[:3000]}"  # máx 3K chars de DDL
            )},
            {'role': 'user', 'content': (
                f"Pregunta: {pregunta}\n"
                f"SQL que falló:\n{sql_malo}\n"
                f"Error: {error_msg}\n\n"
                f"Corrige el SQL."
            )},
        ]

        res = _llamar_agente(agente, msgs, temperatura=0.1, max_tokens=MAX_TOKENS_CORRECCION)
        if not res.get('ok') or not res.get('texto'):
            _marcar_procesado(conn, err['id'], f"agente no respondió: {res.get('error', '?')}")
            fallidos += 1
            continue

        # Extraer SQL de la respuesta
        from ia_service.formateador import extraer_sql
        sql_nuevo = extraer_sql(res['texto'])
        if not sql_nuevo:
            _marcar_procesado(conn, err['id'], 'no se pudo extraer SQL de la respuesta')
            fallidos += 1
            continue

        # Verificar contra BD real
        resultado = ejecutor_sql.ejecutar(sql_nuevo)
        if resultado['ok']:
            guardar_ejemplo_sql(empresa, pregunta, sql_nuevo)
            # También registrar como corrección para historial
            registrar_feedback(
                empresa, 'correccion', pregunta,
                sql_fallido=sql_malo, sql_correcto=sql_nuevo,
                error_original=error_msg,
                notas='corregido por ia_mejora_continua',
            )
            _marcar_procesado(conn, err['id'], f"corregido → ejemplo guardado (agente: {agente['slug']})")
            corregidos += 1
            log(f"  ✓ Error #{err['id']} corregido: {pregunta[:50]}...")
        else:
            _marcar_procesado(conn, err['id'],
                              f"corrección falló: {resultado.get('error', '?')[:200]}")
            fallidos += 1
            log(f"  ✗ Error #{err['id']} no se pudo corregir")

    conn.close()
    return {'corregidos': corregidos, 'fallidos': fallidos}


# ── 4. Detector de patrones (0 tokens) ──────────────────────────────────────

# Patrones conocidos de errores SQL con la corrección correspondiente
PATRONES_CONOCIDOS = [
    {
        'regex': r"Unknown column '([^']+)'",
        'concepto': 'Columna inexistente: {match}',
        'keywords': 'columna,error,sql,{match}',
        'explicacion': (
            'El LLM genera SQL con la columna "{match}" que no existe. '
            'Verificar con DESCRIBE la tabla correcta antes de usar esa columna.'
        ),
    },
    {
        'regex': r"Table '([^']+)' doesn't exist",
        'concepto': 'Tabla inexistente: {match}',
        'keywords': 'tabla,error,sql,{match}',
        'explicacion': (
            'El LLM referencia la tabla "{match}" que no existe en la BD. '
            'Las tablas disponibles empiezan con zeffi_ o resumen_.'
        ),
    },
]


def detectar_patrones(empresa: str, dias: int = 7, dry_run: bool = False) -> int:
    """
    Analiza errores de los últimos N días y detecta patrones recurrentes.
    Si un patrón aparece ≥3 veces, genera una regla en ia_logica_negocio.
    Costo: 0 tokens (puro regex/SQL).
    """
    conn = get_local_conn()

    # Obtener errores recientes (procesados o no)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT error_original, sql_fallido, pregunta FROM ia_feedback "
            "WHERE empresa=%s AND tipo='sql_error' "
            "AND created_at >= NOW() - INTERVAL %s DAY",
            (empresa, dias)
        )
        errores = cur.fetchall()

    if not errores:
        conn.close()
        return 0

    # Contar ocurrencias de cada patrón
    reglas_generadas = 0
    for patron in PATRONES_CONOCIDOS:
        matches = {}
        for err in errores:
            error_txt = err.get('error_original', '') or ''
            m = re.search(patron['regex'], error_txt)
            if m:
                valor = m.group(1)
                matches.setdefault(valor, []).append(err)

        for valor, ocurrencias in matches.items():
            if len(ocurrencias) < PATRON_MIN_OCURRENCIAS:
                continue

            concepto = patron['concepto'].format(match=valor)
            keywords = patron['keywords'].format(match=valor)
            explicacion = patron['explicacion'].format(match=valor)
            explicacion += f" (detectado {len(ocurrencias)} veces en los últimos {dias} días)"

            if dry_run:
                log(f"  [dry-run] Generaría regla: {concepto} ({len(ocurrencias)} ocurrencias)")
                reglas_generadas += 1
                continue

            # Verificar si ya existe regla para este concepto
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM ia_logica_negocio "
                    "WHERE empresa=%s AND concepto=%s AND activo=1",
                    (empresa, concepto)
                )
                if cur.fetchone():
                    continue  # Ya existe, no duplicar

                palabras = len(explicacion.split())
                cur.execute("""
                    INSERT INTO ia_logica_negocio
                    (empresa, concepto, explicacion, keywords, siempre_presente, palabras, creado_por)
                    VALUES (%s, %s, %s, %s, 0, %s, %s)
                """, (empresa, concepto, explicacion, keywords, palabras, 'mejora-continua'))
            conn.commit()
            reglas_generadas += 1
            log(f"  → Regla generada: {concepto} ({len(ocurrencias)} ocurrencias)")

    conn.close()
    return reglas_generadas


# ── 5. Suite de verificación básica ──────────────────────────────────────────

SUITE_BASICA = [
    ("¿Cuánto vendimos ayer?", 'analisis_datos'),
    ("Hola", 'conversacion'),
    ("Top 3 clientes este mes", 'analisis_datos'),
]


def verificar_servicio(empresa: str) -> dict:
    """
    Ejecuta consultas de verificación para asegurar que el servicio funciona.
    Returns: {'total': N, 'ok': N, 'fallidas': [...]}
    """
    from ia_service import consultar

    resultados = {'total': len(SUITE_BASICA), 'ok': 0, 'fallidas': []}

    for pregunta, tipo_esperado in SUITE_BASICA:
        try:
            res = consultar(
                pregunta=pregunta,
                usuario_id='mejora-continua',
                canal='script',
                empresa=empresa,
            )
            if res.get('ok'):
                resultados['ok'] += 1
            else:
                resultados['fallidas'].append({
                    'pregunta': pregunta,
                    'error': res.get('error', 'respuesta no ok'),
                })
        except Exception as e:
            resultados['fallidas'].append({
                'pregunta': pregunta,
                'error': str(e),
            })

    return resultados


# ── Utilidades ───────────────────────────────────────────────────────────────

def _marcar_procesado(conn, feedback_id: int, notas: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ia_feedback SET procesado=1, notas=%s WHERE id=%s",
            (notas[:500], feedback_id)
        )
    conn.commit()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Mejora continua del servicio de IA')
    parser.add_argument('--empresa', default='ori_sil_2')
    parser.add_argument('--max', type=int, default=10, help='Máx correcciones con LLM')
    parser.add_argument('--solo-patrones', action='store_true', help='Solo detectar patrones')
    parser.add_argument('--dry-run', action='store_true', help='Simular sin cambios')
    parser.add_argument('--verificar', action='store_true', help='Ejecutar suite de verificación')
    args = parser.parse_args()

    t0 = time.time()
    resumen = {'incorporadas': 0, 'corregidos': 0, 'fallidos': 0, 'reglas': 0}

    log(f"Inicio — empresa={args.empresa}, max={args.max}, dry_run={args.dry_run}")

    if not args.solo_patrones:
        # Paso 1: Recolectar
        pendientes = recolectar_pendientes(args.empresa, limite=args.max * 3)
        n_corr = len(pendientes['correcciones'])
        n_err = len(pendientes['errores'])
        log(f"Pendientes: {n_corr} correcciones, {n_err} errores sin resolver")

        # Paso 2: Incorporar correcciones (0 tokens)
        if pendientes['correcciones']:
            resumen['incorporadas'] = incorporar_correcciones(
                pendientes['correcciones'], args.empresa, args.dry_run
            )
            log(f"Correcciones incorporadas: {resumen['incorporadas']}")

        # Paso 3: Corregir errores (tokens mínimos)
        if pendientes['errores']:
            res_corr = corregir_errores(
                pendientes['errores'], args.empresa, args.max, args.dry_run
            )
            resumen['corregidos'] = res_corr['corregidos']
            resumen['fallidos'] = res_corr['fallidos']
            log(f"Errores: {res_corr['corregidos']} corregidos, {res_corr['fallidos']} no resueltos")

    # Paso 4: Detectar patrones (0 tokens)
    resumen['reglas'] = detectar_patrones(args.empresa, dry_run=args.dry_run)
    if resumen['reglas']:
        log(f"Reglas generadas: {resumen['reglas']}")

    # Paso 5: Verificación (opcional)
    if args.verificar:
        log("Ejecutando suite de verificación...")
        verif = verificar_servicio(args.empresa)
        log(f"Verificación: {verif['ok']}/{verif['total']} OK")
        if verif['fallidas']:
            for f in verif['fallidas']:
                log(f"  ✗ {f['pregunta']}: {f['error'][:100]}")

    # Resumen
    elapsed = time.time() - t0
    log(f"Completado en {elapsed:.1f}s — "
        f"{resumen['incorporadas']} incorporadas, "
        f"{resumen['corregidos']} corregidos, "
        f"{resumen['fallidos']} fallidos, "
        f"{resumen['reglas']} reglas nuevas")

    # Notificar si hubo cambios
    total_cambios = resumen['incorporadas'] + resumen['corregidos'] + resumen['reglas']
    if total_cambios > 0 and not args.dry_run:
        notificar(
            f"🔧 <b>Mejora continua IA</b>\n"
            f"Ejemplos incorporados: {resumen['incorporadas']}\n"
            f"Errores corregidos: {resumen['corregidos']}\n"
            f"Reglas nuevas: {resumen['reglas']}\n"
            f"⏱️ {elapsed:.1f}s"
        )

    return resumen


if __name__ == '__main__':
    main()
