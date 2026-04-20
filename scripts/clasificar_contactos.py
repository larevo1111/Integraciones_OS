#!/usr/bin/env python3
"""
clasificar_contactos.py — Clasifica contactos en EspoCRM
5 tipos: Negocio amigo, Red de amigos, Cliente directo, Interno, Otro

Criterios:
1. Interno: NV-*, MUESTRAS, DESPERDICIO, CONSUMO INTERNO, DEGUSTACIONES, CONSUMIDOR FINAL, CLIENTE GENERAL, ORIGEN SILVESTRE, RED DE MIGOS OS, VENTAS A MIEMBROS
2. Red de amigos: su numero_identificacion coincide con un empleado de Effi (excluyendo internos)
3. Negocio amigo: tipo_persona Jurídica, O nombre tiene indicadores de negocio
4. Cliente directo: todo lo demás (nombres de persona)
5. Otro: no encaja en ninguno (se asigna manualmente)

Uso: python3 scripts/clasificar_contactos.py [--dry-run]
"""

import re
import sys
import mysql.connector

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from lib import cfg_local
DB_EFFI = dict(**cfg_local(), database='effi_data')
DB_ESPO = dict(**cfg_local(), database='espocrm')

# ─── Internos: registros ficticios, consumo interno, muestras, etc. ───────────
INTERNAL_KEYWORDS = [
    r'\bNV[\s-]',           # NV-CONSUMO, NV - Daños, etc.
    r'\bCONSUMO INTERNO\b',
    r'\bDEGUSTACIONES?\b',
    r'\bDESPERDICIO\b',
    r'\bMUESTRAS?\s*VENDEDORES?\b',
    r'\bCONSUMIDOR FINAL\b',
    r'\bCLIENTE GENERAL\b',
    r'\bORIGEN SILVESTRE\b',
    r'\bRED DE MIGOS\b',
    r'\bVENTAS A MIEMBROS\b',
    r'\bMUESTRA VENDEDORES\b',
    r'\bCONSUMO DESARROLLO\b',
]

# IDs específicos que son internos (cuentas ficticias)
INTERNAL_IDS = {
    '000909',           # RED DE MIGOS OS
    '89898989',         # VENTAS A MIEMBROS OS
    '969696969',        # CONSUMO INTERNO OS
    '454564564',        # MUESTRA VENDEDORES OS
    '222222222222',     # CONSUMIDOR FINAL
    '999999999999',     # CONSUMIDOR FINAL GENERAL
    '12313231',         # DESPERDICIO
    '4342341234',       # MUESTRAS VENDEDORES
    '7777777777',       # NV-CONSUMO INTERNO
    '000001',           # NV-Consumo desarrollo de productos
    '666666696666',     # NV-DEGUSTACIONES
    '0000000000001010101', # NV - Daños y Averias
    '9999999',          # ORIGEN SILVESTRE / Pablo Duque
    '901753603',        # ORIGEN SILVESTRE
    '90173460334',      # CLIENTE GENERAL A
    '11257367334',      # CLIENTE GENERAL B
}

# ─── Palabras clave que indican un negocio ─────────────────────────────────────
BUSINESS_KEYWORDS = [
    r'\bS\.?A\.?S\b', r'\bLTDA\b', r'\bS\.?A\.\b', r'\bLLC\b', r'\bINC\b',
    r'\bTIENDA\b', r'\bALMACEN\b', r'\bSUPERMERCADO\b', r'\bMINIMERCADO\b',
    r'\bDROGUERIA\b', r'\bFARMACIA\b', r'\bRESTAURANT\w*\b', r'\bCAFE\b', r'\bCAFÉ\b',
    r'\bMERCADO(?!\s*LI)\b',  # MERCADO pero NO MercadoLibre
    r'\bPLAZA\b', r'\bFUNDACION\b', r'\bCORPORACION\b',
    r'\bDISTRIBUI?DORA?\b', r'\bCOMERCIALIZADORA\b', r'\bINVERSIONES\b',
    r'\bGRUPO\b', r'\bAUTOSERVICIO\b', r'\bGRANERO\b', r'\bLABORAT\b',
    r'\bSPA\b', r'\bHOTEL\b', r'\bPANADERIA\b', r'\bINSTITUTO\b',
    r'\bSTORE\b', r'\bSTUDIO\b', r'\bMARKET\b', r'\bCLUB\b',
    r'\bCHOCOLATERIA\b', r'\bESTADERO\b', r'\bCARNICERIA\b',
    r'\bFERIA\b', r'\bAGROPECUARIA\b', r'\bCONSULTORIA\b',
    r'\bPIZZERIA\b', r'\bARTESANI\b', r'\bCOWORKING\b',
    r'\bFITNES\b', r'\bVITAMIN\b', r'\bNATURALISTA\b', r'\bMULTINATURISTA\b',
    r'\bSOLOENVASES\b', r'\bNACIONAL DE\b', r'\bUNICOR\b',
    r'\bALICO\b', r'\bDISCORDOBA\b', r'\bBREMEN\b',
    r'\bFINCA\b', r'\bFRESAS\b', r'\bREFUGIO\b',
    r'\bPRODUCTOS NATURALES\b', r'\bARBOL DE CACAO\b',
    r'\bSERES SANOS\b', r'\bARTE NATIVA\b', r'\bAGROMA\b',
    r'\bNOTARI\w*\b', r'\bLITOGRAFIA\b', r'\bIMPERIO\b',
    r'\bCONTABILIDAD\b', r'\bVARIEDADES\b',
]

# Negocios conocidos por nombre (sin keyword genérico)
KNOWN_BUSINESSES = {
    'GALILEA', 'TITANIA', 'MANDALAIRE', 'TANQUEO', 'CANELA CAFE',
    'SOUL', 'KAKAW', 'INKAMPO', 'ECOSANOS', 'CENTRO GREEN',
    'ALTA MAGIA', 'BENDITO', 'CARPE DIEM', 'LA KERUNGA',
    'LA TULPA', 'LA SAMARIA', 'LA MONTAÑITA', 'LA TIERRITA',
    'RENACER', 'APICA', 'CHOCOFRUTS', 'ARTESERVICIOS',
    'MACADAMIAS', 'PAZIONART', 'CASI NEW', 'PRINCIPE CONEJO',
    'BE GOOD', 'CUMORAH', 'LOS GIRASOLES', 'DONDE EL TIO',
    'RAICES', 'NUESTRO', 'PSO STORE', 'SANTO RINCON',
    'EDEN GARDEN', 'YOGUIANDO', 'ANIDARTE', 'BAKAU',
    'DOCE GRACIAS', 'MADRE TIERRA', 'JAN ARTESANO',
    'MACARENA', 'EL BARATON', 'MICROPAPEL', 'PLASTIAMERICA',
    'ADN ALGO DE NOSOTROS', 'LA COSONA', 'LA DESPENSA',
    'CHOCOLATE DE LA ABUELA', 'FRUTOS Y SEMILLAS',
    'EKO MARKET', 'CASA AMARELA', 'BOCANADA',
    'HORS CATEGORIE', 'PERSEVERANCIA', 'PENJAMO',
    'TIENDA DE NONA', 'SAZON EN EL PUNTO',
    'MERCADO ALTERNATIVO', 'MERCADO LOCAL',
    'LA QUESERIA', 'DIATRIBUIDORA',
    'EL RECREO', 'COSECHAS SANTA ELENA',
    'PATIO SANTA ELENA', 'SANTO RINCON',
    'TRADICIONAL',   # Marta Calvo Restaurante el tradicional
    'EBANISTERIA',
    'CARPINTERIA',
}

# ─── IDs específicos que son persona pero su nombre engaña ─────────────────────
# (Falsos positivos: persona con "Mercado libre" o guion por otro motivo)
FORCE_CLIENTE_DIRECTO = {
    '22658854',     # Antonella Barrios Mercado libre — persona
    '51754849',     # Rosalba Valencia - Mercadolibre 2024 — persona
    '1110444211',   # Camilo Gómez Ocampo - katherin Gomez — persona
    '21523349',     # Beatriz Agudelo - Cathy Vieira — persona
    '3104503547',   # Esneyder Roble Motos - Reginaldo — persona
    '43509389',     # Estela Montes empleada el patio Santa Elena — persona
}

# IDs que son negocios pero el script no los detecta automáticamente
FORCE_NEGOCIO = {
    '1128456609',   # VITAMINFIT - Xiomara Ocampo Marin
    '99990068',     # Luz Elena la sazón en el punto exacto — restaurante
    '3145906045',   # Mauricio Tortas Parque San Carlos — negocio
}


def is_internal(name, num_id):
    """Detecta registros internos/ficticios."""
    if num_id in INTERNAL_IDS:
        return True
    upper = (name or '').upper().strip()
    for kw in INTERNAL_KEYWORDS:
        if re.search(kw, upper):
            return True
    return False


def is_business_name(name):
    """Detecta si un nombre corresponde a un negocio."""
    if not name:
        return False
    upper = name.upper().strip()

    # Keywords directos
    for kw in BUSINESS_KEYWORDS:
        if re.search(kw, upper):
            return True

    # Negocios conocidos
    for biz in KNOWN_BUSINESSES:
        if biz in upper:
            return True

    # Patrón "NEGOCIO - Persona" (si la parte antes del guion tiene >=2 palabras en mayúscula)
    if ' - ' in name:
        parte1 = name.split(' - ')[0].strip()
        words = parte1.split()
        if len(words) >= 2:
            return True

    # Patrón "NOMBRE / Persona"
    if ' / ' in name:
        return True

    return False


def main():
    dry_run = '--dry-run' in sys.argv

    conn_effi = mysql.connector.connect(**DB_EFFI)
    conn_espo = mysql.connector.connect(**DB_ESPO, autocommit=False)
    cur_effi = conn_effi.cursor(dictionary=True, buffered=True)
    cur_espo = conn_espo.cursor(dictionary=True, buffered=True)

    # 1. Cargar IDs de empleados
    cur_effi.execute("SELECT numero_de_identificacion FROM zeffi_empleados WHERE vigencia = 'Vigente'")
    employee_ids = {row['numero_de_identificacion'] for row in cur_effi.fetchall()}
    print(f"Empleados vigentes: {len(employee_ids)}")

    # 2. Cargar todos los contactos de EspoCRM
    cur_espo.execute("""
        SELECT id, numero_identificacion, first_name, last_name, tipo_persona, tipo_cliente, fuente
        FROM contact WHERE deleted = 0
    """)
    contacts = cur_espo.fetchall()
    print(f"Contactos en EspoCRM: {len(contacts)}")

    # 3. Clasificar
    results = {
        'Interno': [],
        'Red de amigos': [],
        'Negocio amigo': [],
        'Cliente directo': [],
        'Otro': [],
    }

    for c in contacts:
        num_id = c['numero_identificacion'] or ''
        nombre = f"{c['first_name'] or ''} {c['last_name'] or ''}".strip()
        tipo_persona = c['tipo_persona'] or ''

        # Prioridad 1: Internos (cuentas ficticias)
        if is_internal(nombre, num_id):
            tipo = 'Interno'
        # Prioridad 2: Forzar negocio (override manual)
        elif num_id in FORCE_NEGOCIO:
            tipo = 'Negocio amigo'
        # Prioridad 3: Forzar como cliente directo (falsos positivos)
        elif num_id in FORCE_CLIENTE_DIRECTO:
            tipo = 'Cliente directo'
        # Prioridad 4: Empleados = Red de amigos
        elif num_id in employee_ids:
            tipo = 'Red de amigos'
        # Prioridad 5: Negocios (automático)
        elif tipo_persona == 'Jurídica (moral)' or is_business_name(nombre):
            tipo = 'Negocio amigo'
        # Prioridad 6: Cliente directo
        else:
            tipo = 'Cliente directo'

        results[tipo].append((c['id'], num_id, nombre, c['tipo_cliente']))

    # 4. Mostrar resumen
    print(f"\n{'='*70}")
    print(f"CLASIFICACIÓN PROPUESTA")
    print(f"{'='*70}")

    for tipo in ['Interno', 'Red de amigos', 'Negocio amigo', 'Cliente directo', 'Otro']:
        items = results[tipo]
        print(f"\n--- {tipo} ({len(items)}) ---")
        for _, num_id, nombre, old_tipo in sorted(items, key=lambda x: x[2]):
            print(f"  {num_id:<20} {nombre}")

    # 5. Aplicar si no es dry-run
    if not dry_run:
        print(f"\n{'='*70}")
        print("APLICANDO CAMBIOS...")
        cur_update = conn_espo.cursor()
        total = 0
        for tipo, items in results.items():
            for contact_id, _, _, _ in items:
                cur_update.execute(
                    "UPDATE contact SET tipo_cliente = %s WHERE id = %s",
                    (tipo, contact_id)
                )
                total += 1
        # Poner calificacion B a todos los Negocio amigo
        for contact_id, _, _, _ in results['Negocio amigo']:
            cur_update.execute(
                "UPDATE contact SET calificacion_negocio_amigo = 'B' WHERE id = %s",
                (contact_id,)
            )
        conn_espo.commit()
        cur_update.close()
        print(f"✅ {total} contactos clasificados:")
        for tipo in ['Interno', 'Red de amigos', 'Negocio amigo', 'Cliente directo', 'Otro']:
            extra = " (todos calificación B)" if tipo == 'Negocio amigo' else ""
            print(f"   {tipo}: {len(results[tipo])}{extra}")
    else:
        print(f"\n[DRY RUN — no se aplicaron cambios]")

    cur_effi.close()
    cur_espo.close()
    conn_effi.close()
    conn_espo.close()


if __name__ == '__main__':
    main()
