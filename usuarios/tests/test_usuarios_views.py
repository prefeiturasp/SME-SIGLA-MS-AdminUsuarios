import pytest
from django.contrib.auth.models import User
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIRequestFactory

from usuarios.exceptions import (
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoRequisicaoError,
    SmeIntegracaoException,
)
from usuarios.views.usuarios import (
    CriarNovaSenhaView,
    CriarUsuarioView,
    EsqueciSenhaView,
    LoginView,
    _mask_email,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def rf():
    return APIRequestFactory()


def test_mask_email_formats_values():
    assert _mask_email("abcde@prefeitura.sp.gov.br") == "a***e@prefeitura.sp.gov.br"
    assert _mask_email("ab@prefeitura.sp.gov.br") == "a*@prefeitura.sp.gov.br"
    assert _mask_email("invalido") == "***"


def test_login_user_not_found_returns_401(rf):
    request = rf.post("/usuarios/login/", {"usuario": "nao-existe", "senha": "123"}, format="json")
    response = LoginView.as_view()(request)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["detail"] == "Usuário não encontrado"


def test_login_invalid_credentials_returns_401(rf, monkeypatch):
    User.objects.create_user(username="rf123", password="segredo")
    def _raise_invalid(*_args, **_kwargs):
        raise AutenticacaoCredenciaisInvalidasError()

    monkeypatch.setattr("usuarios.views.usuarios.AutenticacaoService.autentica", _raise_invalid)
    request = rf.post("/usuarios/login/", {"usuario": "rf123", "senha": "errada"}, format="json")
    response = LoginView.as_view()(request)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["detail"] == "Credenciais inválidas"


def test_login_upstream_error_returns_400(rf, monkeypatch):
    User.objects.create_user(username="rf123", password="segredo")
    def _raise_upstream(*_args, **_kwargs):
        raise AutenticacaoRequisicaoError("falha")

    monkeypatch.setattr("usuarios.views.usuarios.AutenticacaoService.autentica", _raise_upstream)
    request = rf.post("/usuarios/login/", {"usuario": "rf123", "senha": "segredo"}, format="json")
    response = LoginView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Falha no serviço de autenticação"


def test_login_success_returns_payload(rf, monkeypatch):
    user = User.objects.create_user(username="rf123", password="segredo")
    monkeypatch.setattr(
        "usuarios.views.usuarios.AutenticacaoService.autentica",
        lambda *_args, **_kwargs: {"token": "abc"},
    )
    called = {"count": 0}

    def _montar(*_args, **_kwargs):
        called["count"] += 1
        return {"access": "ok", "user": {"username": user.username}}

    monkeypatch.setattr("usuarios.views.usuarios.AutenticacaoService.montar_resposta_login", _montar)

    request = rf.post("/usuarios/login/", {"usuario": "rf123", "senha": "segredo"}, format="json")
    response = LoginView.as_view()(request)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["access"] == "ok"
    assert called["count"] == 1


def test_esqueci_senha_user_not_found(rf):
    request = rf.post("/usuarios/esqueci-minha-senha/", {"rf": "000"}, format="json")
    response = EsqueciSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado"


def test_esqueci_senha_sme_failure(rf, monkeypatch):
    User.objects.create_user(username="123")
    def _raise(*_args, **_kwargs):
        raise Exception("erro")

    monkeypatch.setattr("usuarios.views.usuarios.SmeIntegracaoService.informacao_usuario", _raise)
    request = rf.post("/usuarios/esqueci-minha-senha/", {"rf": "123"}, format="json")
    response = EsqueciSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Falha ao consultar dados do usuário"


def test_esqueci_senha_email_not_found(rf, monkeypatch):
    User.objects.create_user(username="123")
    monkeypatch.setattr(
        "usuarios.views.usuarios.SmeIntegracaoService.informacao_usuario",
        lambda *_args, **_kwargs: {"Nome": "Maria"},
    )
    request = rf.post("/usuarios/esqueci-minha-senha/", {"rf": "123"}, format="json")
    response = EsqueciSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "E-mail não encontrado para o usuário"


def test_esqueci_senha_email_send_failure(rf, monkeypatch):
    User.objects.create_user(username="123", first_name="Maria")
    monkeypatch.setattr(
        "usuarios.views.usuarios.SmeIntegracaoService.informacao_usuario",
        lambda *_args, **_kwargs: {"Nome": "Maria", "Email": "maria@prefeitura.sp.gov.br"},
    )

    def _raise_send(*_args, **_kwargs):
        raise Exception("smtp")

    monkeypatch.setattr("usuarios.views.usuarios.EmailService.enviar_email_esqueci_senha", _raise_send)
    request = rf.post("/usuarios/esqueci-minha-senha/", {"rf": "123"}, format="json")
    response = EsqueciSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.data["detail"] == "Falha ao enviar e-mail"


def test_esqueci_senha_success(rf, monkeypatch):
    User.objects.create_user(username="123", first_name="Maria")
    monkeypatch.setattr(
        "usuarios.views.usuarios.SmeIntegracaoService.informacao_usuario",
        lambda *_args, **_kwargs: {"Nome": "Maria", "Email": "maria@prefeitura.sp.gov.br"},
    )
    monkeypatch.setattr("usuarios.views.usuarios.EmailService.enviar_email_esqueci_senha", lambda *_args, **_kwargs: None)
    request = rf.post("/usuarios/esqueci-minha-senha/", {"rf": "123"}, format="json")
    response = EsqueciSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["usuario"] == "123"
    assert response.data["email_enviado"] is True


def test_criar_nova_senha_uid_invalido(rf):
    request = rf.post(
        "/usuarios/criar-nova-senha/",
        {"uid": "invalido", "token": "x", "nova_senha": "novasenha"},
        format="json",
    )
    response = CriarNovaSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "UID inválido"


def test_criar_nova_senha_token_invalido(rf):
    user = User.objects.create_user(username="123", password="senha-antiga")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    request = rf.post(
        "/usuarios/criar-nova-senha/",
        {"uid": uid, "token": "token-invalido", "nova_senha": "novasenha"},
        format="json",
    )
    response = CriarNovaSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Token inválido"


def test_criar_nova_senha_sme_exception(rf, monkeypatch):
    user = User.objects.create_user(username="123", password="senha-antiga")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    called = {"count": 0}

    def _check_token(*_args, **_kwargs):
        called["count"] += 1
        return True

    def _raise_sme(*_args, **_kwargs):
        raise SmeIntegracaoException("erro")

    monkeypatch.setattr("usuarios.views.usuarios.default_token_generator.check_token", _check_token)
    monkeypatch.setattr("usuarios.views.usuarios.SmeIntegracaoService.redefine_senha", _raise_sme)
    request = rf.post(
        "/usuarios/criar-nova-senha/",
        {"uid": uid, "token": "ok", "nova_senha": "novasenha"},
        format="json",
    )
    response = CriarNovaSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Falha ao redefinir senha no SME Integração"
    assert called["count"] == 1


def test_criar_nova_senha_success(rf, monkeypatch):
    user = User.objects.create_user(username="123", password="senha-antiga")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    monkeypatch.setattr("usuarios.views.usuarios.default_token_generator.check_token", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("usuarios.views.usuarios.SmeIntegracaoService.redefine_senha", lambda *_args, **_kwargs: None)
    request = rf.post(
        "/usuarios/criar-nova-senha/",
        {"uid": uid, "token": "ok", "nova_senha": "novasenha"},
        format="json",
    )
    response = CriarNovaSenhaView.as_view()(request)
    user.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert user.check_password("novasenha")


def test_criar_usuario_username_conflict(rf):
    User.objects.create_user(username="existente", email="x@x.com", password="123456")
    request = rf.post(
        "/usuarios/criar-usuario/",
        {"usuario": "existente", "senha": "123456", "email": "novo@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Nome de usuário" in response.data["detail"]


def test_criar_usuario_email_conflict(rf):
    User.objects.create_user(username="u1", email="igual@x.com", password="123456")
    request = rf.post(
        "/usuarios/criar-usuario/",
        {"usuario": "novo", "senha": "123456", "email": "igual@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "E-mail" in response.data["detail"]


def test_criar_usuario_success(rf):
    request = rf.post(
        "/usuarios/criar-usuario/",
        {"usuario": "novo", "senha": "123456", "email": "novo@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"] == "novo"
    assert User.objects.filter(username="novo").exists()

