"""Módulo management/commands/load_initial_permissions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from permissoes.repository import (
    ContentTypeRepository,
    GroupRepository,
    PermissionRepository,
)

_JSON_DIR = Path(__file__).resolve().parent / "json"


class Command(BaseCommand):
    """Representa Command."""

    help = "Carrega permissões e grupos iniciais a partir dos arquivos JSON"

    def add_arguments(self, parser: Any) -> None:
        """Registra os argumentos da linha de comando."""
        parser.add_argument(
            "--permissions",
            type=str,
            default=str(_JSON_DIR / "permissions.json"),
            help="Caminho do arquivo JSON de permissões",
        )
        parser.add_argument(
            "--groups",
            type=str,
            default=str(_JSON_DIR / "groups.json"),
            help="Caminho do arquivo JSON de grupos",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Roda a lógica principal do comando."""
        permissions_file = options["permissions"]
        groups_file = options["groups"]
        self.stdout.write(
            self.style.MIGRATE_HEADING("🧩 Carregando permissões iniciais...")
        )
        with open(permissions_file, encoding="utf-8") as f:
            permissions_data = json.load(f)
        for perm in permissions_data:
            app_label = perm["app_label"]
            model = perm["model"]
            content_type, _ = ContentTypeRepository.get_or_create(
                app_label=app_label, model=model
            )
            obj, created = PermissionRepository.get_or_create(
                codename=perm["codename"],
                content_type=content_type,
                name=perm["name"],
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Criada permissão {obj.codename}")
                )
            else:
                self.stdout.write(f"↻ Permissão já existe: {obj.codename}")
        self.stdout.write(
            self.style.MIGRATE_HEADING("\n👥 Carregando grupos...")
        )
        with open(groups_file, encoding="utf-8") as f:
            groups_data = json.load(f)
        for group_data in groups_data:
            group, _ = GroupRepository.get_or_create(group_data["name"])
            perms = []
            for p in group_data["permissoes"]:
                try:
                    perm = (
                        PermissionRepository.obter_por_codename_e_content_type(
                            codename=p["codename"],
                            app_label=p["app_label"],
                            model=p["model"],
                        )
                    )
                    perms.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ Permissão não encontrada: {p['codename']}"
                        )
                    )
            GroupRepository.definir_permissoes(group, perms)
            GroupRepository.salvar(group)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Grupo '{group.name}' atualizado com {len(perms)} permissões."  # noqa: E501
                )
            )
        self.stdout.write(
            self.style.SUCCESS("\n🎯 Carga inicial concluída com sucesso!")
        )
