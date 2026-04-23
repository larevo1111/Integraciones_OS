#!/usr/bin/env python3
"""Corre persistir_receta para TODOS los productos del universo (2025-01-01→hoy).
Graba todas como borrador. Después Claude/Santi valida familia por familia.

Uso:
  python3 persistir_todas.py                    # todos los pendientes
  python3 persistir_todas.py --familia mieles   # solo una familia
  python3 persistir_todas.py --force            # regenera incluso las ya persistidas
"""
import sys
import traceback
from listar_universo import universo_effi, recetas_existentes
from persistir_receta import persistir
from _common import familia_por_nombre


def main():
    args = sys.argv[1:]
    filtro_familia = None
    force = False
    if '--familia' in args:
        filtro_familia = args[args.index('--familia') + 1]
    if '--force' in args:
        force = True

    productos = universo_effi()
    existentes = recetas_existentes()

    if filtro_familia:
        productos = [p for p in productos if familia_por_nombre(p['nombre']) == filtro_familia]

    if not force:
        productos = [p for p in productos if p['cod'] not in existentes]

    print(f"Procesando {len(productos)} productos...")
    print('-' * 80)

    ok = 0
    fail = 0
    errores = []
    for i, p in enumerate(productos, 1):
        cod = p['cod']
        nombre = (p['nombre'] or '')[:45]
        try:
            receta_id, r = persistir(
                cod,
                cantidad_ref=None,
                estado='borrador',
                notas='Generada automáticamente por motor de atribución v2. Requiere revisión manual.',
            )
            print(
                f"[{i:>3}/{len(productos)}] {cod:<6} {nombre:<45} "
                f"patrón={r['patron']:<10} conf={r['confianza']:<6} "
                f"mats={len(r['materiales'])} costos={len(r['costos_produccion'])}"
            )
            ok += 1
        except Exception as e:
            print(f"[{i:>3}/{len(productos)}] {cod:<6} {nombre:<45} ERROR: {e}")
            fail += 1
            errores.append((cod, str(e)))

    print('-' * 80)
    print(f"OK: {ok}  FAIL: {fail}")
    if errores:
        print('\nErrores:')
        for c, e in errores:
            print(f"  {c}: {e}")


if __name__ == '__main__':
    main()
