"""
Django management command to create sample users with a fixed password.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria usuários de exemplo para desenvolvimento (senha fixa: 123456)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Número de usuários a serem criados (padrão: 5)",
        )

    def handle(self, *args, **options):
        count = options["count"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Criando {count} usuários com senha fixa 123456..."
            )
        )

        usuarios_criados = []
        usuarios_pulados = []

        for i in range(count):
            username = f"usuario{i+1}"
            email = f"{username}@example.com"
            first_name = "Usuario"
            last_name = f"{i+1}"

            if User.objects.filter(username=username).exists():
                usuarios_pulados.append(username)
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password="123456",
                first_name=first_name,
                last_name=last_name,
            )
            usuarios_criados.append(user)

            self.stdout.write(
                f"  ✓ Criado usuário: {user.username} (email: {user.email})"
            )

        self.stdout.write(self.style.SUCCESS("\nResumo:"))
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅ {len(usuarios_criados)} usuários criados."
            )
        )
        if usuarios_pulados:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️  {len(usuarios_pulados)} já existiam e foram pulados: {", ".join(usuarios_pulados)}'  # noqa: E501
                )
            )
        self.stdout.write(
            self.style.SUCCESS("Senha padrão para todos: 123456")
        )
