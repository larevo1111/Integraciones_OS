#!/usr/bin/env python3
"""Persiste una receta construida en la BD VPS inventario_produccion_effi.

Uso:
  python3 persistir_receta.py <cod> [--cantidad N] [--estado borrador|validada] [--notas "texto"]
  python3 persistir_receta.py <cod> --delete         # borrar receta
"""
import sys
from _common import DbRecetas
from construir_receta import construir


def borrar(cod: str):
    with DbRecetas() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM prod_recetas WHERE cod_articulo=%s", (cod,))
            return cur.rowcount


def persistir(cod: str, cantidad_ref=None, estado='borrador', notas=''):
    receta = construir(cod, cantidad_ref)
    ops_ref_csv = ','.join(str(x) for x in receta.get('ops_referencia', []))

    with DbRecetas() as conn:
        with conn.cursor() as cur:
            # Existe?
            cur.execute(
                "SELECT id FROM prod_recetas WHERE cod_articulo=%s", (cod,)
            )
            row = cur.fetchone()

            if row:
                receta_id = row['id']
                cur.execute(
                    """
                    UPDATE prod_recetas SET
                        nombre=%s, familia=%s, patron=%s, cantidad_lote_std=%s,
                        unidad_producto=%s, confianza=%s, estado=%s,
                        n_ops_analizadas=%s, ops_referencia=%s,
                        notas_analisis=COALESCE(NULLIF(%s,''), notas_analisis),
                        validated_at = CASE WHEN %s='validada' AND validated_at IS NULL
                                            THEN NOW() ELSE validated_at END
                    WHERE id=%s
                    """,
                    (
                        receta['nombre'], receta['familia'], receta['patron'],
                        receta['cantidad_lote_std'], receta['unidad'],
                        receta['confianza'], estado,
                        receta['n_ops_analizadas'], ops_ref_csv,
                        notas, estado, receta_id,
                    ),
                )
                cur.execute("DELETE FROM prod_recetas_materiales WHERE receta_id=%s", (receta_id,))
                cur.execute("DELETE FROM prod_recetas_productos WHERE receta_id=%s", (receta_id,))
                cur.execute("DELETE FROM prod_recetas_costos WHERE receta_id=%s", (receta_id,))
            else:
                cur.execute(
                    """
                    INSERT INTO prod_recetas
                      (cod_articulo, nombre, familia, patron, cantidad_lote_std,
                       unidad_producto, confianza, estado, n_ops_analizadas,
                       ops_referencia, notas_analisis, validated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            CASE WHEN %s='validada' THEN NOW() ELSE NULL END)
                    """,
                    (
                        cod, receta['nombre'], receta['familia'],
                        receta['patron'], receta['cantidad_lote_std'],
                        receta['unidad'], receta['confianza'], estado,
                        receta['n_ops_analizadas'], ops_ref_csv,
                        notas or None, estado,
                    ),
                )
                receta_id = cur.lastrowid

            # Materiales
            for m in receta['materiales']:
                cur.execute(
                    """INSERT INTO prod_recetas_materiales
                       (receta_id, cod_material, nombre, cantidad_por_lote,
                        ratio_por_unidad, costo_unit_snapshot, n_ops_aparece)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        receta_id, m['cod'], m['nombre'],
                        m['cantidad_por_lote'], m['ratio_por_unidad'],
                        m['costo_unit_actual'], m['n_ops_aparece'],
                    ),
                )

            # Productos
            for p in receta['productos']:
                cur.execute(
                    """INSERT INTO prod_recetas_productos
                       (receta_id, cod_articulo, nombre, es_principal,
                        cantidad_por_lote, ratio_por_unidad,
                        precio_min_venta_snapshot, n_ops_aparece)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        receta_id, p['cod'], p['nombre'], p['es_principal'],
                        p['cantidad_por_lote'], p['ratio_por_unidad'],
                        p['precio_min_venta_actual'], p['n_ops_aparece'],
                    ),
                )

            # Costos
            for c in receta['costos_produccion']:
                cur.execute(
                    """INSERT INTO prod_recetas_costos
                       (receta_id, tipo_costo_id, nombre, cantidad_por_lote, costo_unit)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        receta_id, 0,  # tipo_costo_id se resuelve luego (cruce por nombre)
                        c['cp'], c['cantidad_por_lote'], c['costo_unit'],
                    ),
                )
            return receta_id, receta


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python3 persistir_receta.py <cod> [--cantidad N] [--estado borrador|validada] [--notas "texto"]')
        print('     python3 persistir_receta.py <cod> --delete')
        sys.exit(1)
    cod = sys.argv[1]

    if '--delete' in sys.argv:
        n = borrar(cod)
        print(f'Eliminadas {n} receta(s) de cod={cod}')
        sys.exit(0)

    cantidad = None
    if '--cantidad' in sys.argv:
        cantidad = float(sys.argv[sys.argv.index('--cantidad') + 1])
    estado = 'borrador'
    if '--estado' in sys.argv:
        estado = sys.argv[sys.argv.index('--estado') + 1]
    notas = ''
    if '--notas' in sys.argv:
        notas = sys.argv[sys.argv.index('--notas') + 1]

    receta_id, receta = persistir(cod, cantidad, estado, notas)
    print(f"✓ Persistida receta_id={receta_id} cod={cod} estado={estado}")
    print(f"  Patrón={receta['patron']} lote_std={receta['cantidad_lote_std']} confianza={receta['confianza']}")
    print(f"  Materiales={len(receta['materiales'])} productos={len(receta['productos'])} costos={len(receta['costos_produccion'])}")
