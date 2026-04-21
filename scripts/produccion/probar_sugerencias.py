#!/usr/bin/env python3
"""
Pruebas masivas de sugerir_receta.py contra OPs reales.

Para cada artículo, compara la sugerencia contra TODAS las OPs limpias (no outliers)
y reporta el match promedio. El objetivo NO es que coincida con una OP específica,
sino que la sugerencia esté en línea con el promedio de las OPs históricas limpias.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local
import pymysql
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sugerir_receta import sugerir_receta, obtener_detalle_op, to_float
from statistics import median

DB_EFFI = dict(**cfg_local(), database='effi_data', cursorclass=pymysql.cursors.DictCursor)


def q(sql, params=None):
    conn = pymysql.connect(**DB_EFFI)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def articulos_con_ops(min_ops=4, limit=30):
    return q("""
        SELECT ap.cod_articulo AS cod, LEFT(ap.descripcion_articulo_producido, 50) AS nombre,
               COUNT(DISTINCT ap.id_orden) AS n_ops
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.vigencia = 'Orden vigente' AND e.vigencia = 'Vigente'
          AND e.fecha_de_creacion > '2026-01-01'
        GROUP BY ap.cod_articulo, ap.descripcion_articulo_producido
        HAVING n_ops >= %s
        ORDER BY n_ops DESC
        LIMIT %s
    """, (min_ops, limit))


def calcular_score(cod, cantidad_test, sug, verbose=False):
    """
    Compara la sugerencia contra la mediana de las OPs limpias.
    - Para escalable: compara ratios material/producido
    - Para lote_fijo: compara cantidades absolutas dividiendo por n_lotes
    """
    ops_ref = sug.get('ops_referencia', [])
    outliers = set(sug.get('ops_outlier_descartadas', []))
    ops_limpias = [op for op in ops_ref if op not in outliers]
    if not ops_limpias:
        return None, 'Sin OPs limpias'

    es_lote_fijo = sug['patron'] == 'lote_fijo'
    n_lotes = sug.get('n_lotes') or 1

    scores = []
    for mat_sug in sug['materiales']:
        cod_mat = mat_sug['cod']
        valores_reales = []
        for op_id in ops_limpias:
            detalle = obtener_detalle_op(op_id)
            cant_prod = sum(to_float(p['cantidad']) for p in detalle['producidos'] if p['cod'] == cod)
            if cant_prod <= 0: continue
            for m in detalle['materiales']:
                if m['cod'] == cod_mat:
                    cant_mat = to_float(m['cantidad'])
                    if es_lote_fijo:
                        valores_reales.append(cant_mat)
                    else:
                        valores_reales.append(cant_mat / cant_prod)
                    break
        if len(valores_reales) < 2:
            continue
        real_med = median(valores_reales)
        if real_med == 0:
            continue
        if es_lote_fijo:
            sugerido_norm = mat_sug['cantidad'] / n_lotes
        else:
            sugerido_norm = mat_sug['ratio_unit']
        diff_pct = abs(sugerido_norm - real_med) / abs(real_med) * 100
        scores.append(diff_pct)
    if not scores:
        return None, 'Sin materiales para comparar'
    return {'avg_diff': sum(scores)/len(scores), 'max_diff': max(scores), 'n_mats': len(scores)}, None


def main():
    arts = articulos_con_ops(min_ops=4, limit=20)
    print(f'\n{"="*100}')
    print(f'PRUEBAS MASIVAS: {len(arts)} artículos · sugerir_receta.py')
    print(f'{"="*100}')
    print(f'{"Cód":>4} | {"Nombre":<40} | {"N OPs":>5} | {"Patrón":<10} | {"Conf":<6} | {"Avg Δ%":>7} | {"Max Δ%":>7} | Estado')
    print(f'{"-"*100}')

    import random
    random.seed(42)
    resumen = {'perfecto': 0, 'bueno': 0, 'aceptable': 0, 'malo': 0, 'sin_data': 0}
    detalles_problemas = []

    for art in arts:
        cant = random.choice([4, 10, 25, 50, 100])
        try:
            sug = sugerir_receta(art['cod'], cant, n_ops=10)
            if sug['patron'] == 'sin_historia':
                print(f'{art["cod"]:>4} | {art["nombre"][:40]:<40} | {art["n_ops"]:>5} | sin_historia')
                resumen['sin_data'] += 1
                continue

            score, error = calcular_score(art['cod'], cant, sug)
            if error:
                print(f'{art["cod"]:>4} | {art["nombre"][:40]:<40} | {art["n_ops"]:>5} | {sug["patron"]:<10} | — | — | {error}')
                resumen['sin_data'] += 1
                continue

            avg = score['avg_diff']
            mx = score['max_diff']

            if avg < 5 and mx < 15:
                estado = '✅ Perfecto'; resumen['perfecto'] += 1
            elif avg < 15 and mx < 30:
                estado = '👍 Bueno'; resumen['bueno'] += 1
            elif avg < 30:
                estado = '⚠️  Aceptable'; resumen['aceptable'] += 1
            else:
                estado = '❌ Malo'; resumen['malo'] += 1
                detalles_problemas.append((art, sug, score))

            print(f'{art["cod"]:>4} | {art["nombre"][:40]:<40} | {art["n_ops"]:>5} | {sug["patron"]:<10} | {sug["confianza"]:<6} | {avg:>6.1f}% | {mx:>6.1f}% | {estado}')

        except Exception as e:
            print(f'{art["cod"]:>4} | ERROR: {e}')

    print(f'{"-"*100}')
    total = sum(resumen.values())
    print(f'Resumen de {total} pruebas:')
    print(f'  ✅ Perfecto (avg<5% y max<15%): {resumen["perfecto"]}')
    print(f'  👍 Bueno (avg<15% y max<30%): {resumen["bueno"]}')
    print(f'  ⚠️  Aceptable (avg<30%):       {resumen["aceptable"]}')
    print(f'  ❌ Malo (avg>=30%):           {resumen["malo"]}')
    print(f'  ❓ Sin data:                  {resumen["sin_data"]}')

    if detalles_problemas:
        print(f'\n{"="*100}')
        print(f'DETALLE DE CASOS PROBLEMÁTICOS')
        print(f'{"="*100}')
        for art, sug, score in detalles_problemas:
            print(f'\n--- {art["cod"]} {art["nombre"]} ---')
            print(f'  Patrón: {sug["patron"]} | OPs limpias: {sug["ops_efectivas"] - len(sug["ops_outlier_descartadas"])}')
            print(f'  Outliers: {sug["ops_outlier_descartadas"]}')
            print(f'  Observaciones: {sug["observaciones"]}')


if __name__ == '__main__':
    main()
