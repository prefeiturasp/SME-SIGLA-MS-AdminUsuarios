"""
Importa usuários a partir de uma string JSON (argumento posicional único).

Uso:
    python manage.py importar_usuarios '[{"nome":"Fulano","username":"fulano","email":"f@ex.com"}]'
"""
import json
from typing import List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


def split_nome(full_name: str) -> Tuple[str, str]:
    if not full_name:
        return "", ""
    parts = str(full_name).strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


class Command(BaseCommand):
    help = 'Importa usuários a partir de uma string JSON.'

    def add_arguments(self, parser):
        parser.add_argument('data', type=str, help='String JSON com lista de usuários')

    def handle(self, *args, **options):
        data_str = options.get('data')

        try:
            payload = json.loads(data_str)
        except Exception as exc:
            raise CommandError(f'Não foi possível ler o JSON: {exc}')

        if not isinstance(payload, list):
            raise CommandError('O JSON deve ser uma lista de objetos de usuários.')

        User = get_user_model()

        criados: List[str] = []
        pulados: List[str] = []
        erros: List[str] = []

        self.stdout.write(self.style.SUCCESS(f'Processando {len(payload)} registros...'))

        for idx, item in enumerate(payload, start=1):
            username = (item or {}).get('username')
            email = (item or {}).get('email')
            nome = (item or {}).get('nome')

            if not username or not email:
                erros.append(f'#{idx} - Faltando username/email')
                continue

            first_name, last_name = split_nome(nome)

            try:
                user = User.objects.filter(username=username).first()
                if user:
                    pulados.append(username)
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=None,  # senha não definida (unusable)
                        first_name=first_name,
                        last_name=last_name,
                    )
                    criados.append(user.username)
            except Exception as exc:
                erros.append(f"#{idx} - {username or '<sem-username>'}: {exc}")

        # Resumo
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Resumo de Importação'))
        self.stdout.write(self.style.SUCCESS(f'  ✅ Criados: {len(criados)}'))
        self.stdout.write(self.style.WARNING(f"  ↩️  Pulados (já existiam): {len(pulados)}"))
        self.stdout.write(self.style.ERROR(f'  ❌ Erros: {len(erros)}'))

        if criados:
            self.stdout.write(self.style.SUCCESS(f"  + {', '.join(criados)}"))
        if pulados:
            self.stdout.write(self.style.WARNING(f"  = {', '.join(pulados)}"))
        if erros:
            for e in erros:
                self.stdout.write(self.style.ERROR(f'    - {e}'))


