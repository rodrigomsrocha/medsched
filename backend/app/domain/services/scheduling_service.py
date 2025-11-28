from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..entities import Agenda, Consulta, Medico, Paciente, SlotAgenda
from ..enums import StatusConsulta
from ..exceptions import SchedulingError, ValidationError


@dataclass
class AgendamentoService:
    """Regras de negócio de agendamentos (coleções em memória)."""

    agendas: Dict[str, Agenda] = field(default_factory=dict)
    consultas: Dict[str, Consulta] = field(default_factory=dict)

    def criar_agenda_se_nao_existir(self, medico: Medico) -> Agenda:
        if medico.id not in self.agendas:
            self.agendas[medico.id] = Agenda(medico_id=medico.id)
        return self.agendas[medico.id]

    def disponibilizar_slot(self, medico: Medico, inicio: datetime, fim: datetime) -> None:
        self.criar_agenda_se_nao_existir(medico).adicionar_slot(inicio, fim)

    def bloquear_horario(self, medico: Medico, inicio: datetime, fim: datetime) -> None:
        self.criar_agenda_se_nao_existir(medico).bloquear(inicio, fim)

    def desbloquear_horario(self, medico: Medico, inicio: datetime, fim: datetime) -> None:
        self.criar_agenda_se_nao_existir(medico).desbloquear(inicio, fim)

    def slots_disponiveis(self, medico: Medico) -> List[SlotAgenda]:
        # Slots permanecem livres enquanto não há confirmação; apenas consultas confirmadas bloqueiam o slot.
        ativos = [
            c
            for c in self.consultas.values()
            if c.medico_id == medico.id and c.status == StatusConsulta.CONFIRMADA
        ]
        livres = []
        for s in self.criar_agenda_se_nao_existir(medico).slots():
            if s.bloqueado:
                continue
            if any(not (s.fim <= c.inicio or c.fim <= s.inicio) for c in ativos):
                continue
            livres.append(s)
        return livres

    def agendar(self, paciente: Paciente, medico: Medico, inicio: datetime, fim: datetime) -> Consulta:
        agenda = self.criar_agenda_se_nao_existir(medico)
        slot = agenda.encontrar_slot_disponivel(inicio, fim)
        if not slot:
            raise SchedulingError("Horário indisponível na agenda do médico.")

        for c in self.consultas.values():
            if c.medico_id == medico.id and c.status == StatusConsulta.CONFIRMADA:
                colide = not (fim <= c.inicio or c.fim <= inicio)
                if colide:
                    raise SchedulingError("Há uma consulta confirmada que colide com este horário.")

        # Paciente não pode ter sobreposição de consultas (mesmo que com outro médico)
        for c in self.consultas.values():
            if c.paciente_id == paciente.id and c.status in (StatusConsulta.AGENDADA, StatusConsulta.CONFIRMADA):
                if not (fim <= c.inicio or c.fim <= inicio):
                    raise SchedulingError("Você já possui uma consulta neste horário.")

        consulta = Consulta.nova(paciente.id, medico.id, inicio, fim)
        self.consultas[consulta.id] = consulta
        return consulta

    def cancelar(self, consulta_id: str, agora: Optional[datetime] = None) -> Consulta:
        consulta = self._obter(consulta_id)
        consulta.cancelar(agora=agora)
        return consulta

    def confirmar(self, consulta_id: str) -> Consulta:
        consulta = self._obter(consulta_id)
        consulta.confirmar()
        # Cancela automaticamente outras consultas agendadas no mesmo intervalo para o mesmo médico
        for other in self.consultas.values():
            if other.id == consulta.id:
                continue
            if other.medico_id == consulta.medico_id and other.status == StatusConsulta.AGENDADA:
                overlap = not (consulta.fim <= other.inicio or other.fim <= consulta.inicio)
                if overlap:
                    try:
                        other.cancelar()
                    except Exception:
                        other._status = StatusConsulta.CANCELADA
        return consulta

    def remarcar(
        self, consulta_id: str, novo_inicio: datetime, novo_fim: datetime, confirmar_nova: bool = False
    ) -> Consulta:
        """
        Cancela a consulta atual e cria outra.
        - Se confirmar_nova=True (médico remarcando), a nova já nasce CONFIRMADA e cancela agendadas que colidam.
        - Se confirmar_nova=False (paciente remarcando), a nova fica AGENDADA aguardando confirmação do médico.
        """
        antiga = self._obter(consulta_id)
        paciente_id, medico_id = antiga.paciente_id, antiga.medico_id

        # Verifica conflitos para paciente (exceto a própria consulta)
        for c in self.consultas.values():
            if c.id == consulta_id:
                continue
            if c.paciente_id == paciente_id and c.status in (StatusConsulta.AGENDADA, StatusConsulta.CONFIRMADA):
                overlap = not (novo_fim <= c.inicio or c.fim <= novo_inicio)
                if overlap:
                    raise SchedulingError("Paciente possui outra consulta neste horário.")

        # Verifica conflitos confirmados para o médico (exceto a própria consulta)
        for c in self.consultas.values():
            if c.id == consulta_id:
                continue
            if c.medico_id == medico_id and c.status == StatusConsulta.CONFIRMADA:
                overlap = not (novo_fim <= c.inicio or c.fim <= novo_inicio)
                if overlap:
                    raise SchedulingError("Médico já possui consulta confirmada nesse horário.")

        try:
            antiga.cancelar()
        except Exception:
            antiga._status = StatusConsulta.CANCELADA
        fake_pac = type("FakePac", (), {"id": paciente_id})()
        fake_med = type("FakeMed", (), {"id": medico_id})()
        nova = self.agendar(fake_pac, fake_med, novo_inicio, novo_fim)
        if confirmar_nova:
            nova.confirmar()
            for other in list(self.consultas.values()):
                if other.id == nova.id:
                    continue
                if other.medico_id == nova.medico_id and other.status == StatusConsulta.AGENDADA:
                    overlap = not (nova.fim <= other.inicio or other.fim <= nova.inicio)
                    if overlap:
                        try:
                            other.cancelar()
                        except Exception:
                            other._status = StatusConsulta.CANCELADA
        return nova

    def historico_do_paciente(self, paciente: Paciente) -> List[Consulta]:
        return [c for c in self.consultas.values() if c.paciente_id == paciente.id]

    def consultas_do_medico(self, medico: Medico) -> List[Consulta]:
        return [c for c in self.consultas.values() if c.medico_id == medico.id]

    def _obter(self, consulta_id: str) -> Consulta:
        if consulta_id not in self.consultas:
            raise ValidationError("Consulta não encontrada.")
        return self.consultas[consulta_id]
