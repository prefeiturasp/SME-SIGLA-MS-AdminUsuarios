"""Módulo tests/test_urls."""
from __future__ import annotations
from typing import Any
import pytest
from django.urls import resolve, reverse
from usuarios.views import AlterarEmailView, CriarNovaSenhaView, CriarUsuarioView, EsqueciSenhaView, LoginView
from usuarios.views.permissoes import GerenciarPermissoesUsuarioView, GerenciarUsuariosGrupoView, GruposDisponiveisView, PermissoesDisponiveisView, UsuariosComGruposView

@pytest.mark.parametrize('route_name,view_class', [('usuario-login', LoginView), ('usuario-esqueci-minha-senha', EsqueciSenhaView), ('usuario-criar-nova-senha', CriarNovaSenhaView), ('usuario-criar', CriarUsuarioView), ('alterar-email', AlterarEmailView), ('permissoes-disponiveis', PermissoesDisponiveisView), ('grupos-disponiveis', GruposDisponiveisView), ('grupos-gerenciar-usuarios', GerenciarUsuariosGrupoView), ('usuarios-gerenciar-permissoes', GerenciarPermissoesUsuarioView), ('usuarios-com-grupos', UsuariosComGruposView)])
def test_urlpatterns_resolve_expected_views(route_name: Any, view_class: Any) -> None:
    """Verifica urlpatterns resolve expected views.
    
    Args:
        route_name: Parâmetro route name da operação.
        view_class: Parâmetro view class da operação.
    
    Returns:
        Não retorna valor.
    
    Raises:
        Nenhuma exceção específica documentada.
    """
    match = resolve(reverse(route_name))
    assert match.func.view_class is view_class  # type: ignore[attr-defined]
