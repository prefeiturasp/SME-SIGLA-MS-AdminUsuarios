"""Configuração do app Django ``permissoes``."""

from django.apps import AppConfig


class PermissoesConfig(AppConfig):
    """App de grupos e permissões."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "permissoes"
