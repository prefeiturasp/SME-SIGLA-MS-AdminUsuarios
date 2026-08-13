"""Módulo tests/test_management_commands."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from usuarios.management.commands.importar_usuarios import split_nome
from usuarios.repository import UserRepository

pytestmark = pytest.mark.django_db


def test_split_nome_handles_edge_cases():
    """Verifica split nome handles edge cases."""
    assert split_nome("") == ("", "")
    assert split_nome("Maria") == ("Maria", "")
    assert split_nome("Maria da Silva") == ("Maria", "da Silva")


def test_criar_usuarios_creates_and_skips_existing():
    """Verifica criar usuarios creates and skips existing."""
    UserRepository.criar(
        username="usuario1", email="usuario1@example.com", password="123456"
    )
    call_command("criar_usuarios", count=3)
    user_model = get_user_model()
    created_users = user_model.objects.filter(
        username__in=["usuario1", "usuario2", "usuario3"]
    )
    assert created_users.count() == 3
    assert UserRepository.obter_por_username("usuario2").check_password(
        "123456"
    )


def test_importar_usuarios_invalid_payload_raises():
    """Verifica importar usuarios invalid payload raises."""
    with pytest.raises(CommandError, match="Não foi possível ler o JSON"):
        call_command("importar_usuarios", "nao-e-json")
    with pytest.raises(CommandError, match="deve ser uma lista"):
        call_command("importar_usuarios", json.dumps({"username": "u1"}))


def test_importar_usuarios_creates_skips_and_collects_errors():
    """Verifica importar usuarios creates skips and collects errors."""
    UserRepository.criar(
        username="existente", email="existente@example.com"
    )
    payload = [
        {
            "username": "novo",
            "email": "novo@example.com",
            "nome": "Novo Usuario",
        },
        {
            "username": "existente",
            "email": "existente@example.com",
            "nome": "Existente",
        },
        {"username": "sem-email"},
    ]
    call_command("importar_usuarios", json.dumps(payload))
    novo = UserRepository.obter_por_username("novo")
    assert novo is not None
    assert novo.first_name == "Novo"
    assert novo.last_name == "Usuario"
    assert novo.has_usable_password() is False


def test_limpar_usuarios_keeps_superuser_and_deletes_regular():
    """Verifica limpar usuarios keeps superuser and deletes regular."""
    user_model = get_user_model()
    user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="123456"
    )
    UserRepository.criar(username="u1", email="u1@example.com")
    UserRepository.criar(username="u2", email="u2@example.com")
    call_command("limpar_usuarios")
    assert UserRepository.existe_por_username("admin")
    assert not UserRepository.existe_por_username("u1")
    assert not UserRepository.existe_por_username("u2")
