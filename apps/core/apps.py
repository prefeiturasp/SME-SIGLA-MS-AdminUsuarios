"""Configuração do app Django ``core``."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App com os blocos compartilhados entre os demais apps."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
