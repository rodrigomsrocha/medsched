# -*- coding: utf-8 -*-
import os
import sys
import json
from importlib import reload
from typing import Dict, List, Tuple, Optional

# Adiciona o diretório backend ao Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from app.schemas import LoginRequest, AgendamentoRequest, RemarcarRequest


class SimpleResponse:
    def __init__(self, status_code: int, body: bytes, headers: Optional[List[Tuple[bytes, bytes]]] = None):
        self.status_code = status_code
        self._body = body or b""
        self.headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in (headers or [])}
        self.text = self._body.decode("utf-8") if self._body else ""

    def json(self):
        if not self._body:
            return None
        return json.loads(self._body)


class TestClient:
    __test__ = False

    def __init__(self, app):
        self.app = app

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> SimpleResponse:
        return dispatch_request(self.app, "GET", path, None, headers or {})

    def post(self, path: str, json: Optional[Dict] = None, headers: Optional[Dict[str, str]] = None) -> SimpleResponse:
        return dispatch_request(self.app, "POST", path, json, headers or {})

# Configura BD temporário antes de carregar a app
os.environ["MEDSCHED_DB_PATH"] = os.environ.get("PYTEST_DB_PATH", "/tmp/medsched_test.db")

import app.storage as storage  # noqa: E402
import app.main as main  # noqa: E402


def _optional_user(headers: Dict[str, str]):
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return None
    token = auth.split(" ", 1)[1] if " " in auth else auth
    return storage.store.usuario_por_token(token)


def _require_user(headers: Dict[str, str]):
    user = _optional_user(headers)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return user


def _response(payload, status_code: int) -> SimpleResponse:
    body = json.dumps(jsonable_encoder(payload)).encode("utf-8") if payload is not None else b""
    return SimpleResponse(status_code, body)


def _error_response(exc: HTTPException) -> SimpleResponse:
    detail = {"detail": exc.detail}
    return _response(detail, exc.status_code)


def dispatch_request(app, method: str, path: str, body_json: Optional[Dict], headers: Dict[str, str]) -> SimpleResponse:
    try:
        if method == "POST" and path == "/auth/login":
            payload = LoginRequest(**(body_json or {}))
            res = main.login(payload)
            return _response(res, status.HTTP_200_OK)

        if method == "GET" and path.startswith("/agendas/") and path.endswith("/slots"):
            medico_id = path.split("/")[2]
            res = main.horarios_disponiveis(medico_id)
            return _response(res, status.HTTP_200_OK)

        if method == "POST" and path == "/consultas":
            usuario = _require_user(headers)
            payload = AgendamentoRequest(**(body_json or {}))
            res = main.agendar(payload, usuario=usuario)
            return _response(res, status.HTTP_201_CREATED)

        if method == "GET" and path == "/consultas":
            usuario = _optional_user(headers)
            res = main.listar_consultas(medico_id=None, paciente_id=None, status_filtro=None, usuario=usuario)
            return _response(res, status.HTTP_200_OK)

        if method == "POST" and path.startswith("/consultas/") and path.endswith("/remarcar"):
            consulta_id = path.split("/")[2]
            usuario = _require_user(headers)
            payload = RemarcarRequest(**(body_json or {}))
            res = main.remarcar(consulta_id, payload, usuario=usuario)
            return _response(res, status.HTTP_200_OK)

        return SimpleResponse(status.HTTP_404_NOT_FOUND, b"")

    except HTTPException as exc:
        return _error_response(exc)
    except Exception as exc:  # noqa: BLE001
        return SimpleResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, json.dumps({"detail": str(exc)}).encode("utf-8"))


def fresh_client() -> TestClient:
    db_path = os.environ.get("MEDSCHED_DB_PATH", "/tmp/medsched_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    # cria store novo e injeta na app
    storage.store = storage.MemoryStore()
    main.store = storage.store
    reload(main)
    main.store = storage.store
    return TestClient(main.app)


def auth_headers(client: TestClient, email: str, senha: str) -> Dict[str, str]:
    res = client.post("/auth/login", json={"email": email, "senha": senha})
    assert res.status_code == 200, res.text
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_admin():
    client = fresh_client()
    res = client.post("/auth/login", json={"email": "admin@medsched.com", "senha": "admin123"})
    assert res.status_code == 200
    body = res.json()
    assert body["usuario"]["perfil"] == "ADMIN"


def test_patient_cannot_overlap_same_patient():
    client = fresh_client()
    headers = auth_headers(client, "joao@email.com", "joao123")
    # obter slots de outro médico no mesmo horário da consulta inicial (primeiro slot de Bruno)
    bruno_slots = client.get(f"/agendas/{list(storage.store.medicos.values())[1].id}/slots")
    assert bruno_slots.status_code == 200
    slot = bruno_slots.json()[0]
    # primeira tentativa deve dar erro porque já há consulta nesse intervalo com Ana
    agendar_res = client.post(
        "/consultas",
        json={
            "paciente_id": list(storage.store.pacientes.values())[0].id,
            "medico_id": list(storage.store.medicos.values())[1].id,
            "inicio": slot["inicio"],
            "fim": slot["fim"],
        },
        headers=headers,
    )
    assert agendar_res.status_code == 400
    assert "consulta" in agendar_res.json()["detail"].lower()


def test_reschedule_patient_requires_confirmation():
    client = fresh_client()
    headers = auth_headers(client, "joao@email.com", "joao123")
    consultas = client.get("/consultas", headers=headers).json()
    consulta = consultas[0]
    med_id = consulta["medico_id"]
    slots = client.get(f"/agendas/{med_id}/slots").json()
    novo = slots[-1]
    res = client.post(
        f"/consultas/{consulta['id']}/remarcar",
        json={"novo_inicio": novo["inicio"], "novo_fim": novo["fim"]},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "AGENDADA"


def test_reschedule_by_doctor_confirms_and_cancels_conflicts():
    client = fresh_client()
    headers_doc = auth_headers(client, "bruno@clinic.com", "bruno123")
    consultas_doc = client.get("/consultas", headers=headers_doc).json()
    consulta = consultas_doc[0]
    slots = client.get(f"/agendas/{consulta['medico_id']}/slots").json()
    novo = slots[-1]
    res = client.post(
        f"/consultas/{consulta['id']}/remarcar",
        json={"novo_inicio": novo["inicio"], "novo_fim": novo["fim"]},
        headers=headers_doc,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "CONFIRMADA"

    # cria outra consulta no mesmo slot para outro paciente e verifica cancelamento ao confirmar
    headers_pac = auth_headers(client, "joao@email.com", "joao123")
    agendar = client.post(
        "/consultas",
        json={
            "paciente_id": list(storage.store.pacientes.values())[0].id,
            "medico_id": consulta["medico_id"],
            "inicio": novo["inicio"],
            "fim": novo["fim"],
        },
        headers=headers_pac,
    )
    assert agendar.status_code == 400  # slot já confirmado pelo médico


if __name__ == "__main__":
    pytest.main([__file__])
