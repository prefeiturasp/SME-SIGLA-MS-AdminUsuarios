# URL configuration for the usuarios module.
from django.urls import path
from usuarios.views import LoginView, EsqueciSenhaView, CriarNovaSenhaView

urlpatterns = [
    path('login/', LoginView.as_view(), name='usuario-login'),
    path('esqueci-minha-senha/', EsqueciSenhaView.as_view(), name='usuario-esqueci-minha-senha'),
    path('criar-nova-senha/', CriarNovaSenhaView.as_view(), name='usuario-criar-nova-senha'),
    # path('criar-usuario/', CreateUserView.as_view(), name='usuario-criar'),
] 