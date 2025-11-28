from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..exceptions import ValidationError


@dataclass(frozen=True)
class SlotAgenda:
    inicio: datetime
    fim: datetime
    bloqueado: bool = False

    def contem(self, instante: datetime) -> bool:
        return self.inicio <= instante < self.fim

    def sobrepoe(self, outro: "SlotAgenda") -> bool:
        return self.inicio < outro.fim and outro.inicio < self.fim


@dataclass
class Agenda:
    medico_id: str
    _slots: List[SlotAgenda] = field(default_factory=list)

    def slots(self) -> List[SlotAgenda]:
        return list(self._slots)

    def adicionar_slot(self, inicio: datetime, fim: datetime) -> None:
        self._validar_intervalo(inicio, fim)
        novo = SlotAgenda(inicio=inicio, fim=fim, bloqueado=False)
        for s in self._slots:
            if s.sobrepoe(novo):
                raise ValidationError("Novo slot se sobrepõe a um slot existente.")
        self._slots.append(novo)
        self._slots.sort(key=lambda s: s.inicio)

    def bloquear(self, inicio: datetime, fim: datetime) -> None:
        self._validar_intervalo(inicio, fim)
        self._slots.append(SlotAgenda(inicio, fim, bloqueado=True))
        self._slots.sort(key=lambda s: s.inicio)

    def desbloquear(self, inicio: datetime, fim: datetime) -> None:
        self._slots = [
            s
            for s in self._slots
            if not (s.inicio == inicio and s.fim == fim and s.bloqueado)
        ]

    def encontrar_slot_disponivel(self, inicio: datetime, fim: datetime) -> Optional[SlotAgenda]:
        alvo = SlotAgenda(inicio, fim, bloqueado=False)
        for s in self._slots:
            if s.sobrepoe(alvo) and not s.bloqueado:
                if s.inicio == inicio and s.fim == fim:
                    return s
        return None

    def _validar_intervalo(self, inicio: datetime, fim: datetime) -> None:
        if inicio >= fim:
            raise ValidationError("Intervalo inválido: início deve ser menor que fim.")
