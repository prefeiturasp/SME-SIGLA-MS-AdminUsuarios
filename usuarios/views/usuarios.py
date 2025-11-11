"""
DRF views for the usuarios module.
"""

import logging
from typing import dataclass_transform
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType

from usuarios.serializers import (
    
    LoginSerializer,
    LoginResponseSerializer,
    EsqueciSenhaSerializer,
    CriarNovaSenhaSerializer,
    CreateUserSerializer,
)
from usuarios.services.autenticacao import AutenticacaoService
from usuarios.services.sme_integracao import SmeIntegracaoService
from usuarios.services.email import EmailService
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from usuarios.exceptions import (
    AutenticacaoRespostaInvalidaError,
    AutenticacaoRequisicaoError,
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoUpstreamError,
    SmeIntegracaoException,
)

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    try:
        local, domain = email.split('@', 1)
    except ValueError:
        return '***'
    if not local:
        return f"***@{domain}"
    if len(local) <= 2:
        masked_local = local[0] + '*' * max(1, len(local) - 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"

class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginSerializer        
    )
    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = User.objects.filter(username=serializer.validated_data['usuario']).first()
        if not usuario:
            return Response({'detail': 'Usuário não encontrado'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            data = AutenticacaoService.autentica(
                serializer.validated_data['usuario'],
                serializer.validated_data['senha']
            )
        except AutenticacaoCredenciaisInvalidasError:
            return Response({'detail': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
        except (AutenticacaoRespostaInvalidaError, AutenticacaoUpstreamError, AutenticacaoRequisicaoError):
            return Response({'detail': 'Falha no serviço de autenticação'}, status=status.HTTP_400_BAD_REQUEST)

        response_data = AutenticacaoService.montar_resposta_login(data, usuario)
        return Response(response_data, status=status.HTTP_200_OK)


class EsqueciSenhaView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = EsqueciSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data['rf']
        user = User.objects.filter(username=usuario).first()
        if not user:
            return Response({'detail': 'Usuário não encontrado'}, status=status.HTTP_404_NOT_FOUND)
        try:
            info = SmeIntegracaoService.informacao_usuario(usuario)
        except Exception:
            return Response({'detail': 'Falha ao consultar dados do usuário'}, status=status.HTTP_400_BAD_REQUEST)

        email = (info or {}).get('Email') or (info or {}).get('email')
        nome = (info or {}).get('Nome') or (info or {}).get('nome') or user.first_name
        if not email:
            return Response({'detail': 'E-mail não encontrado para o usuário'}, status=status.HTTP_404_NOT_FOUND)

        try:
            EmailService.enviar_email_esqueci_senha(
                user=user,
                email=email,
                nome=nome
            )
        except Exception:
            return Response({'detail': 'Falha ao enviar e-mail'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'usuario': user.username, 'email': _mask_email(email), 'email_enviado': True}, status=status.HTTP_200_OK)


class CriarNovaSenhaView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CriarNovaSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        nova_senha = serializer.validated_data['nova_senha']

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({'detail': 'UID inválido'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'detail': 'Token inválido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            SmeIntegracaoService.redefine_senha(user.username, nova_senha)
        except SmeIntegracaoException as e:
            logger.error(f"Falha ao redefinir senha no SME Integração: {e}")
            return Response({'detail': 'Falha ao redefinir senha no SME Integração'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nova_senha)
        user.save(update_fields=['password'])

        return Response({'detail': 'Senha alterada com sucesso'}, status=status.HTTP_200_OK)


class CriarUsuarioView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=CreateUserSerializer,
        responses={
            201: OpenApiResponse(
                description="Usuário criado com sucesso"
            ),
            400: OpenApiResponse(description="Dados inválidos"),
            409: OpenApiResponse(description="Usuário já cadastrado"),
        },
        description="Cria um novo usuário, verificando se o nome de usuário ou e-mail já estão em uso."
    )
    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data.get("username")
        email = serializer.validated_data.get("email")

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Nome de usuário já está cadastrado."},
                status=status.HTTP_409_CONFLICT,
            )

        if email and User.objects.filter(email=email).exists():
            return Response(
                {"detail": "E-mail já está cadastrado."},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.create_user(**serializer.validated_data)

        return Response(
            {"detail": "Usuário criado com sucesso", "user": user.username},
            status=status.HTTP_201_CREATED,
        )

