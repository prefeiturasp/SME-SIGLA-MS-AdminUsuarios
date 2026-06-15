"""Módulo tests/test_permissoes_views."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIRequestFactory

from usuarios.views.permissoes import (
    GerenciarPermissoesUsuarioView,
    GerenciarUsuariosGrupoView,
    GruposDisponiveisView,
    PermissoesDisponiveisView,
    UsuariosComGruposView,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def rf():
    return APIRequestFactory()


@pytest.fixture
def ct_user():
    return ContentType.objects.get_for_model(User)


@pytest.fixture
def perm_direta(ct_user):
    return Permission.objects.create(
        codename="pode_ver_dashboard",
        name="Pode ver dashboard",
        content_type=ct_user,
    )


@pytest.fixture
def perm_grupo(ct_user):
    return Permission.objects.create(
        codename="pode_editar_grupo",
        name="Pode editar grupo",
        content_type=ct_user,
    )


def test_gerenciar_permissoes_usuario_requires_param(rf):
    """Verifica gerenciar permissoes usuario requires param."""
    request = rf.get("/usuarios/permissoes/")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "usuario é obrigatório"


def test_gerenciar_permissoes_usuario_not_found(rf):
    """Verifica gerenciar permissoes usuario not found."""
    request = rf.get("/usuarios/permissoes/?usuario=naoexiste")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado"


def test_gerenciar_permissoes_usuario_success_with_group_and_direct(
    rf, perm_direta, perm_grupo
):
    """Verifica gerenciar permissoes usuario success with group and direct."""
    user = User.objects.create_user(
        username="alice",
        first_name="Alice",
        last_name="Silva",
        email="a@x.com",
    )
    user.user_permissions.add(perm_direta)
    grupo = Group.objects.create(name="Admins")
    grupo.permissions.add(perm_grupo)
    user.groups.add(grupo)
    request = rf.get("/usuarios/permissoes/?usuario=alice")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["usuario"] == "alice"
    assert response.data["nome"] == "Alice Silva"
    assert response.data["total_permissoes"] == 2
    assert set(response.data["grupos"]) == {"Admins"}


def test_gerenciar_permissoes_usuario_filters_model(rf, perm_direta):
    """Verifica gerenciar permissoes usuario filters model."""
    user = User.objects.create_user(username="alice")
    user.user_permissions.add(perm_direta)
    request = rf.get("/usuarios/permissoes/?usuario=alice&model=user")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_permissoes"] == 1


def test_permissoes_disponiveis_get_returns_permissions(rf, perm_direta):
    """Verifica permissoes disponiveis get returns permissions."""
    request = rf.get("/permissoes/")
    response = PermissoesDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert any(p["codename"] == perm_direta.codename for p in response.data)


def test_permissoes_disponiveis_post_creates_permission(rf, ct_user):
    """Verifica permissoes disponiveis post creates permission."""
    request = rf.post(
        "/permissoes/",
        {
            "app_label": ct_user.app_label,
            "model": ct_user.model,
            "codename": "pode_exportar",
            "name": "Pode exportar",
        },
        format="json",
    )
    response = PermissoesDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["codename"] == "pode_exportar"


def test_grupos_disponiveis_get_not_found_by_name(rf):
    """Verifica grupos disponiveis get not found by name."""
    request = rf.get("/grupos/?grupo=Inexistente")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Grupo não encontrado"


def test_grupos_disponiveis_get_all(rf):
    """Verifica grupos disponiveis get all."""
    Group.objects.create(name="A")
    Group.objects.create(name="B")
    request = rf.get("/grupos/")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


def test_grupos_disponiveis_put_not_found(rf):
    """Verifica grupos disponiveis put not found."""
    request = rf.put("/grupos/", {"grupo": "Inexistente"}, format="json")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_grupos_disponiveis_put_add_remove_permissions(
    rf, perm_direta, perm_grupo
):
    """Verifica grupos disponiveis put add remove permissions."""
    group = Group.objects.create(name="Gestores")
    group.permissions.add(perm_direta)
    request = rf.put(
        "/grupos/",
        {
            "grupo": "Gestores",
            "adicionar_codenames": [perm_grupo.codename],
            "remover_codenames": [perm_direta.codename],
        },
        format="json",
    )
    response = GruposDisponiveisView.as_view()(request)
    group.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert set(group.permissions.values_list("codename", flat=True)) == {
        perm_grupo.codename
    }


def test_grupos_disponiveis_post_creates_group(rf, perm_direta):
    """Verifica grupos disponiveis post creates group."""
    request = rf.post(
        "/grupos/",
        {
            "grupo": "Operadores",
            "permissoes_codenames": [perm_direta.codename],
        },
        format="json",
    )
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_201_CREATED
    group = Group.objects.get(name="Operadores")
    assert group.permissions.filter(codename=perm_direta.codename).exists()


def test_gerenciar_usuarios_grupo_group_not_found(rf):
    """Verifica gerenciar usuarios grupo group not found."""
    request = rf.put(
        "/grupos/usuarios/",
        {"grupo": "X", "adicionar_usuarios": ["u"]},
        format="json",
    )
    response = GerenciarUsuariosGrupoView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Grupo não encontrado"


def test_gerenciar_usuarios_grupo_add_and_remove(rf):
    """Verifica gerenciar usuarios grupo add and remove."""
    group = Group.objects.create(name="Equipe")
    u1 = User.objects.create_user(username="u1")
    User.objects.create_user(username="u2")
    group.user_set.add(u1)
    request = rf.put(
        "/grupos/usuarios/",
        {
            "grupo": "Equipe",
            "adicionar_usuarios": ["u2"],
            "remover_usuarios": ["u1"],
        },
        format="json",
    )
    response = GerenciarUsuariosGrupoView.as_view()(request)
    group.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert set(group.user_set.values_list("username", flat=True)) == {"u2"}


def test_usuarios_com_grupos_get_and_filter(rf):
    """Verifica usuarios com grupos get and filter."""
    g = Group.objects.create(name="Equipe")
    u1 = User.objects.create_user(username="alice", first_name="Alice")
    User.objects.create_user(username="bob")
    u1.groups.add(g)
    all_request = rf.get("/usuarios/grupos/")
    all_response = UsuariosComGruposView.as_view()(all_request)
    assert all_response.status_code == status.HTTP_200_OK
    assert all_response.data["count"] == 2
    filtered_request = rf.get("/usuarios/grupos/?usuario=ali")
    filtered_response = UsuariosComGruposView.as_view()(filtered_request)
    assert filtered_response.status_code == status.HTTP_200_OK
    assert filtered_response.data["count"] == 1
    assert filtered_response.data["results"][0]["usuario"] == "alice"


def test_usuarios_com_grupos_patch_user_not_found(rf):
    """Verifica usuarios com grupos patch user not found."""
    request = rf.patch(
        "/usuarios/grupos/", {"usuario": "naoexiste"}, format="json"
    )
    response = UsuariosComGruposView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado"


def test_usuarios_com_grupos_patch_updates_fields_and_groups(rf, monkeypatch):
    """Verifica usuarios com grupos patch updates fields and groups."""
    monkeypatch.setattr(
        "usuarios.views.permissoes.SmeIntegracaoService.alterar_email",
        lambda *_a, **_k: "OK",
    )
    user = User.objects.create_user(
        username="alice", email="old@x.com", first_name="Old"
    )
    g1 = Group.objects.create(name="G1")
    Group.objects.create(name="G2")
    user.groups.add(g1)
    request = rf.patch(
        "/usuarios/grupos/",
        {
            "usuario": "alice",
            "nome": "Alice Silva",
            "email": "new@x.com",
            "is_active": False,
            "grupos": ["G2"],
        },
        format="json",
    )
    response = UsuariosComGruposView.as_view()(request)
    user.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert user.first_name == "Alice"
    assert user.last_name == "Silva"
    assert user.email == "new@x.com"
    assert user.is_active is False
    assert set(user.groups.values_list("name", flat=True)) == {"G2"}


def test_usuarios_com_grupos_patch_email_unique_validation(rf):
    """Verifica usuarios com grupos patch email unique validation."""
    User.objects.create_user(username="u1", email="same@x.com")
    User.objects.create_user(username="u2", email="u2@x.com")
    request = rf.patch(
        "/usuarios/grupos/",
        {"usuario": "u2", "email": "same@x.com"},
        format="json",
    )
    response = UsuariosComGruposView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


def test_patch_email_diferente_chama_sme_e_salva(rf, monkeypatch):
    """Verifica patch email diferente chama sme e salva."""
    user = User.objects.create_user(username="alice", email="old@x.com")
    chamadas = {"n": 0}

    def _ok(*_a, **_k):
        """Ok."""
        chamadas["n"] += 1
        return "OK"

    monkeypatch.setattr(
        "usuarios.views.permissoes.SmeIntegracaoService.alterar_email", _ok
    )
    request = rf.patch(
        "/usuarios/grupos/",
        {"usuario": "alice", "email": "new@x.com"},
        format="json",
    )
    response = UsuariosComGruposView.as_view()(request)
    user.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert user.email == "new@x.com"
    assert chamadas["n"] == 1


def test_patch_email_igual_nao_chama_sme(rf, monkeypatch):
    """Verifica patch email igual nao chama sme."""
    User.objects.create_user(username="alice", email="same@x.com")
    chamadas = {"n": 0}

    def _spy(*_a, **_k):
        """Spy."""
        chamadas["n"] += 1
        return "OK"

    monkeypatch.setattr(
        "usuarios.views.permissoes.SmeIntegracaoService.alterar_email", _spy
    )
    request = rf.patch(
        "/usuarios/grupos/",
        {"usuario": "alice", "email": "SAME@x.com"},
        format="json",
    )
    response = UsuariosComGruposView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert chamadas["n"] == 0


def test_patch_email_sme_falha_retorna_400_e_nao_salva(rf, monkeypatch):
    """Verifica patch email sme falha retorna 400 e nao salva."""
    from usuarios.exceptions import SmeIntegracaoException

    user = User.objects.create_user(username="alice", email="old@x.com")

    def _raise(*_a, **_k):
        """Raise."""
        raise SmeIntegracaoException("email recusado")

    monkeypatch.setattr(
        "usuarios.views.permissoes.SmeIntegracaoService.alterar_email", _raise
    )
    request = rf.patch(
        "/usuarios/grupos/",
        {"usuario": "alice", "email": "new@x.com"},
        format="json",
    )
    response = UsuariosComGruposView.as_view()(request)
    user.refresh_from_db()
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email recusado" in response.data["detail"]
    assert user.email == "old@x.com"
