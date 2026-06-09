"""Módulo tests/test_management_commands."""
from __future__ import annotations
from typing import Any
import json
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from usuarios.management.commands.importar_usuarios import split_nome
pytestmark = pytest.mark.django_db

def test_split_nome_handles_edge_cases() -> None:
    """Verifica split nome handles edge cases."""
    assert split_nome('') == ('', '')
    assert split_nome('Maria') == ('Maria', '')
    assert split_nome('Maria da Silva') == ('Maria', 'da Silva')

def test_criar_usuarios_creates_and_skips_existing() -> None:
    """Verifica criar usuarios creates and skips existing."""
    user_model = get_user_model()
    user_model.objects.create_user(username='usuario1', email='usuario1@example.com', password='123456')
    call_command('criar_usuarios', count=3)
    created_users = user_model.objects.filter(username__in=['usuario1', 'usuario2', 'usuario3'])
    assert created_users.count() == 3
    assert user_model.objects.get(username='usuario2').check_password('123456')

def test_importar_usuarios_invalid_payload_raises() -> None:
    """Verifica importar usuarios invalid payload raises."""
    with pytest.raises(CommandError, match='Não foi possível ler o JSON'):
        call_command('importar_usuarios', 'nao-e-json')
    with pytest.raises(CommandError, match='deve ser uma lista'):
        call_command('importar_usuarios', json.dumps({'username': 'u1'}))

def test_importar_usuarios_creates_skips_and_collects_errors() -> None:
    """Verifica importar usuarios creates skips and collects errors."""
    user_model = get_user_model()
    user_model.objects.create_user(username='existente', email='existente@example.com')
    payload = [{'username': 'novo', 'email': 'novo@example.com', 'nome': 'Novo Usuario'}, {'username': 'existente', 'email': 'existente@example.com', 'nome': 'Existente'}, {'username': 'sem-email'}]
    call_command('importar_usuarios', json.dumps(payload))
    novo = user_model.objects.get(username='novo')
    assert novo.first_name == 'Novo'
    assert novo.last_name == 'Usuario'
    assert novo.has_usable_password() is False

def test_limpar_usuarios_keeps_superuser_and_deletes_regular() -> None:
    """Verifica limpar usuarios keeps superuser and deletes regular."""
    user_model = get_user_model()
    user_model.objects.create_superuser(username='admin', email='admin@example.com', password='123456')
    user_model.objects.create_user(username='u1', email='u1@example.com')
    user_model.objects.create_user(username='u2', email='u2@example.com')
    call_command('limpar_usuarios')
    assert user_model.objects.filter(username='admin').exists()
    assert not user_model.objects.filter(username__in=['u1', 'u2']).exists()

def test_load_initial_permissions_creates_groups_and_permissions(tmp_path: Any) -> None:
    """Verifica load initial permissions creates groups and permissions."""
    permissions_file = tmp_path / 'permissions.json'
    groups_file = tmp_path / 'groups.json'
    permissions_file.write_text(json.dumps([{'app_label': 'auth', 'model': 'user', 'codename': 'can_manage_users', 'name': 'Can manage users'}]), encoding='utf-8')
    groups_file.write_text(json.dumps([{'name': 'Gestores', 'permissoes': [{'app_label': 'auth', 'model': 'user', 'codename': 'can_manage_users'}, {'app_label': 'auth', 'model': 'user', 'codename': 'missing_permission'}]}]), encoding='utf-8')
    call_command('load_initial_permissions', permissions=str(permissions_file), groups=str(groups_file))
    perm = Permission.objects.get(codename='can_manage_users')
    group = Group.objects.get(name='Gestores')
    assert group.permissions.filter(pk=perm.pk).exists()
