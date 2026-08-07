"""Rotas de URL do módulo permissoes."""

from django.urls import path

from permissoes.api.views import (
    GerenciarPermissoesUsuarioView,
    GerenciarUsuariosGrupoView,
    GruposDisponiveisView,
    PermissoesDisponiveisView,
    UsuariosComGruposView,
)

urlpatterns = [
    path(
        "permissoes/",
        PermissoesDisponiveisView.as_view(),
        name="permissoes-disponiveis",
    ),
    path(
        "grupos/", GruposDisponiveisView.as_view(), name="grupos-disponiveis"
    ),
    path(
        "grupos/usuarios/",
        GerenciarUsuariosGrupoView.as_view(),
        name="grupos-gerenciar-usuarios",
    ),
    path(
        "usuarios/permissoes/",
        GerenciarPermissoesUsuarioView.as_view(),
        name="usuarios-gerenciar-permissoes",
    ),
    path(
        "usuarios/grupos/",
        UsuariosComGruposView.as_view(),
        name="usuarios-com-grupos",
    ),
]
