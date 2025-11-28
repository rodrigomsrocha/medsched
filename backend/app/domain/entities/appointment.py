from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from ..enums import StatusConsulta
from ..exceptions import ValidationError, SchedulingError


@dataclass
class Consulta:
    _id: str
    _paciente_id: str
    _medico_id: str
    _inicio: datetime
    _fim: datetime
    _status: StatusConsulta = StatusConsulta.AGENDADA
    _observacoes: Optional[str] = None
    _criada_em: datetime = field(default_factory=datetime.utcnow)
    _atualizada_em: datetime = field(default_factory=datetime.utcnow)

    @property
    def id(self) -> str:
        return self._id

    @property
    def paciente_id(self) -> str:
        return self._paciente_id

    @property
    def medico_id(self) -> str:
        return self._medico_id

    @property
    def inicio(self) -> datetime:
        return self._inicio

    @property
    def fim(self) -> datetime:
        return self._fim

    @property
    def status(self) -> StatusConsulta:
        return self._status

    @property
    def observacoes(self) -> Optional[str]:
        return self._observacoes

    def anotar(self, texto: str) -> None:
        self._observacoes = (texto or "").strip() or None
        self._atualizada_em = datetime.utcnow()

    def confirmar(self, agora: Optional[datetime] = None) -> None:
        if self._status != StatusConsulta.AGENDADA:
            raise SchedulingError("Apenas consultas agendadas podem ser confirmadas.")
        self._status = StatusConsulta.CONFIRMADA
        self._atualizada_em = (agora or datetime.utcnow())

    def cancelar(self, agora: Optional[datetime] = None) -> None:
        if self._status in (StatusConsulta.CANCELADA, StatusConsulta.REALIZADA):
            raise SchedulingError("Consulta já finalizada/cancelada.")
        if self._inicio <= (agora or datetime.utcnow()):
            raise SchedulingError("Não é possível cancelar consultas no passado.")
        self._status = StatusConsulta.CANCELADA
        self._atualizada_em = (agora or datetime.utcnow())

    def remarcar(self, novo_inicio, novo_fim) -> None:
        if novo_inicio >= novo_fim:
            raise ValidationError("Intervalo de remarcação inválido.")
        self._atualizada_em = datetime.utcnow()

    @staticmethod
    def nova(paciente_id: str, medico_id: str, inicio: datetime, fim: datetime) -> "Consulta":
        if inicio >= fim:
            raise ValidationError("Intervalo de consulta inválido.")
        return Consulta(
            _id=str(uuid.uuid4()),
            _paciente_id=paciente_id,
            _medico_id=medico_id,
            _inicio=inicio,
            _fim=fim,
        )
