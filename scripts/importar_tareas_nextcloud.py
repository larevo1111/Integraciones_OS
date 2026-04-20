#!/usr/bin/env python3
"""
Importar tareas de Nextcloud (BD local) a Sistema Gestión OS (Hostinger).
Lee de oc_calendars + oc_calendarobjects, parsea iCalendar VTODO,
genera un solo archivo SQL y lo envía en una conexión SSH.
"""

import re
import subprocess
import sys
import tempfile
import os
import mysql.connector

# ── Conexiones (via helper central) ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local, cfg_remota_ssh, cfg_remota_db
LOCAL_DB = dict(**cfg_local(), database='nextcloud')

CALENDARIOS = {
    '01_Ventas': 1,
    '02_Cartera': 2,
    '03_Produccion': 3,
    '05_Administrativo': 5,
    '06_Informes': 6,
    '07_Contenido_y_Marca': 7,
    '08_Sistemas': 8,
    '11_Reuniones': 11,
    '12_Varios': 12,
}

EMPRESA = 'Ori_Sil_2'
EMAIL_SANTI = 'ssierra047@gmail.com'
EMAIL_JEN = 'jennifercanogarcia@gmail.com'

_ssh = cfg_remota_ssh('GESTION')
_dbg = cfg_remota_db('GESTION')
SSH_BASE = f"ssh -i {_ssh['key']} -p {_ssh['port']} {_ssh['user']}@{_ssh['host']}"
MYSQL_REMOTE = f"mysql -u {_dbg['user']} -p'{_dbg['password']}' {_dbg['database']}"


def ssh_mysql_file(sql_file_path):
    """Envía un archivo SQL a Hostinger via SSH stdin. Una sola conexión."""
    cmd = f'{SSH_BASE} "{MYSQL_REMOTE}"'
    with open(sql_file_path, 'r') as f:
        r = subprocess.run(cmd, shell=True, stdin=f, capture_output=True, text=True)
    if r.returncode != 0:
        err = '\n'.join(l for l in r.stderr.strip().split('\n') if 'password' not in l.lower())
        if err:
            print(f"  [ERROR SSH] {err}")
    return r.stdout.strip()


def ssh_mysql_query(sql):
    """Ejecuta una query simple en Hostinger via SSH."""
    cmd = f"{SSH_BASE} \"{MYSQL_REMOTE} -N -e \\\"{sql}\\\"\""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def extraer_campo(data, campo):
    pattern = rf'(?:^|\n){campo}(?:;[^:\n]*)?:([^\n]*)'
    m = re.search(pattern, data)
    return m.group(1).strip() if m else None


def extraer_parent_uid(data):
    m = re.search(r'RELATED-TO;RELTYPE=PARENT:([^\n]+)', data)
    return m.group(1).strip() if m else None


def extraer_categories(data):
    m = re.search(r'CATEGORIES:([^\n]+)', data)
    return m.group(1).strip() if m else ''


def parsear_fecha(valor):
    if not valor:
        return None
    m = re.match(r'(\d{4})(\d{2})(\d{2})', valor.strip())
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return None


def parsear_datetime(valor):
    if not valor:
        return None
    valor = valor.strip().rstrip('Z')
    m = re.match(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', valor)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}'
    return parsear_fecha(valor)


def determinar_responsable(categories):
    if re.search(r'\bJen\b', categories, re.IGNORECASE):
        return EMAIL_JEN
    return EMAIL_SANTI


def escapar_sql(valor):
    if valor is None:
        return 'NULL'
    valor = str(valor).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{valor}'"


def main():
    print("=" * 60)
    print("IMPORTACIÓN NEXTCLOUD → SISTEMA GESTIÓN OS")
    print("=" * 60)

    # 1. Leer tareas de Nextcloud (local, rápido)
    print("\n[1] Leyendo tareas de Nextcloud...")
    conn = mysql.connector.connect(**LOCAL_DB)
    cur = conn.cursor()
    placeholders = ', '.join(['%s'] * len(CALENDARIOS))
    cur.execute(f"""
        SELECT c.displayname, o.calendardata
        FROM oc_calendars c
        JOIN oc_calendarobjects o ON o.calendarid = c.id
        WHERE c.displayname IN ({placeholders})
    """, list(CALENDARIOS.keys()))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    print(f"    {len(rows)} registros leídos.")

    # 2. Parsear todas las tareas
    print("\n[2] Parseando tareas...")
    tareas = []
    for displayname, calendardata in rows:
        data = calendardata if isinstance(calendardata, str) else calendardata.decode('utf-8')
        data = data.replace('\\n', '\n').replace('\r\n', '\n').replace('\r', '\n')

        uid = extraer_campo(data, 'UID')
        summary = extraer_campo(data, 'SUMMARY')
        if not summary:
            continue

        status_ical = extraer_campo(data, 'STATUS') or ''
        estado = 'Completada' if status_ical == 'COMPLETED' else 'Pendiente'

        due = extraer_campo(data, 'DUE')
        dtstart = extraer_campo(data, 'DTSTART')
        fecha_limite = parsear_fecha(due) or parsear_fecha(dtstart)

        created = extraer_campo(data, 'CREATED')
        fecha_creacion = parsear_datetime(created)

        completed_dt = extraer_campo(data, 'COMPLETED')
        fecha_fin_real = parsear_datetime(completed_dt)

        description = extraer_campo(data, 'DESCRIPTION')
        if description and 'Default Tasks.org' in description:
            description = None

        parent_uid = extraer_parent_uid(data)
        categories = extraer_categories(data)
        responsable = determinar_responsable(categories)
        categoria_id = CALENDARIOS.get(displayname, 12)

        tareas.append({
            'uid': uid,
            'titulo': summary,
            'descripcion': description,
            'estado': estado,
            'categoria_id': categoria_id,
            'calendario': displayname,
            'responsable': responsable,
            'fecha_limite': fecha_limite,
            'fecha_creacion': fecha_creacion,
            'fecha_fin_real': fecha_fin_real,
            'parent_uid': parent_uid,
        })

    principales = [t for t in tareas if not t['parent_uid']]
    subtareas = [t for t in tareas if t['parent_uid']]
    print(f"    {len(principales)} principales + {len(subtareas)} subtareas = {len(tareas)} total")

    # 3. Generar SQL completo en archivo temporal
    print("\n[3] Generando archivo SQL...")

    # Necesitamos IDs predecibles para parent_id de subtareas.
    # Estrategia: usar variables MySQL para capturar IDs.
    # Como AUTO_INCREMENT empieza en 1 y van secuenciales,
    # podemos predecir: primera principal = 1, segunda = 2, etc.
    # Luego subtareas empiezan desde len(principales) + 1.

    # Mapeo uid → id_secuencial (principales primero)
    uid_to_seq = {}
    for i, t in enumerate(principales, start=1):
        uid_to_seq[t['uid']] = i

    sql_lines = []
    sql_lines.append("-- Importación Nextcloud → g_tareas")
    sql_lines.append("DELETE FROM g_tareas;")
    sql_lines.append("ALTER TABLE g_tareas AUTO_INCREMENT = 1;")
    sql_lines.append("")

    # Insertar principales (sin parent_id)
    sql_lines.append("-- Tareas principales")
    for t in principales:
        sql_lines.append(
            f"INSERT INTO g_tareas "
            f"(empresa, titulo, descripcion, categoria_id, estado, responsable, "
            f"fecha_limite, fecha_creacion, fecha_fin_real, usuario_creador) VALUES ("
            f"{escapar_sql(EMPRESA)}, {escapar_sql(t['titulo'])}, {escapar_sql(t['descripcion'])}, "
            f"{t['categoria_id']}, {escapar_sql(t['estado'])}, {escapar_sql(t['responsable'])}, "
            f"{escapar_sql(t['fecha_limite'])}, {escapar_sql(t['fecha_creacion'])}, "
            f"{escapar_sql(t['fecha_fin_real'])}, {escapar_sql(t['responsable'])});"
        )

    # Insertar subtareas (con parent_id basado en el secuencial del padre)
    sql_lines.append("")
    sql_lines.append("-- Subtareas")
    huerfanas = 0
    for t in subtareas:
        parent_seq = uid_to_seq.get(t['parent_uid'])
        if parent_seq:
            parent_id_sql = str(parent_seq)
        else:
            parent_id_sql = 'NULL'
            huerfanas += 1

        sql_lines.append(
            f"INSERT INTO g_tareas "
            f"(parent_id, empresa, titulo, descripcion, categoria_id, estado, responsable, "
            f"fecha_limite, fecha_creacion, fecha_fin_real, usuario_creador) VALUES ("
            f"{parent_id_sql}, {escapar_sql(EMPRESA)}, {escapar_sql(t['titulo'])}, "
            f"{escapar_sql(t['descripcion'])}, {t['categoria_id']}, {escapar_sql(t['estado'])}, "
            f"{escapar_sql(t['responsable'])}, {escapar_sql(t['fecha_limite'])}, "
            f"{escapar_sql(t['fecha_creacion'])}, {escapar_sql(t['fecha_fin_real'])}, "
            f"{escapar_sql(t['responsable'])});"
        )

    sql_content = '\n'.join(sql_lines)

    # Escribir archivo temporal
    tmp_path = '/tmp/importar_tareas_nc.sql'
    with open(tmp_path, 'w') as f:
        f.write(sql_content)
    print(f"    Archivo generado: {tmp_path} ({len(sql_lines)} líneas)")
    if huerfanas:
        print(f"    {huerfanas} subtareas huérfanas (padre no encontrado, insertadas sin parent_id)")

    # 4. Enviar a Hostinger en UNA sola conexión SSH
    print("\n[4] Enviando SQL a Hostinger (una sola conexión SSH)...")
    result = ssh_mysql_file(tmp_path)
    if result:
        print(f"    Respuesta: {result}")
    print("    Envío completado.")

    # 5. Verificación y resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total parseadas: {len(tareas)} ({len(principales)} principales + {len(subtareas)} subtareas)")

    print("\nPor responsable:")
    conteo_resp = {}
    for t in tareas:
        r = 'Jen' if t['responsable'] == EMAIL_JEN else 'Santi'
        conteo_resp[r] = conteo_resp.get(r, 0) + 1
    for r, c in sorted(conteo_resp.items()):
        print(f"  {r}: {c}")

    print("\nPor categoría:")
    conteo_cat = {}
    for t in tareas:
        conteo_cat[t['calendario']] = conteo_cat.get(t['calendario'], 0) + 1
    for cat, c in sorted(conteo_cat.items()):
        print(f"  {cat}: {c}")

    # Verificar en Hostinger
    print("\nVerificación en Hostinger:")
    total_h = ssh_mysql_query("SELECT COUNT(*) FROM g_tareas")
    print(f"  Total en g_tareas: {total_h}")
    estados_h = ssh_mysql_query("SELECT CONCAT(estado, \\': \\', COUNT(*)) FROM g_tareas GROUP BY estado")
    for linea in estados_h.split('\n'):
        if linea.strip():
            print(f"  {linea.strip()}")

    # Limpiar
    os.remove(tmp_path)
    print("\nImportación finalizada.")


if __name__ == '__main__':
    main()
