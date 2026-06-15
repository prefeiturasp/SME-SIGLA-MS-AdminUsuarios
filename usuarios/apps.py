"""Módulo apps."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Representa UsuariosConfig."""

    default_auto_field = "django.db.backends.BigAutoField"
    name = "usuarios"
