from enum import Enum


class Perfil(str, Enum):
    PACIENTE = "PACIENTE"
    MEDICO = "MEDICO"
    ADMIN = "ADMIN"


class StatusConsulta(str, Enum):
    AGENDADA = "AGENDADA"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    REALIZADA = "REALIZADA"
    REMARCADA = "REMARCADA"
