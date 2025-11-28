"""Camada de domínio do sistema de agendamento médico."""

from .enums import Perfil, StatusConsulta
from .entities import Usuario, Paciente, Medico, Administrador, Agenda, SlotAgenda, Consulta
from .services import AgendamentoService
from .exceptions import DomainError, SchedulingError, ValidationError

__all__ = [
    "Perfil",
    "StatusConsulta",
    "Usuario",
    "Paciente",
    "Medico",
    "Administrador",
    "Agenda",
    "SlotAgenda",
    "Consulta",
    "AgendamentoService",
    "DomainError",
    "SchedulingError",
    "ValidationError",
]
