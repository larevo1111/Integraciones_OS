#!/usr/bin/env python3
"""Override manual de una receta — sobrescribe la receta en BD con
valores dados por Claude (mi razonamiento) o Santi.

Uso como módulo:
  from override_receta import override
  override({
    'cod_articulo': '480',
    'patron': 'escalable',
    'cantidad_lote_std': None,
    'confianza': 'alta',
    'estado': 'validada',
    'notas': 'Tableta 50g puro. Cobertura 319 a 50g/unid. M.O. 0.0074h/unid.',
    'materiales': [
      {'cod': '319', 'cantidad_por_lote': 0.050, 'ratio_por_unidad': 0.050},
    ],
    'productos': [   # si solo hay principal, basta
      # { 'cod':'481', 'cantidad_por_lote': 1, 'ratio_por_unidad':1, 'precio_min_venta': 8900 }
    ],
    'costos': [
      {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
       'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
  })

Importante:
- Si 'ratio_por_unidad' no se pasa y es escalable, se infiere: ratio = cantidad_por_lote (cuando cant_lote=1).
- Auto-completa nombres de materiales y productos desde zeffi_inventario.
- Auto-completa precio venta si no se pasa.
- Deja los costos_unit de materiales desde zeffi_inventario.costo_manual.
"""
import sys
from _common import DbRecetas, q_effi, to_float, familia_por_nombre


def _info(cod):
    r = q_effi(
        "SELECT id, nombre, costo_manual FROM zeffi_inventario WHERE id=%s LIMIT 1",
        (cod,),
    )
    if not r:
        return {'id': cod, 'nombre': '???', 'costo_manual': 0}
    return r[0]


def _ult_precio(cod, minimo=100.0):
    r = q_effi(
        """SELECT precio_minimo_ud FROM zeffi_articulos_producidos ap
           JOIN zeffi_produccion_encabezados e ON e.id_orden=ap.id_orden
           WHERE ap.cod_articulo=%s AND ap.vigencia='Orden vigente' AND e.vigencia='Vigente'
             AND CAST(REPLACE(ap.precio_minimo_ud,',','.') AS DECIMAL(18,4))>=%s
           ORDER BY e.fecha_de_creacion DESC LIMIT 1""",
        (cod, minimo),
    )
    return to_float(r[0]['precio_minimo_ud']) if r else 0.0


def override(data: dict):
    cod = data['cod_articulo']
    info = _info(cod)
    nombre = info['nombre']
    familia = data.get('familia') or familia_por_nombre(nombre)
    patron = data['patron']
    cant_lote = data.get('cantidad_lote_std')
    unidad = data.get('unidad', 'und' if patron == 'lote_fijo' and cant_lote and cant_lote > 10 else 'kg')
    confianza = data.get('confianza', 'media')
    estado = data.get('estado', 'validada')
    notas = data.get('notas', 'Override manual.')
    n_ops = data.get('n_ops', 0)
    ops_ref = ','.join(str(x) for x in data.get('ops_referencia', []))

    with DbRecetas() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM prod_recetas WHERE cod_articulo=%s", (cod,)
            )
            row = cur.fetchone()

            if row:
                rid = row['id']
                cur.execute(
                    """UPDATE prod_recetas SET
                       nombre=%s, familia=%s, patron=%s, cantidad_lote_std=%s,
                       unidad_producto=%s, confianza=%s, estado=%s,
                       n_ops_analizadas=%s, ops_referencia=%s, notas_analisis=%s,
                       validated_at=CASE WHEN %s='validada' THEN NOW() ELSE validated_at END
                       WHERE id=%s""",
                    (nombre, familia, patron, cant_lote, unidad, confianza,
                     estado, n_ops, ops_ref, notas, estado, rid),
                )
                cur.execute("DELETE FROM prod_recetas_materiales WHERE receta_id=%s", (rid,))
                cur.execute("DELETE FROM prod_recetas_productos WHERE receta_id=%s", (rid,))
                cur.execute("DELETE FROM prod_recetas_costos WHERE receta_id=%s", (rid,))
            else:
                cur.execute(
                    """INSERT INTO prod_recetas (cod_articulo,nombre,familia,patron,
                       cantidad_lote_std,unidad_producto,confianza,estado,
                       n_ops_analizadas,ops_referencia,notas_analisis,validated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       CASE WHEN %s='validada' THEN NOW() ELSE NULL END)""",
                    (cod, nombre, familia, patron, cant_lote, unidad, confianza,
                     estado, n_ops, ops_ref, notas, estado),
                )
                rid = cur.lastrowid

            # Materiales
            for m in data.get('materiales', []):
                m_info = _info(m['cod'])
                cost = m.get('costo_unit_snapshot', to_float(m_info.get('costo_manual') or 0))
                ratio = m.get('ratio_por_unidad', m['cantidad_por_lote'])
                cur.execute(
                    """INSERT INTO prod_recetas_materiales
                       (receta_id, cod_material, nombre, cantidad_por_lote,
                        ratio_por_unidad, costo_unit_snapshot, n_ops_aparece)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (rid, m['cod'], m_info['nombre'],
                     m['cantidad_por_lote'], ratio, cost, m.get('n_ops_aparece', 0)),
                )

            # Producto principal (siempre el cod_articulo)
            ppal_ratio = 1.0
            ppal_cant = data.get('cantidad_principal', cant_lote or 1.0)
            precio_ppal = data.get('precio_min_venta_principal', _ult_precio(cod))
            cur.execute(
                """INSERT INTO prod_recetas_productos
                   (receta_id, cod_articulo, nombre, es_principal,
                    cantidad_por_lote, ratio_por_unidad,
                    precio_min_venta_snapshot, n_ops_aparece)
                   VALUES (%s,%s,%s,1,%s,%s,%s,%s)""",
                (rid, cod, nombre, ppal_cant, ppal_ratio, precio_ppal, n_ops),
            )

            # Co-productos si se pasan
            for p in data.get('productos', []):
                p_info = _info(p['cod'])
                precio = p.get('precio_min_venta_snapshot', _ult_precio(p['cod']))
                cur.execute(
                    """INSERT INTO prod_recetas_productos
                       (receta_id, cod_articulo, nombre, es_principal,
                        cantidad_por_lote, ratio_por_unidad,
                        precio_min_venta_snapshot, n_ops_aparece)
                       VALUES (%s,%s,%s,0,%s,%s,%s,%s)""",
                    (rid, p['cod'], p_info['nombre'],
                     p['cantidad_por_lote'],
                     p.get('ratio_por_unidad', p['cantidad_por_lote']),
                     precio, p.get('n_ops_aparece', 0)),
                )

            # Costos
            for c in data.get('costos', []):
                cur.execute(
                    """INSERT INTO prod_recetas_costos
                       (receta_id, tipo_costo_id, nombre, cantidad_por_lote, costo_unit)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (rid, c.get('tipo_costo_id', 0), c['nombre'],
                     c['cantidad_por_lote'], c['costo_unit']),
                )

            return rid


if __name__ == '__main__':
    import json
    if len(sys.argv) < 2:
        print('Uso: python3 override_receta.py <archivo.json>')
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    rid = override(data)
    print(f"✓ Receta id={rid} cod={data['cod_articulo']} actualizada.")
