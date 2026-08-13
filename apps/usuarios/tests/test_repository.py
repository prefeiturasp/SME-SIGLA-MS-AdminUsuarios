"""Testes unitários do UserRepository."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from rest_framework import serializers

from usuarios.repository import UserRepository

pytestmark = pytest.mark.django_db


class _UserMiniSerializer(serializers.ModelSerializer):
    """Serializer mínimo para testar serializar/serializar_lista."""

    class Meta:
        """Representa Meta."""

        model = User
        fields = ["id", "username", "email"]


def test_serializar_e_serializar_lista() -> None:
    """Verifica serializar item e lista via serializer informado."""
    u1 = UserRepository.criar(username="a", email="a@x.com")
    u2 = UserRepository.criar(username="b", email="b@x.com")
    data = UserRepository.serializar(u1, _UserMiniSerializer)
    assert data["username"] == "a"
    assert data["email"] == "a@x.com"
    lista = UserRepository.serializar_lista(
        UserRepository.buscar_todos().order_by("username"),
        _UserMiniSerializer,
    )
    assert [item["username"] for item in lista] == ["a", "b"]
    assert u2.username == "b"


def test_buscar_todos_e_listar_com_grupos() -> None:
    """Verifica buscar_todos e filtro de listar_com_grupos."""
    UserRepository.criar(username="alice")
    UserRepository.criar(username="bob")
    assert UserRepository.buscar_todos().count() == 2
    filtrado = UserRepository.listar_com_grupos(username_filtro="ali")
    assert list(filtrado.values_list("username", flat=True)) == ["alice"]
    todos = UserRepository.listar_com_grupos()
    assert todos.count() == 2


def test_obter_por_username_variantes() -> None:
    """Verifica obter por username, com grupos e apenas id."""
    user = UserRepository.criar(username="rf1", email="rf1@x.com")
    grupo = Group.objects.create(name="Gestor")
    UserRepository.adicionar_grupos(user, [grupo])
    assert UserRepository.obter_por_username("rf1") == user
    assert UserRepository.obter_por_username("inexistente") is None
    com_grupos = UserRepository.obter_por_username_com_grupos("rf1")
    assert com_grupos is not None
    assert list(com_grupos.groups.values_list("name", flat=True)) == [
        "Gestor"
    ]
    apenas_id = UserRepository.obter_por_username_apenas_id("rf1")
    assert apenas_id is not None
    assert apenas_id.id == user.id
    assert UserRepository.obter_por_pk(user.pk) == user


def test_existe_username_email_e_outro_usuario() -> None:
    """Verifica checagens de existência de username e e-mail."""
    user = UserRepository.criar(username="u1", email="U1@X.com")
    assert UserRepository.existe_por_username("u1") is True
    assert UserRepository.existe_por_username("outro") is False
    assert UserRepository.existe_por_email("u1@x.com") is True
    assert UserRepository.existe_por_email("livre@x.com") is False
    assert (
        UserRepository.existe_email_em_outro_usuario("u1@x.com", user.id)
        is False
    )
    UserRepository.criar(username="u2", email="outro@x.com")
    assert (
        UserRepository.existe_email_em_outro_usuario("outro@x.com", user.id)
        is True
    )
    assert (
        UserRepository.existe_email_em_outro_usuario("livre@x.com", None)
        is False
    )


def test_criar_salvar_e_listar_por_usernames() -> None:
    """Verifica criar, salvar e listar por usernames."""
    user = UserRepository.criar(
        username="novo",
        email="novo@x.com",
        first_name="Novo",
        last_name="User",
        password="123456",
    )
    assert user.check_password("123456")
    user.email = "atualizado@x.com"
    UserRepository.salvar(user, campos_atualizacao=["email"])
    user.refresh_from_db()
    assert user.email == "atualizado@x.com"
    user.first_name = "Nome"
    UserRepository.salvar(user)
    user.refresh_from_db()
    assert user.first_name == "Nome"
    UserRepository.criar(username="outro")
    qs = UserRepository.listar_por_usernames(["novo", "fantasma"])
    assert list(qs.values_list("username", flat=True)) == ["novo"]


def test_nao_superusers_contar_filtrar_excluir() -> None:
    """Verifica filtrar/contar/excluir usuários não superuser."""
    User.objects.create_superuser(
        username="admin", email="a@x.com", password="x"
    )
    UserRepository.criar(username="comum1")
    UserRepository.criar(username="comum2")
    assert UserRepository.contar_nao_superusers() == 2
    qs = UserRepository.filtrar_nao_superusers()
    assert set(qs.values_list("username", flat=True)) == {
        "comum1",
        "comum2",
    }
    UserRepository.excluir_queryset(qs)
    assert UserRepository.contar_nao_superusers() == 0
    assert User.objects.filter(username="admin").exists()


def test_grupos_adicionar_remover_e_nomes() -> None:
    """Verifica associação de grupos e listagem de nomes."""
    user = UserRepository.criar(username="u")
    g1 = Group.objects.create(name="Beta")
    g2 = Group.objects.create(name="Alpha")
    UserRepository.adicionar_grupos(user, [g1, g2])
    assert UserRepository.nomes_grupos(user) == ["Alpha", "Beta"]
    assert set(UserRepository.nomes_grupos_sem_ordem(user)) == {
        "Alpha",
        "Beta",
    }
    UserRepository.remover_grupos(user, [g1])
    assert UserRepository.nomes_grupos(user) == ["Alpha"]
