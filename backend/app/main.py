from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .domain import Medico, Paciente, Perfil, StatusConsulta
from .domain.exceptions import DomainError
from .schemas import (
    AgendamentoRequest,
    ApiState,
    ConsultaOut,
    LoginRequest,
    LoginResponse,
    MedicoCreate,
    PacienteCreate,
    RemarcarRequest,
    SlotOut,
    UsuarioOut,
)
from .storage import store

app = FastAPI(title="MedSched", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serializar_consulta(consulta) -> ConsultaOut:
    med = store.medicos.get(consulta.medico_id)
    pac = store.pacientes.get(consulta.paciente_id)
    return ConsultaOut(
        id=consulta.id,
        paciente_id=consulta.paciente_id,
        paciente_nome=pac.nome if pac else "Paciente",
        medico_id=consulta.medico_id,
        medico_nome=med.nome if med else "Médico",
        especialidade=(med.especialidades[0] if med and med.especialidades else None),
        especialidades=getattr(med, "especialidades", None),
        inicio=consulta.inicio,
        fim=consulta.fim,
        status=consulta.status,
        observacoes=consulta.observacoes,
    )


def _handle_domain_error(err: DomainError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


def _extract_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1]
    return auth_header


def get_usuario(auth: Optional[str] = Header(default=None, alias="Authorization")):
    token = _extract_token(auth)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")
    user = store.usuario_por_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return user


def optional_usuario(auth: Optional[str] = Header(default=None, alias="Authorization")):
    token = _extract_token(auth)
    if not token:
        return None
    return store.usuario_por_token(token)


def require_admin(user=Depends(get_usuario)):
    if user.perfil != Perfil.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores")
    return user


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    token = store.autenticar(payload.email, payload.senha)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    usuario = store.usuario_por_token(token)
    return LoginResponse(token=token, usuario=usuario)


@app.get("/me", response_model=UsuarioOut)
def me(usuario=Depends(get_usuario)):
    return usuario


@app.get("/medicos", response_model=List[UsuarioOut])
def listar_medicos(especializacao: Optional[str] = Query(default=None)):
    medicos = list(store.medicos.values())
    if especializacao:
        medicos = [m for m in medicos if m.especialidades and especializacao.lower() in " ".join(m.especialidades).lower()]
    return medicos


@app.post("/medicos", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_medico(payload: MedicoCreate, _admin=Depends(require_admin)):
    try:
        medico = Medico.novo(
            payload.nome,
            payload.email,
            especialidades=payload.especialidades,
            telefone=payload.telefone,
            senha=payload.senha,
        )
        return store.adicionar_medico(medico)
    except DomainError as err:
        _handle_domain_error(err)


@app.get("/pacientes", response_model=List[UsuarioOut])
def listar_pacientes(_admin=Depends(require_admin)):
    return list(store.pacientes.values())


@app.post("/pacientes", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_paciente(payload: PacienteCreate, _admin=Depends(require_admin)):
    try:
        paciente = Paciente.novo(payload.nome, payload.email, payload.telefone, senha=payload.senha)
        return store.adicionar_paciente(paciente)
    except DomainError as err:
        _handle_domain_error(err)


@app.get("/agendas/{medico_id}/slots", response_model=List[SlotOut])
def horarios_disponiveis(medico_id: str):
    try:
        medico = store.obter_medico(medico_id)
        return store.servico.slots_disponiveis(medico)
    except DomainError as err:
        _handle_domain_error(err)


@app.post("/agendas/{medico_id}/slots", response_model=List[SlotOut], status_code=status.HTTP_201_CREATED)
def criar_slot(medico_id: str, slot: SlotOut, usuario=Depends(get_usuario)):
    try:
        medico = store.obter_medico(medico_id)
        if usuario.perfil not in (Perfil.ADMIN, Perfil.MEDICO) or (usuario.perfil == Perfil.MEDICO and usuario.id != medico_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para alterar esta agenda")
        if slot.bloqueado:
            store.servico.bloquear_horario(medico, slot.inicio, slot.fim)
        else:
            store.servico.disponibilizar_slot(medico, slot.inicio, slot.fim)
        return store.servico.slots_disponiveis(medico)
    except DomainError as err:
        _handle_domain_error(err)


@app.get("/consultas", response_model=List[ConsultaOut])
def listar_consultas(
    medico_id: Optional[str] = Query(default=None),
    paciente_id: Optional[str] = Query(default=None),
    status_filtro: Optional[StatusConsulta] = Query(default=None, alias="status"),
    usuario=Depends(optional_usuario),
):
    consultas = store.servico.consultas.values()
    if medico_id:
        consultas = [c for c in consultas if c.medico_id == medico_id]
    if paciente_id:
        consultas = [c for c in consultas if c.paciente_id == paciente_id]
    if status_filtro:
        consultas = [c for c in consultas if c.status == status_filtro]
    # proteção mínima: se usuário autenticado, só vê suas consultas (médico/paciente) exceto admin
    if usuario and usuario.perfil == Perfil.PACIENTE:
        consultas = [c for c in consultas if c.paciente_id == usuario.id]
    if usuario and usuario.perfil == Perfil.MEDICO:
        consultas = [c for c in consultas if c.medico_id == usuario.id]
    return [_serializar_consulta(c) for c in consultas]


@app.post("/consultas", response_model=ConsultaOut, status_code=status.HTTP_201_CREATED)
def agendar(payload: AgendamentoRequest, usuario=Depends(get_usuario)):
    if usuario.perfil not in (Perfil.PACIENTE, Perfil.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente pacientes ou admins")
    if usuario.perfil == Perfil.PACIENTE and usuario.id != payload.paciente_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Paciente inválido")
    try:
        paciente = store.obter_paciente(payload.paciente_id)
        medico = store.obter_medico(payload.medico_id)
        consulta = store.servico.agendar(paciente, medico, payload.inicio, payload.fim)
        return _serializar_consulta(consulta)
    except DomainError as err:
        _handle_domain_error(err)


def _autorizar_consulta(usuario, consulta):
    if usuario.perfil == Perfil.ADMIN:
        return True
    if usuario.perfil == Perfil.PACIENTE and consulta.paciente_id == usuario.id:
        return True
    if usuario.perfil == Perfil.MEDICO and consulta.medico_id == usuario.id:
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para esta consulta")


@app.post("/consultas/{consulta_id}/confirmar", response_model=ConsultaOut)
def confirmar(consulta_id: str, usuario=Depends(get_usuario)):
    try:
        consulta = store.servico._obter(consulta_id)
        if usuario.perfil != Perfil.MEDICO or usuario.id != consulta.medico_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o médico pode confirmar")
        consulta = store.servico.confirmar(consulta_id)
        return _serializar_consulta(consulta)
    except DomainError as err:
        _handle_domain_error(err)


@app.post("/consultas/{consulta_id}/cancelar", response_model=ConsultaOut)
def cancelar(consulta_id: str, usuario=Depends(get_usuario)):
    try:
        consulta = store.servico._obter(consulta_id)
        _autorizar_consulta(usuario, consulta)
        consulta = store.servico.cancelar(consulta_id)
        return _serializar_consulta(consulta)
    except DomainError as err:
        _handle_domain_error(err)


@app.post("/consultas/{consulta_id}/remarcar", response_model=ConsultaOut)
def remarcar(consulta_id: str, payload: RemarcarRequest, usuario=Depends(get_usuario)):
    try:
        consulta = store.servico._obter(consulta_id)
        _autorizar_consulta(usuario, consulta)
        confirmar = usuario.perfil == Perfil.MEDICO and usuario.id == consulta.medico_id
        nova_consulta = store.servico.remarcar(consulta_id, payload.novo_inicio, payload.novo_fim, confirmar_nova=confirmar)
        return _serializar_consulta(nova_consulta)
    except DomainError as err:
        _handle_domain_error(err)


@app.get("/estado", response_model=ApiState)
def estado_atual(medico_id: Optional[str] = None):
    medico_ref = store.medicos.get(medico_id) if medico_id else next(iter(store.medicos.values()), None)
    slots = store.servico.slots_disponiveis(medico_ref) if medico_ref else []
    return ApiState(
        medicos=list(store.medicos.values()),
        pacientes=list(store.pacientes.values()),
        slots=slots,
        consultas=[_serializar_consulta(c) for c in store.servico.consultas.values()],
    )
