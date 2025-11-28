from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid
import json

from .db import db
from .domain import Medico, Paciente, Administrador, AgendamentoService, Perfil
from .domain.exceptions import ValidationError


class MemoryStore:
    """Armazena dados em memória com persistência simples em SQLite para usuários."""

    def __init__(self) -> None:
        self.medicos: Dict[str, Medico] = {}
        self.pacientes: Dict[str, Paciente] = {}
        self.admins: Dict[str, Administrador] = {}
        self.servico = AgendamentoService()
        self.sessions: Dict[str, str] = {}
        # garante que o arquivo recém-criado (ou recriado) tenha esquema necessário
        db._ensure()
        self._seed()

    # --- usuários ---
    def adicionar_medico(self, medico: Medico) -> Medico:
        self.medicos[medico.id] = medico
        self.servico.criar_agenda_se_nao_existir(medico)
        db.salvar_usuario(
            id=medico.id,
            nome=medico.nome,
            email=medico.email,
            telefone=medico.telefone,
            perfil=medico.perfil.value,
            especialidades=medico.especialidades,
            senha=medico._senha,
        )
        return medico

    def adicionar_paciente(self, paciente: Paciente) -> Paciente:
        self.pacientes[paciente.id] = paciente
        db.salvar_usuario(
            id=paciente.id,
            nome=paciente.nome,
            email=paciente.email,
            telefone=paciente.telefone,
            perfil=paciente.perfil.value,
            especialidades=None,
            senha=paciente._senha,
        )
        return paciente

    def adicionar_admin(self, admin: Administrador) -> Administrador:
        self.admins[admin.id] = admin
        db.salvar_usuario(
            id=admin.id,
            nome=admin.nome,
            email=admin.email,
            telefone=admin.telefone,
            perfil=admin.perfil.value,
            especialidades=None,
            senha=admin._senha,
        )
        return admin

    def obter_medico(self, medico_id: str) -> Medico:
        if medico_id not in self.medicos:
            raise ValidationError("Médico não encontrado.")
        return self.medicos[medico_id]

    def obter_paciente(self, paciente_id: str) -> Paciente:
        if paciente_id not in self.pacientes:
            raise ValidationError("Paciente não encontrado.")
        return self.pacientes[paciente_id]

    def obter_admin(self, admin_id: str) -> Administrador:
        if admin_id not in self.admins:
            raise ValidationError("Administrador não encontrado.")
        return self.admins[admin_id]

    def autenticar(self, email: str, senha: str) -> Optional[str]:
        usuarios = list(self.admins.values()) + list(self.medicos.values()) + list(self.pacientes.values())
        for u in usuarios:
            if u.email == email.lower().strip() and u.verificar_senha(senha):
                token = str(uuid.uuid4())
                self.sessions[token] = u.id
                return token
        return None

    def usuario_por_token(self, token: str):
        user_id = self.sessions.get(token)
        if not user_id:
            return None
        if user_id in self.admins:
            return self.admins[user_id]
        if user_id in self.medicos:
            return self.medicos[user_id]
        if user_id in self.pacientes:
            return self.pacientes[user_id]
        return None

    # --- dados iniciais ---
    def _seed(self) -> None:
        # carregar usuários persistidos
        for row in db.carregar_por_perfil(Perfil.ADMIN.value):
            admin = Administrador(
                _id=row["id"],
                _nome=row["nome"],
                _email=row["email"],
                _perfil=Perfil.ADMIN,
                _telefone=row["telefone"],
                _senha=row["senha"],
            )
            self.admins[admin.id] = admin

        for row in db.carregar_por_perfil(Perfil.MEDICO.value):
            med = Medico(
                _id=row["id"],
                _nome=row["nome"],
                _email=row["email"],
                _perfil=Perfil.MEDICO,
                _telefone=row["telefone"],
                _senha=row["senha"],
                especialidades=json.loads(row["especialidades"]) if row["especialidades"] else [],
            )
            self.adicionar_medico(med)

        for row in db.carregar_por_perfil(Perfil.PACIENTE.value):
            pac = Paciente(
                _id=row["id"],
                _nome=row["nome"],
                _email=row["email"],
                _perfil=Perfil.PACIENTE,
                _telefone=row["telefone"],
                _senha=row["senha"],
            )
            self.pacientes[pac.id] = pac

        if not self.admins:
            self.adicionar_admin(
                Administrador.novo("Admin", "admin@medsched.com", telefone="1100000000", senha="admin123")
            )
        if not self.medicos:
            self.adicionar_medico(
                Medico.novo(
                    "Dra. Ana Cardoso",
                    "ana@clinic.com",
                    especialidades=["Cardiologia", "Clínica Geral"],
                    telefone="11999990000",
                    senha="ana123",
                )
            )
            self.adicionar_medico(
                Medico.novo(
                    "Dr. Bruno Silva",
                    "bruno@clinic.com",
                    especialidades=["Ortopedia"],
                    telefone="21988887777",
                    senha="bruno123",
                )
            )
        if not self.pacientes:
            joao = self.adicionar_paciente(
                Paciente.novo("João da Silva", "joao@email.com", telefone="11922223333", senha="joao123")
            )
            maria = self.adicionar_paciente(
                Paciente.novo("Maria Oliveira", "maria@email.com", telefone="21911114444", senha="maria123")
            )
        else:
            # reutiliza primeiros pacientes para seed de consultas
            joao = next(iter(self.pacientes.values()))
            maria = next(iter(self.pacientes.values()))

        # seeds de slots/consultas apenas para médicos já carregados
        medicos_para_seed = list(self.medicos.values())
        if len(medicos_para_seed) >= 2:
            ana, bruno = medicos_para_seed[0], medicos_para_seed[1]
        elif medicos_para_seed:
            ana = medicos_para_seed[0]
            bruno = medicos_para_seed[0]
        else:
            return

        base = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        for med in (ana, bruno):
            for offset in range(1, 6):
                inicio = base + timedelta(hours=offset)
                fim = inicio + timedelta(minutes=30)
                try:
                    self.servico.disponibilizar_slot(med, inicio, fim)
                except Exception:
                    pass
            lunch_inicio = base + timedelta(hours=3, minutes=30)
            lunch_fim = lunch_inicio + timedelta(minutes=30)
            try:
                self.servico.bloquear_horario(med, lunch_inicio, lunch_fim)
            except Exception:
                pass

        # consulta exemplo
        try:
            consulta = self.servico.agendar(joao, ana, base + timedelta(hours=1), base + timedelta(hours=1, minutes=30))
            self.servico.confirmar(consulta.id)
        except Exception:
            pass
        try:
            self.servico.agendar(maria, bruno, base + timedelta(hours=2), base + timedelta(hours=2, minutes=30))
        except Exception:
            pass


store = MemoryStore()
