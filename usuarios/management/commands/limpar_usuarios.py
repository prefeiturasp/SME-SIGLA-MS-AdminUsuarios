"""
Django management command to clear non-superuser Django users.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove todos os usuários que não são superusuários"

    def handle(self, *args, **options):
        total_registros = User.objects.filter(is_superuser=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removendo {total_registros} usuários (não superusers)..."
            )
        )

        try:
            qs = User.objects.filter(is_superuser=False)
            usernames = list(qs.values_list("username", flat=True))
            qs.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {total_registros} usuários removidos com sucesso!"
                )
            )
            if usernames:
                self.stdout.write(
                    self.style.WARNING(
                        f'Usuários removidos: {", ".join(usernames)}'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro ao remover usuários: {e}")
            )
