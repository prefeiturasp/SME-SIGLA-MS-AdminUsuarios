# URL configuration for the usuarios module.
from django.urls import path
from usuarios.views import (
    LoginView,
    EsqueciSenhaView,
    CriarNovaSenhaView,
    CriarUsuarioView
)

from usuarios.views.permissoes import (
    GerenciarUsuariosGrupoView,
    PermissoesDisponiveisView,
    GerenciarPermissoesUsuarioView,
     GruposDisponiveisView,    
    UsuariosComGruposView,  
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='usuario-login'),
    path('esqueci-minha-senha/', EsqueciSenhaView.as_view(), name='usuario-esqueci-minha-senha'),
    path('criar-nova-senha/', CriarNovaSenhaView.as_view(), name='usuario-criar-nova-senha'),
    path('criar-usuario/', CriarUsuarioView.as_view(), name='usuario-criar'),    

    path('permissoes/', PermissoesDisponiveisView.as_view(), name='permissoes-disponiveis'), 

    path('grupos/', GruposDisponiveisView.as_view(), name='grupos-disponiveis'), 
    path('grupos/usuarios/', GerenciarUsuariosGrupoView.as_view(), name='grupos-gerenciar-usuarios'),      

    path('usuarios/permissoes/', GerenciarPermissoesUsuarioView.as_view(), name='usuarios-gerenciar-permissoes'),
    path('usuarios/grupos/', UsuariosComGruposView.as_view(), name='usuarios-com-grupos'),
    
    
] 
 