"""Rotas de URL do módulo usuarios."""

from django.urls import path

from usuarios.api.views import (
    AlterarEmailView,
    AlterarSenhaView,
    BuscarUsuarioEolView,
    CriarNovaSenhaView,
    CriarUsuarioView,
    EsqueciSenhaView,
    LoginView,
    MeusDadosView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="usuario-login"),
    path(
        "esqueci-minha-senha/",
        EsqueciSenhaView.as_view(),
        name="usuario-esqueci-minha-senha",
    ),
    path(
        "criar-nova-senha/",
        CriarNovaSenhaView.as_view(),
        name="usuario-criar-nova-senha",
    ),
    path("criar-usuario/", CriarUsuarioView.as_view(), name="usuario-criar"),
    path(
        "buscar-usuario-eol/",
        BuscarUsuarioEolView.as_view(),
        name="buscar-usuario-eol",
    ),
    path("meus-dados/", MeusDadosView.as_view(), name="meus-dados"),
    path("alterar-senha/", AlterarSenhaView.as_view(), name="alterar-senha"),
    path("alterar-email/", AlterarEmailView.as_view(), name="alterar-email"),
]
