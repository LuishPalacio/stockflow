import os
import time

import psycopg2
import psycopg2.extras

DATA_DIR = os.environ.get("DATA_DIR") or os.path.dirname(os.path.abspath(__file__))

EQUIPAMENTO_COLUMNS = [
    "codigo", "tipo", "fabricante", "nome", "modelo", "valor", "estado",
    "funcionario", "data_entrega", "setor", "sn", "pn", "so", "processador", "ram",
    "armazenamento", "carregador", "sn_carregador", "mac_rede", "mac_wifi", "imei1", "imei2",
    "resolucao", "proporcao", "taxa_atualizacao", "tipo_painel", "fonte", "saidas", "obs",
]

# Expressão usada como valor padrão de data/hora, no formato "YYYY-MM-DD HH:MM:SS".
_TIMESTAMP_DEFAULT = "to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')"


class DB:
    """Envolve a conexão psycopg2 com uma API simples (db.execute(...), db.commit(),
    db.close()), parecida com sqlite3.Connection."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        # psycopg2 só faz a substituição de %s quando params não é None - se passarmos
        # () por padrão, qualquer "%" literal na consulta (ex: LIKE '...%') quebra
        # mesmo sem parâmetro nenhum. Com None, consultas sem parâmetro vão como estão.
        cur = self._conn.cursor()
        if params is None:
            cur.execute(sql)
        else:
            cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _senha_postgres():
    """Lê a senha de um arquivo secreto (Docker secrets) se disponível, senão
    cai para a variável de ambiente direta - assim funciona nos dois modos."""
    caminho = os.environ.get("POSTGRES_PASSWORD_FILE")
    if caminho and os.path.exists(caminho):
        with open(caminho, "r") as f:
            return f.read().strip()
    return os.environ.get("POSTGRES_PASSWORD", "")


def _connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "stockflow"),
        user=os.environ.get("POSTGRES_USER", "stockflow"),
        password=_senha_postgres(),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_db(retries=10, delay=1.5):
    """Conecta ao Postgres, tentando de novo por alguns segundos caso o banco
    ainda esteja subindo (comum logo depois que o container é criado)."""
    ultimo_erro = None
    for tentativa in range(retries):
        try:
            return DB(_connect())
        except psycopg2.OperationalError as erro:
            ultimo_erro = erro
            if tentativa < retries - 1:
                time.sleep(delay)
    raise ultimo_erro


def ensure_schema():
    db = get_db()

    db.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            nome TEXT,
            auth_provider TEXT NOT NULL DEFAULT 'local',
            is_admin INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT DEFAULT ({_TIMESTAMP_DEFAULT})
        )
    """)

    db.execute(f"""
        CREATE TABLE IF NOT EXISTS equipamento_historico (
            id SERIAL PRIMARY KEY,
            equipamento_id INTEGER NOT NULL,
            equipamento_label TEXT,
            acao TEXT NOT NULL,
            campo TEXT,
            valor_anterior TEXT,
            valor_novo TEXT,
            usuario TEXT,
            data_hora TEXT DEFAULT ({_TIMESTAMP_DEFAULT})
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_historico_equipamento ON equipamento_historico (equipamento_id)"
    )

    colunas_eq_sql = ",\n            ".join(
        f"{c} REAL" if c == "valor" else f"{c} TEXT" for c in EQUIPAMENTO_COLUMNS
    )
    db.execute(f"""
        CREATE TABLE IF NOT EXISTS equipamentos (
            id SERIAL PRIMARY KEY,
            {colunas_eq_sql}
        )
    """)

    db.commit()
    db.close()
