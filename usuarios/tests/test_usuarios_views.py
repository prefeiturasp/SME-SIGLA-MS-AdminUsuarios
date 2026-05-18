import pytest
from django.contrib.auth.models import User, Group
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIRequestFactory

from usuarios.exceptions import (
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoRequisicaoError,
    SmeIntegracaoException,
)
from usuarios.serializers.password import AlterarSenhaSerializer
from usuarios.views.usuarios import (
    AlterarSenhaView,
    CriarNovaSenhaView,
    CriarUsuarioView,
    EsqueciSenhaView,
    LoginView,
    MeusDadosView,
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
        {"username": "existente", "nome": "Maria Silva", "email": "novo@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Nome de usuário" in response.data["detail"]


def test_criar_usuario_email_conflict(rf):
    User.objects.create_user(username="u1", email="igual@x.com", password="123456")
    request = rf.post(
        "/usuarios/criar-usuario/",
        {"username": "novo", "nome": "Maria Silva", "email": "igual@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "E-mail" in response.data["detail"]


def test_criar_usuario_success(rf):
    request = rf.post(
        "/usuarios/criar-usuario/",
        {"username": "novo", "nome": "Maria Silva", "email": "novo@x.com"},
        format="json",
    )
    response = CriarUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"] == "novo"
    user = User.objects.get(username="novo")
    assert user.first_name == "Maria"
    assert user.last_name == "Silva"
    assert user.has_usable_password() is False

def test_meus_dados_unauthenticated(rf):
    request = rf.get("/usuarios/meus-dados/")
    response = MeusDadosView.as_view()(request)
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_meus_dados_sem_grupos(rf):
    user = User.objects.create_user(
        username="rf999", first_name="João", last_name="Silva", email="joao@sp.gov.br"
    )
    request = rf.get("/usuarios/meus-dados/")
    request.user = user
    response = MeusDadosView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["rf"] == "rf999"
    assert response.data["nome_completo"] == "João Silva"
    assert response.data["email"] == "joao@sp.gov.br"
    assert response.data["perfil_acesso"] == []


def test_meus_dados_com_grupos(rf):
    user = User.objects.create_user(username="rf888", first_name="Maria")
    grupo = Group.objects.create(name="Gestor")
    user.groups.add(grupo)
    request = rf.get("/usuarios/meus-dados/")
    request.user = user
    response = MeusDadosView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert "Gestor" in response.data["perfil_acesso"]


def test_meus_dados_nome_apenas_first_name(rf):
    user = User.objects.create_user(username="rf777", first_name="Ana", last_name="")
    request = rf.get("/usuarios/meus-dados/")
    request.user = user
    response = MeusDadosView.as_view()(request)
    assert response.data["nome_completo"] == "Ana"


# ── AlterarSenhaView ──────────────────────────────────────────────────────────

def test_alterar_senha_unauthenticated(rf):
    request = rf.post("/usuarios/alterar-senha/", {}, format="json")
    response = AlterarSenhaView.as_view()(request)
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_alterar_senha_atual_incorreta(rf):
    user = User.objects.create_user(username="rf111", password="SenhaCorreta1!")
    request = rf.post(
        "/usuarios/alterar-senha/",
        {"senha_atual": "Errada1!", "nova_senha": "NovaSenha1!", "confirmacao_nova_senha": "NovaSenha1!"},
        format="json",
    )
    request.user = user
    response = AlterarSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Senha atual incorreta" in response.data["detail"]


def test_alterar_senha_sme_exception(rf, monkeypatch):
    user = User.objects.create_user(username="rf222", password="SenhaCorreta1!")

    def _raise_sme(*_args, **_kwargs):
        raise SmeIntegracaoException("senha fraca")

    monkeypatch.setattr("usuarios.views.usuarios.SmeIntegracaoService.redefine_senha", _raise_sme)
    request = rf.post(
        "/usuarios/alterar-senha/",
        {"senha_atual": "SenhaCorreta1!", "nova_senha": "NovaSenha1!", "confirmacao_nova_senha": "NovaSenha1!"},
        format="json",
    )
    request.user = user
    response = AlterarSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "senha fraca" in response.data["detail"]


def test_alterar_senha_success(rf, monkeypatch):
    user = User.objects.create_user(username="rf333", password="SenhaCorreta1!")
    monkeypatch.setattr("usuarios.views.usuarios.SmeIntegracaoService.redefine_senha", lambda *_a, **_k: None)
    request = rf.post(
        "/usuarios/alterar-senha/",
        {"senha_atual": "SenhaCorreta1!", "nova_senha": "NovaSenha1!", "confirmacao_nova_senha": "NovaSenha1!"},
        format="json",
    )
    request.user = user
    response = AlterarSenhaView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Senha alterada com sucesso"
    user.refresh_from_db()
    assert user.check_password("NovaSenha1!")


# ── AlterarSenhaSerializer ────────────────────────────────────────────────────

@pytest.mark.parametrize("nova_senha,esperado", [
    ("curta1!", "entre 8 e 12"),
    ("SenhaLongaDemais1!", "entre 8 e 12"),
    ("Semsymbol1", "símbolo"),
    ("SEMMINUS1!", "minúscula"),
    ("semmaius1!", "maiúscula"),
    ("SemNumero!", "número"),
    ("Espaço 1!", "espaços"),
    ("Acentuàdo1!", "acentuados"),
])
def test_alterar_senha_serializer_validacao_nova_senha(nova_senha, esperado):
    data = {
        "senha_atual": "Antiga1!",
        "nova_senha": nova_senha,
        "confirmacao_nova_senha": nova_senha,
    }
    serializer = AlterarSenhaSerializer(data=data)
    assert not serializer.is_valid()
    errors_str = str(serializer.errors)
    assert esperado in errors_str


def test_alterar_senha_serializer_confirmacao_divergente():
    data = {
        "senha_atual": "Antiga1!",
        "nova_senha": "NovaSenha1!",
        "confirmacao_nova_senha": "Diferente1!",
    }
    serializer = AlterarSenhaSerializer(data=data)
    assert not serializer.is_valid()
    assert "confirmacao_nova_senha" in serializer.errors


def test_alterar_senha_serializer_valido():
    data = {
        "senha_atual": "Antiga1!",
        "nova_senha": "NovaSenha1!",
        "confirmacao_nova_senha": "NovaSenha1!",
    }
    serializer = AlterarSenhaSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
