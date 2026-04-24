"""
Tests de scripts/lib/db_conn.py — helper único de conexiones a BD (Python).

No abre conexiones reales ni tuneles SSH: valida funciones puras (readers de
config, detección de 'local vs remoto') y estructura de la API pública.

Ejecución: pytest tests/python/ (desde raíz del repo)
"""
import os
import sys
from pathlib import Path

# Permitir importar scripts/lib/ desde tests/python/
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'scripts'))

from lib import db_conn  # noqa: E402


class TestApiPublica:
    def test_timezone_es_string(self):
        assert isinstance(db_conn.TIMEZONE, str)
        assert db_conn.TIMEZONE.startswith(('-', '+'))

    def test_exporta_context_managers(self):
        assert callable(db_conn.local)
        assert callable(db_conn.remota)
        assert callable(db_conn.integracion)
        assert callable(db_conn.gestion)
        assert callable(db_conn.inventario)
        assert callable(db_conn.comunidad)

    def test_exporta_cfg_readers(self):
        assert callable(db_conn.cfg_local)
        assert callable(db_conn.cfg_remota_ssh)
        assert callable(db_conn.cfg_remota_db)
        assert callable(db_conn.cfg_inventario)

    def test_exporta_gestion_tuneles(self):
        assert callable(db_conn.abrir_tunel)
        assert callable(db_conn.cerrar_tuneles)


class TestCfgLocal:
    def test_retorna_dict_con_claves_esperadas(self):
        cfg = db_conn.cfg_local()
        assert set(cfg.keys()) == {'host', 'port', 'user', 'password'}

    def test_host_default_127_0_0_1_cuando_no_hay_env(self, monkeypatch):
        monkeypatch.delenv('DB_LOCAL_HOST', raising=False)
        cfg = db_conn.cfg_local()
        assert cfg['host'] == '127.0.0.1'

    def test_port_default_3306_cuando_no_hay_env(self, monkeypatch):
        monkeypatch.delenv('DB_LOCAL_PORT', raising=False)
        cfg = db_conn.cfg_local()
        assert cfg['port'] == 3306

    def test_lee_env_cuando_esta_seteado(self, monkeypatch):
        monkeypatch.setenv('DB_LOCAL_HOST', 'mi-host.ejemplo')
        monkeypatch.setenv('DB_LOCAL_PORT', '3307')
        monkeypatch.setenv('DB_LOCAL_USER', 'usuario_test')
        monkeypatch.setenv('DB_LOCAL_PASS', 'pass_test')
        cfg = db_conn.cfg_local()
        assert cfg['host'] == 'mi-host.ejemplo'
        assert cfg['port'] == 3307
        assert cfg['user'] == 'usuario_test'
        assert cfg['password'] == 'pass_test'


class TestCfgRemota:
    def test_cfg_remota_ssh_lee_prefijo_correcto(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'ssh.integ.ejemplo')
        monkeypatch.setenv('DB_INTEGRACION_SSH_PORT', '2222')
        monkeypatch.setenv('DB_INTEGRACION_SSH_USER', 'sshuser_integ')
        monkeypatch.setenv('DB_INTEGRACION_SSH_KEY', '/tmp/key_integ')
        cfg = db_conn.cfg_remota_ssh('INTEGRACION')
        assert cfg['host'] == 'ssh.integ.ejemplo'
        assert cfg['port'] == 2222
        assert cfg['user'] == 'sshuser_integ'
        assert cfg['key'] == '/tmp/key_integ'

    def test_cfg_remota_ssh_acepta_prefijo_lowercase(self, monkeypatch):
        monkeypatch.setenv('DB_GESTION_SSH_HOST', 'ssh.gestion.ejemplo')
        cfg = db_conn.cfg_remota_ssh('gestion')
        assert cfg['host'] == 'ssh.gestion.ejemplo'

    def test_cfg_remota_db_lee_prefijo_correcto(self, monkeypatch):
        monkeypatch.setenv('DB_GESTION_USER', 'ges_user')
        monkeypatch.setenv('DB_GESTION_PASS', 'ges_pass')
        monkeypatch.setenv('DB_GESTION_NAME', 'os_gestion')
        cfg = db_conn.cfg_remota_db('GESTION')
        assert cfg['user'] == 'ges_user'
        assert cfg['password'] == 'ges_pass'
        assert cfg['database'] == 'os_gestion'
        assert cfg['charset'] == 'utf8mb4'

    def test_cfg_remota_ssh_port_default_22(self, monkeypatch):
        monkeypatch.delenv('DB_COMUNIDAD_SSH_PORT', raising=False)
        cfg = db_conn.cfg_remota_ssh('COMUNIDAD')
        assert cfg['port'] == 22


class TestEsLocal:
    def test_detecta_localhost(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'localhost')
        assert db_conn._es_local('INTEGRACION') is True

    def test_detecta_127_0_0_1(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', '127.0.0.1')
        assert db_conn._es_local('INTEGRACION') is True

    def test_detecta_direct(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'direct')
        assert db_conn._es_local('INTEGRACION') is True

    def test_detecta_vacio(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', '')
        assert db_conn._es_local('INTEGRACION') is True

    def test_host_real_no_es_local(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'ssh.ejemplo.com')
        assert db_conn._es_local('INTEGRACION') is False

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'LOCALHOST')
        assert db_conn._es_local('INTEGRACION') is True


class TestAbrirTunel:
    def test_retorna_none_si_ssh_host_es_local(self, monkeypatch):
        """Cuando la BD 'remota' está en el mismo servidor (SSH_HOST=localhost),
        abrir_tunel debe retornar None — el caller conecta directo."""
        monkeypatch.setenv('DB_INTEGRACION_SSH_HOST', 'localhost')
        assert db_conn.abrir_tunel('INTEGRACION') is None
