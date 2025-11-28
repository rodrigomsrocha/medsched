from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import uuid

from ..enums import Perfil
from ..exceptions import ValidationError


@dataclass
class Usuario:
    _id: str
    _nome: str
    _email: str
    _perfil: Perfil
    _telefone: Optional[str] = None
    _senha: Optional[str] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, novo: str) -> None:
        if not novo or len(novo.strip()) < 3:
            raise ValidationError("Nome inválido.")
        self._nome = novo.strip()

    @property
    def email(self) -> str:
        return self._email

    @property
    def perfil(self) -> Perfil:
        return self._perfil

    @property
    def telefone(self) -> Optional[str]:
        return self._telefone

    @telefone.setter
    def telefone(self, novo: Optional[str]) -> None:
        self._telefone = (novo or "").strip() or None

    def atualizar_senha(self, senha: str) -> None:
        if not senha or len(senha) < 4:
            raise ValidationError("Senha inválida.")
        self._senha = senha

    def verificar_senha(self, senha: str) -> bool:
        return bool(self._senha) and self._senha == senha


@dataclass
class Paciente(Usuario):
    cpf_hash: Optional[str] = None

    @staticmethod
    def novo(nome: str, email: str, telefone: Optional[str] = None, senha: str = "1234") -> "Paciente":
        return Paciente(
            _id=str(uuid.uuid4()),
            _nome=nome.strip(),
            _email=email.lower().strip(),
            _perfil=Perfil.PACIENTE,
            _telefone=(telefone or "").strip() or None,
            _senha=senha,
        )


@dataclass
class Medico(Usuario):
    especialidades: Optional[list[str]] = None

    @staticmethod
    def novo(
        nome: str,
        email: str,
        especialidade: Optional[str] = None,
        especialidades: Optional[list[str]] = None,
        telefone: Optional[str] = None,
        senha: str = "1234",
    ) -> "Medico":
        lista = especialidades or ([especialidade] if especialidade else [])
        return Medico(
            _id=str(uuid.uuid4()),
            _nome=nome.strip(),
            _email=email.lower().strip(),
            _perfil=Perfil.MEDICO,
            _telefone=(telefone or "").strip() or None,
            especialidades=[e.strip() for e in lista if e and e.strip()],
            _senha=senha,
        )


@dataclass
class Administrador(Usuario):
    @staticmethod
    def novo(nome: str, email: str, telefone: Optional[str] = None, senha: str = "admin") -> "Administrador":
        return Administrador(
            _id=str(uuid.uuid4()),
            _nome=nome.strip(),
            _email=email.lower().strip(),
            _perfil=Perfil.ADMIN,
            _telefone=(telefone or "").strip() or None,
            _senha=senha,
        )
