"""Módulo tests/test_urls."""

from __future__ import annotations

import pytest
from django.urls import resolve, reverse

from permissoes.api.views import (
    GerenciarPermissoesUsuarioView,
    GerenciarUsuariosGrupoView,
    GruposDisponiveisView,
    PermissoesDisponiveisView,
    UsuariosComGruposView,
)
from usuarios.api.views import (
    AlterarEmailView,
    CriarNovaSenhaView,
    CriarUsuarioView,
    EsqueciSenhaView,
    LoginView,
)


@pytest.mark.parametrize(
    "route_name,view_class",
    [
        ("usuario-login", LoginView),
        ("usuario-esqueci-minha-senha", EsqueciSenhaView),
        ("usuario-criar-nova-senha", CriarNovaSenhaView),
        ("usuario-criar", CriarUsuarioView),
        ("alterar-email", AlterarEmailView),
        ("permissoes-disponiveis", PermissoesDisponiveisView),
        ("grupos-disponiveis", GruposDisponiveisView),
        ("grupos-gerenciar-usuarios", GerenciarUsuariosGrupoView),
        ("usuarios-gerenciar-permissoes", GerenciarPermissoesUsuarioView),
        ("usuarios-com-grupos", UsuariosComGruposView),
    ],
)
def test_urlpatterns_resolve_expected_views(route_name, view_class):
    """Verifica urlpatterns resolve expected views."""
    match = resolve(reverse(route_name))
    assert match.func.view_class is view_class
