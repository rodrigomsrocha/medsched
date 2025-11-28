from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .domain import Perfil, StatusConsulta


class UsuarioBase(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = None


class PacienteCreate(UsuarioBase):
    senha: str = Field(default="1234")


class MedicoCreate(UsuarioBase):
    especialidades: Optional[List[str]] = Field(None, description="Lista de especializações")
    senha: str = Field(default="1234", description="Senha simples para login")


class UsuarioOut(UsuarioBase):
    id: str
    perfil: Perfil
    especialidades: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class SlotOut(BaseModel):
    inicio: datetime
    fim: datetime
    bloqueado: bool = False

    model_config = ConfigDict(from_attributes=True)


class AgendamentoRequest(BaseModel):
    paciente_id: str
    medico_id: str
    inicio: datetime
    fim: datetime


class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    token: str
    usuario: UsuarioOut


class RemarcarRequest(BaseModel):
    novo_inicio: datetime
    novo_fim: datetime


class ConsultaOut(BaseModel):
    id: str
    paciente_id: str
    paciente_nome: str
    medico_id: str
    medico_nome: str
    especialidade: Optional[str]
    especialidades: Optional[List[str]] = None
    inicio: datetime
    fim: datetime
    status: StatusConsulta
    observacoes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApiState(BaseModel):
    medicos: List[UsuarioOut]
    pacientes: List[UsuarioOut]
    slots: List[SlotOut]
    consultas: List[ConsultaOut]
