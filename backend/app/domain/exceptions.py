class DomainError(Exception):
    """Erro genérico da camada de domínio."""


class ValidationError(DomainError):
    """Dados inválidos para a operação solicitada."""


class SchedulingError(DomainError):
    """Regras de agendamento foram violadas."""
