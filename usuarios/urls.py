# URL configuration for the usuarios module.
from django.urls import path
from usuarios.views import (
    LoginView,
    EsqueciSenhaView,
    CriarNovaSenhaView,
    CriarUsuarioView,
    PermissoesDisponiveisView,
    GerenciarPermissoesUsuarioView,
    CriarPermissaoView,
    GruposDisponiveisView,
    PermissoesGrupoView,
    CriarGrupoView,
    GerenciarUsuariosGrupoView,
    UsuariosComGruposView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='usuario-login'),
    path('esqueci-minha-senha/', EsqueciSenhaView.as_view(), name='usuario-esqueci-minha-senha'),
    path('criar-nova-senha/', CriarNovaSenhaView.as_view(), name='usuario-criar-nova-senha'),
    path('criar-usuario/', CriarUsuarioView.as_view(), name='usuario-criar'),
    path('permissoes/', PermissoesDisponiveisView.as_view(), name='permissoes-disponiveis'),
    path('usuarios/permissoes/', GerenciarPermissoesUsuarioView.as_view(), name='usuarios-gerenciar-permissoes'),
    path('permissoes/criar/', CriarPermissaoView.as_view(), name='permissoes-criar'),
    path('grupos/', GruposDisponiveisView.as_view(), name='grupos-disponiveis'),
    path('grupos/permissoes/', PermissoesGrupoView.as_view(), name='grupos-gerenciar-permissoes'),
    path('grupos/criar/', CriarGrupoView.as_view(), name='grupos-criar'),
    path('grupos/usuarios/', GerenciarUsuariosGrupoView.as_view(), name='grupos-gerenciar-usuarios'),
    path('usuarios/grupos/', UsuariosComGruposView.as_view(), name='usuarios-com-grupos'),
] 