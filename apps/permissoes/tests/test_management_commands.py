"""Módulo tests/test_management_commands."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_load_initial_permissions_creates_groups_and_permissions(tmp_path):
    """Verifica load initial permissions creates groups and permissions."""
    permissions_file = tmp_path / "permissions.json"
    groups_file = tmp_path / "groups.json"
    permissions_file.write_text(
        json.dumps(
            [
                {
                    "app_label": "auth",
                    "model": "user",
                    "codename": "can_manage_users",
                    "name": "Can manage users",
                }
            ]
        ),
        encoding="utf-8",
    )
    groups_file.write_text(
        json.dumps(
            [
                {
                    "name": "Gestores",
                    "permissoes": [
                        {
                            "app_label": "auth",
                            "model": "user",
                            "codename": "can_manage_users",
                        },
                        {
                            "app_label": "auth",
                            "model": "user",
                            "codename": "missing_permission",
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    call_command(
        "load_initial_permissions",
        permissions=str(permissions_file),
        groups=str(groups_file),
    )
    perm = Permission.objects.get(codename="can_manage_users")
    group = Group.objects.get(name="Gestores")
    assert group.permissions.filter(pk=perm.pk).exists()
