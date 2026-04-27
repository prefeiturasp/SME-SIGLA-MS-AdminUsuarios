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
    request = rf.get("/usuarios/permissoes/")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "usuario é obrigatório"


def test_gerenciar_permissoes_usuario_not_found(rf):
    request = rf.get("/usuarios/permissoes/?usuario=naoexiste")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado"


def test_gerenciar_permissoes_usuario_success_with_group_and_direct(rf, perm_direta, perm_grupo):
    user = User.objects.create_user(username="alice", first_name="Alice", last_name="Silva", email="a@x.com")
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
    user = User.objects.create_user(username="alice")
    user.user_permissions.add(perm_direta)
    request = rf.get("/usuarios/permissoes/?usuario=alice&model=user")
    response = GerenciarPermissoesUsuarioView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_permissoes"] == 1


def test_permissoes_disponiveis_get_returns_permissions(rf, perm_direta):
    request = rf.get("/permissoes/")
    response = PermissoesDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert any(p["codename"] == perm_direta.codename for p in response.data)


def test_permissoes_disponiveis_post_creates_permission(rf, ct_user):
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
    request = rf.get("/grupos/?grupo=Inexistente")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Grupo não encontrado"


def test_grupos_disponiveis_get_all(rf):
    Group.objects.create(name="A")
    Group.objects.create(name="B")
    request = rf.get("/grupos/")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


def test_grupos_disponiveis_put_not_found(rf):
    request = rf.put("/grupos/", {"grupo": "Inexistente"}, format="json")
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_grupos_disponiveis_put_add_remove_permissions(rf, perm_direta, perm_grupo):
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
    assert set(group.permissions.values_list("codename", flat=True)) == {perm_grupo.codename}


def test_grupos_disponiveis_post_creates_group(rf, perm_direta):
    request = rf.post(
        "/grupos/",
        {"grupo": "Operadores", "permissoes_codenames": [perm_direta.codename]},
        format="json",
    )
    response = GruposDisponiveisView.as_view()(request)
    assert response.status_code == status.HTTP_201_CREATED
    group = Group.objects.get(name="Operadores")
    assert group.permissions.filter(codename=perm_direta.codename).exists()


def test_gerenciar_usuarios_grupo_group_not_found(rf):
    request = rf.put("/grupos/usuarios/", {"grupo": "X", "adicionar_usuarios": ["u"]}, format="json")
    response = GerenciarUsuariosGrupoView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Grupo não encontrado"


def test_gerenciar_usuarios_grupo_add_and_remove(rf):
    group = Group.objects.create(name="Equipe")
    u1 = User.objects.create_user(username="u1")
    u2 = User.objects.create_user(username="u2")
    group.user_set.add(u1)

    request = rf.put(
        "/grupos/usuarios/",
        {"grupo": "Equipe", "adicionar_usuarios": ["u2"], "remover_usuarios": ["u1"]},
        format="json",
    )
    response = GerenciarUsuariosGrupoView.as_view()(request)
    group.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert set(group.user_set.values_list("username", flat=True)) == {"u2"}


def test_usuarios_com_grupos_get_and_filter(rf):
    g = Group.objects.create(name="Equipe")
    u1 = User.objects.create_user(username="alice", first_name="Alice")
    u2 = User.objects.create_user(username="bob")
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
    request = rf.patch("/usuarios/grupos/", {"usuario": "naoexiste"}, format="json")
    response = UsuariosComGruposView.as_view()(request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Usuário não encontrado"


def test_usuarios_com_grupos_patch_updates_fields_and_groups(rf):
    user = User.objects.create_user(username="alice", email="old@x.com", first_name="Old")
    g1 = Group.objects.create(name="G1")
    g2 = Group.objects.create(name="G2")
    user.groups.add(g1)

    request = rf.patch(
        "/usuarios/grupos/",
        {"usuario": "alice", "nome": "Alice Silva", "email": "new@x.com", "is_active": False, "grupos": ["G2"]},
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
    User.objects.create_user(username="u1", email="same@x.com")
    User.objects.create_user(username="u2", email="u2@x.com")
    request = rf.patch("/usuarios/grupos/", {"usuario": "u2", "email": "same@x.com"}, format="json")
    response = UsuariosComGruposView.as_view()(request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data

