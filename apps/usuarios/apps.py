"""Configuração do app Django ``usuarios``."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """App de autenticação e cadastro de usuários."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
