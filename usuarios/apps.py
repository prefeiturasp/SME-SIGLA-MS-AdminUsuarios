"""Módulo apps."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Define UsuariosConfig."""

    default_auto_field = "django.db.backends.BigAutoField"
    name = "usuarios"
