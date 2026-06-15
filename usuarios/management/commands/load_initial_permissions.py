"""Módulo management/commands/load_initial_permissions."""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    """Representa Command."""

    help = "Carrega permissões e grupos iniciais a partir dos arquivos JSON"

    def add_arguments(self, parser: Any) -> None:
        """Registra os argumentos da linha de comando."""
        parser.add_argument(
            "--permissions",
            type=str,
            default="usuarios/management/commands/json/permissions.json",
            help="Caminho do arquivo JSON de permissões",
        )
        parser.add_argument(
            "--groups",
            type=str,
            default="usuarios/management/commands/json/groups.json",
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
            content_type, _ = ContentType.objects.get_or_create(
                app_label=app_label, model=model
            )
            obj, created = Permission.objects.get_or_create(
                codename=perm["codename"],
                content_type=content_type,
                defaults={"name": perm["name"]},
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
            group, _ = Group.objects.get_or_create(name=group_data["name"])
            perms = []
            for p in group_data["permissoes"]:
                try:
                    perm = Permission.objects.get(
                        codename=p["codename"],
                        content_type__app_label=p["app_label"],
                        content_type__model=p["model"],
                    )
                    perms.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️ Permissão não encontrada: {p['codename']}'
                        )
                    )
            group.permissions.set(perms)
            group.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Grupo '{group.name}' atualizado com {len(perms)} permissões."  # noqa: E501
                )
            )
        self.stdout.write(
            self.style.SUCCESS("\n🎯 Carga inicial concluída com sucesso!")
        )
