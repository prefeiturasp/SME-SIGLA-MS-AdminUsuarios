import pytest
from django.urls import resolve, reverse

from usuarios.views import CriarNovaSenhaView, CriarUsuarioView, EsqueciSenhaView, LoginView
from usuarios.views.permissoes import (
    GerenciarPermissoesUsuarioView,
    GerenciarUsuariosGrupoView,
    GruposDisponiveisView,
    PermissoesDisponiveisView,
    UsuariosComGruposView,
)


@pytest.mark.parametrize(
    "route_name,view_class",
    [
        ("usuario-login", LoginView),
        ("usuario-esqueci-minha-senha", EsqueciSenhaView),
        ("usuario-criar-nova-senha", CriarNovaSenhaView),
        ("usuario-criar", CriarUsuarioView),
        ("permissoes-disponiveis", PermissoesDisponiveisView),
        ("grupos-disponiveis", GruposDisponiveisView),
        ("grupos-gerenciar-usuarios", GerenciarUsuariosGrupoView),
        ("usuarios-gerenciar-permissoes", GerenciarPermissoesUsuarioView),
        ("usuarios-com-grupos", UsuariosComGruposView),
    ],
)
def test_urlpatterns_resolve_expected_views(route_name, view_class):
    match = resolve(reverse(route_name))
    assert match.func.view_class is view_class
