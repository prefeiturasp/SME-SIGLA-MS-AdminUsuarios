"""Testes unitários dos repositories de permissões e grupos."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType

from permissoes.repository import (
    ContentTypeRepository,
    GroupRepository,
    PermissionRepository,
)
from usuarios.repository import UserRepository

pytestmark = pytest.mark.django_db


@pytest.fixture
def ct_user() -> ContentType:
    """ContentType do model User."""
    return ContentType.objects.get_for_model(User)


def test_content_type_obter_e_get_or_create(ct_user: ContentType) -> None:
    """Verifica consultas e get_or_create de ContentType."""
    obtido = ContentTypeRepository.obter_por_app_e_model(
        ct_user.app_label, ct_user.model.upper()
    )
    assert obtido == ct_user
    assert (
        ContentTypeRepository.obter_por_app_e_model("app", "inexistente")
        is None
    )
    exato = ContentTypeRepository.obter_por_app_e_model_exato(
        ct_user.app_label, ct_user.model
    )
    assert exato == ct_user
    criado, created = ContentTypeRepository.get_or_create(
        app_label="custom_app", model="custommodel"
    )
    assert created is True
    novamente, created2 = ContentTypeRepository.get_or_create(
        app_label="custom_app", model="custommodel"
    )
    assert created2 is False
    assert novamente.pk == criado.pk


def test_permission_criar_listar_serializar_e_existe(
    ct_user: ContentType,
) -> None:
    """Verifica CRUD básico e serialização de Permission."""
    perm = PermissionRepository.criar(
        name="Pode testar",
        codename="pode_testar",
        content_type=ct_user,
    )
    assert PermissionRepository.existe_por_content_type_e_codename(
        ct_user, "pode_testar"
    )
    assert not PermissionRepository.existe_por_content_type_e_codename(
        ct_user, "outra"
    )
    data = PermissionRepository.serializar(perm)
    assert data["codename"] == "pode_testar"
    assert data["app_label"] == ct_user.app_label
    lista = PermissionRepository.serializar_lista(
        PermissionRepository.listar_por_codenames(["pode_testar"])
    )
    assert len(lista) == 1
    assert lista[0]["codename"] == "pode_testar"
    todas = PermissionRepository.listar_todas()
    assert perm in list(todas)


def test_permission_get_or_create_e_obter_por_codename(
    ct_user: ContentType,
) -> None:
    """Verifica get_or_create e obter por codename/content_type."""
    obj, created = PermissionRepository.get_or_create(
        codename="perm_unica",
        content_type=ct_user,
        name="Única",
    )
    assert created is True
    mesmo, created2 = PermissionRepository.get_or_create(
        codename="perm_unica",
        content_type=ct_user,
        name="Outro nome",
    )
    assert created2 is False
    assert mesmo.pk == obj.pk
    obtido = PermissionRepository.obter_por_codename_e_content_type(
        codename="perm_unica",
        app_label=ct_user.app_label,
        model=ct_user.model,
    )
    assert obtido == obj
    with pytest.raises(Permission.DoesNotExist):
        PermissionRepository.obter_por_codename_e_content_type(
            codename="nao_existe",
            app_label=ct_user.app_label,
            model=ct_user.model,
        )


def test_permissoes_do_usuario_diretas_grupos_e_filtro(
    ct_user: ContentType,
) -> None:
    """Verifica união de permissões diretas/grupo e filtro por model."""
    user = UserRepository.criar(username="alice")
    perm_direta = PermissionRepository.criar(
        name="Direta",
        codename="perm_direta",
        content_type=ct_user,
    )
    perm_grupo = PermissionRepository.criar(
        name="Grupo",
        codename="perm_grupo",
        content_type=ct_user,
    )
    user.user_permissions.add(perm_direta)
    grupo = GroupRepository.criar("Admins")
    GroupRepository.adicionar_permissoes(grupo, [perm_grupo])
    GroupRepository.adicionar_usuarios(grupo, [user])
    perms = list(PermissionRepository.permissoes_do_usuario(user))
    codenames = {p.codename for p in perms}
    assert {"perm_direta", "perm_grupo"} <= codenames
    filtradas = list(
        PermissionRepository.permissoes_do_usuario(
            user, models_filter=[ct_user.model]
        )
    )
    assert {p.codename for p in filtradas} >= {"perm_direta", "perm_grupo"}
    vazias = list(
        PermissionRepository.permissoes_do_usuario(
            user, models_filter=["model_inexistente"]
        )
    )
    assert vazias == []


def test_group_listar_obter_existe_e_serializar() -> None:
    """Verifica listagem, existência e serialização de grupos."""
    g1 = GroupRepository.criar("Zebra")
    g2 = GroupRepository.criar("Alpha")
    assert GroupRepository.existe_por_nome("Alpha")
    assert not GroupRepository.existe_por_nome("Inexistente")
    assert GroupRepository.obter_por_nome("Alpha") == g2
    assert GroupRepository.obter_por_nome("X") is None
    qs = GroupRepository.listar_com_permissoes()
    assert list(qs.values_list("name", flat=True)) == ["Alpha", "Zebra"]
    filtrado = GroupRepository.listar_com_permissoes(nome="Zebra")
    assert list(filtrado) == [g1]
    data = GroupRepository.serializar(g2)
    assert data["name"] == "Alpha"
    lista = GroupRepository.serializar_lista(
        GroupRepository.listar_por_nomes(["Alpha", "Fantasma"])
    )
    assert [item["name"] for item in lista] == ["Alpha"]
    assert GroupRepository.nomes_existentes({"Alpha", "Beta"}) == {"Alpha"}


def test_group_get_or_create_salvar_e_permissoes(
    ct_user: ContentType,
) -> None:
    """Verifica get_or_create, salvar e gestão de permissões do grupo."""
    grupo, created = GroupRepository.get_or_create("Ops")
    assert created is True
    mesmo, created2 = GroupRepository.get_or_create("Ops")
    assert created2 is False
    assert mesmo.pk == grupo.pk
    p1 = PermissionRepository.criar(
        name="P1", codename="p1", content_type=ct_user
    )
    p2 = PermissionRepository.criar(
        name="P2", codename="p2", content_type=ct_user
    )
    GroupRepository.adicionar_permissoes(grupo, [p1, p2])
    assert set(grupo.permissions.values_list("codename", flat=True)) == {
        "p1",
        "p2",
    }
    GroupRepository.remover_permissoes(grupo, [p1])
    assert list(grupo.permissions.values_list("codename", flat=True)) == [
        "p2"
    ]
    GroupRepository.definir_permissoes(grupo, [p1])
    assert list(grupo.permissions.values_list("codename", flat=True)) == [
        "p1"
    ]
    GroupRepository.salvar(grupo)


def test_group_adicionar_e_remover_usuarios() -> None:
    """Verifica associação e remoção de usuários no grupo."""
    grupo = GroupRepository.criar("Equipe")
    u1 = UserRepository.criar(username="u1")
    u2 = UserRepository.criar(username="u2")
    GroupRepository.adicionar_usuarios(grupo, [u1, u2])
    assert set(grupo.user_set.values_list("username", flat=True)) == {
        "u1",
        "u2",
    }
    GroupRepository.remover_usuarios(grupo, [u2])
    assert list(grupo.user_set.values_list("username", flat=True)) == ["u1"]
