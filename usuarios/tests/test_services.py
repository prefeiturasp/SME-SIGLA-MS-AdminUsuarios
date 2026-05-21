from types import SimpleNamespace

import pytest
import requests
from django.contrib.auth.models import User

from usuarios.exceptions import (
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoRequisicaoError,
    AutenticacaoRespostaInvalidaError,
    AutenticacaoUpstreamError,
    SmeIntegracaoException,
)
from usuarios.services.autenticacao import AutenticacaoService
from usuarios.services.email import EmailService
from usuarios.services.sme_integracao import SmeIntegracaoService
from usuarios.services.token_service import TokenService


pytestmark = pytest.mark.django_db


def test_autenticacao_service_autentica_success(monkeypatch):
    response = SimpleNamespace(status_code=200, json=lambda: {"ok": True})
    monkeypatch.setattr("usuarios.services.autenticacao.requests.post", lambda *args, **kwargs: response)

    result = AutenticacaoService.autentica("user", "pwd")

    assert result == {"ok": True}


def test_autenticacao_service_autentica_error_paths(monkeypatch):
    unauthorized = SimpleNamespace(status_code=401, json=lambda: {"detail": "unauthorized"})
    invalid_json = SimpleNamespace(status_code=200, json=lambda: 1 / 0)
    upstream_error = SimpleNamespace(status_code=500, json=lambda: {"detail": "error"})

    monkeypatch.setattr("usuarios.services.autenticacao.requests.post", lambda *args, **kwargs: unauthorized)
    with pytest.raises(AutenticacaoCredenciaisInvalidasError):
        AutenticacaoService.autentica("user", "pwd")

    monkeypatch.setattr("usuarios.services.autenticacao.requests.post", lambda *args, **kwargs: invalid_json)
    with pytest.raises(AutenticacaoRespostaInvalidaError):
        AutenticacaoService.autentica("user", "pwd")

    monkeypatch.setattr("usuarios.services.autenticacao.requests.post", lambda *args, **kwargs: upstream_error)
    with pytest.raises(AutenticacaoUpstreamError):
        AutenticacaoService.autentica("user", "pwd")

    def _raise_req(*_args, **_kwargs):
        raise requests.RequestException("network")

    monkeypatch.setattr("usuarios.services.autenticacao.requests.post", _raise_req)
    with pytest.raises(AutenticacaoRequisicaoError):
        AutenticacaoService.autentica("user", "pwd")


def test_autenticacao_service_login_payload_helpers(monkeypatch):
    user = User.objects.create_user(username="alice")
    monkeypatch.setattr(
        "usuarios.services.autenticacao.RefreshToken.for_user",
        lambda _user: SimpleNamespace(access_token="access-token", __str__=lambda self: "refresh-token"),
    )

    tokens = AutenticacaoService.gerar_tokens_para_usuario(user)
    resposta = AutenticacaoService.montar_resposta_login({"foo": "bar"}, user)

    assert tokens["access"] == "access-token"
    assert "refresh" in tokens
    assert resposta["foo"] == "bar"
    assert resposta["token"] == "access-token"


def test_sme_integracao_informacao_usuario_success_and_errors(monkeypatch):
    ok_response = SimpleNamespace(status_code=200, json=lambda: {"Nome": "Maria"})
    not_found_response = SimpleNamespace(status_code=404, json=lambda: {})

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.get", lambda *args, **kwargs: ok_response)
    assert SmeIntegracaoService.informacao_usuario("123") == {"Nome": "Maria"}

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.get", lambda *args, **kwargs: not_found_response)
    with pytest.raises(SmeIntegracaoException, match="Dados não encontrados"):
        SmeIntegracaoService.informacao_usuario("123")

    def _raise_request(*_args, **_kwargs):
        raise requests.RequestException("timeout")

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.get", _raise_request)
    with pytest.raises(requests.RequestException):
        SmeIntegracaoService.informacao_usuario("123")


def test_sme_integracao_redefine_senha_success_and_errors(monkeypatch):
    success_response = SimpleNamespace(status_code=200, content=b"")
    fail_response = SimpleNamespace(status_code=400, content=b"{senha invalida}")

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.post", lambda *args, **kwargs: success_response)
    assert SmeIntegracaoService.redefine_senha("123", "nova") == "OK"

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.post", lambda *args, **kwargs: fail_response)
    with pytest.raises(SmeIntegracaoException, match="senha invalida"):
        SmeIntegracaoService.redefine_senha("123", "nova")

    with pytest.raises(SmeIntegracaoException, match="obrigatórios"):
        SmeIntegracaoService.redefine_senha("", "")


def test_sme_integracao_alterar_email_success_and_errors(monkeypatch):
    success_response = SimpleNamespace(status_code=200, content=b"")
    fail_response = SimpleNamespace(status_code=400, content=b"{email invalido}")

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.post", lambda *a, **k: success_response)
    assert SmeIntegracaoService.alterar_email("123", "novo@x.com") == "OK"

    monkeypatch.setattr("usuarios.services.sme_integracao.requests.post", lambda *a, **k: fail_response)
    with pytest.raises(SmeIntegracaoException, match="email invalido"):
        SmeIntegracaoService.alterar_email("123", "novo@x.com")

    with pytest.raises(SmeIntegracaoException, match="obrigatórios"):
        SmeIntegracaoService.alterar_email("", "")
    with pytest.raises(SmeIntegracaoException, match="obrigatórios"):
        SmeIntegracaoService.alterar_email("123", "")


def test_token_service_gerar_token_para_reset():
    user = User.objects.create_user(username="alice", first_name="Alice")

    data = TokenService.gerar_token_para_reset(user, "alice@example.com")

    assert data["name"] == "Alice"
    assert data["uid"]
    assert data["token"]


def test_email_service_enviar_email_and_reset(monkeypatch, settings):
    settings.DEFAULT_FROM_EMAIL = "default@example.com"
    settings.APLICACAO_URL = "http://frontend.local"
    settings.MS_URL = "http://ms.local"

    captured = {}

    class DummyEmail:
        def __init__(self, subject, body, from_email, to, headers):
            captured["subject"] = subject
            captured["body"] = body
            captured["from_email"] = from_email
            captured["to"] = to
            captured["headers"] = headers
            captured["alternatives"] = []

        def attach_alternative(self, html, content_type):
            captured["alternatives"].append((html, content_type))

        def send(self):
            captured["sent"] = True

    monkeypatch.setattr("usuarios.services.email.render_to_string", lambda *_args, **_kwargs: "<b>Oi</b>")
    monkeypatch.setattr("usuarios.services.email.EmailMultiAlternatives", DummyEmail)

    EmailService.enviar_email(
        subject="Assunto",
        template_name="x.html",
        context={"k": "v"},
        recipients=["dest@example.com"],
    )

    user = User.objects.create_user(username="alice", first_name="Alice")
    monkeypatch.setattr(
        "usuarios.services.email.TokenService.gerar_token_para_reset",
        lambda *_args, **_kwargs: {"uid": "uid1", "token": "tok1", "name": "Alice"},
    )
    EmailService.enviar_email_esqueci_senha(user, "dest@example.com", "Alice")

    assert captured["from_email"] == "default@example.com"
    assert captured["to"] == ["dest@example.com"]
    assert captured["sent"] is True
