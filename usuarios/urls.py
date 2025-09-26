# URL configuration for the usuarios module.
from django.urls import path
from usuarios.views import LoginView, ChangePasswordView, CreateUserView

urlpatterns = [
    path('login/', LoginView.as_view(), name='usuario-login'),
    path('alterar-senha/', ChangePasswordView.as_view(), name='usuario-alterar-senha'),
    path('criar-usuario/', CreateUserView.as_view(), name='usuario-criar'),
] 