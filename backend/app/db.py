import json
import os
import sqlite3
from typing import Iterable, List, Optional

DB_PATH = os.getenv("MEDSCHED_DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))


class Database:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        self._ensure()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _ensure(self) -> None:
        conn = self._connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                telefone TEXT,
                perfil TEXT NOT NULL,
                especialidades TEXT,
                senha TEXT
            );
            """
        )
        conn.commit()
        conn.close()

    def salvar_usuario(
        self,
        *,
        id: str,
        nome: str,
        email: str,
        telefone: Optional[str],
        perfil: str,
        especialidades: Optional[List[str]],
        senha: Optional[str],
    ) -> None:
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO usuarios (id, nome, email, telefone, perfil, especialidades, senha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                nome=excluded.nome,
                telefone=excluded.telefone,
                perfil=excluded.perfil,
                especialidades=excluded.especialidades,
                senha=excluded.senha;
            """,
            (
                id,
                nome,
                email.lower().strip(),
                telefone,
                perfil,
                json.dumps(especialidades or []),
                senha,
            ),
        )
        conn.commit()
        conn.close()

    def carregar_por_perfil(self, perfil: str) -> Iterable[sqlite3.Row]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM usuarios WHERE perfil = ?", (perfil,))
        rows = cur.fetchall()
        conn.close()
        return rows


db = Database()
