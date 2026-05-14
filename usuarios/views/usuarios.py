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
    AlterarSenhaSerializer,
    CreateUserSerializer,
    BuscarUsuarioEolSerializer,
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

        # Atualiza nome/email do usuário local com dados retornados da autenticação
        AutenticacaoService.atualizar_usuario_com_dados_autenticacao(user=usuario, dados=data, senha=serializer.validated_data['senha'])
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


class MeusDadosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        nome_completo = f"{user.first_name} {user.last_name}".strip()
        grupos = list(user.groups.values_list('name', flat=True))
        return Response({
            'rf': user.username,
            'nome_completo': nome_completo,
            'email': user.email,
            'perfil_acesso': grupos,
        }, status=status.HTTP_200_OK)


class AlterarSenhaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AlterarSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        senha_atual = serializer.validated_data['senha_atual']
        nova_senha = serializer.validated_data['nova_senha']

        if not user.check_password(senha_atual):
            return Response({'detail': 'Senha atual incorreta.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            SmeIntegracaoService.redefine_senha(user.username, nova_senha)
        except SmeIntegracaoException as e:
            logger.error(f"Falha ao redefinir senha no SME Integração: {e}")               
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nova_senha)
        user.save(update_fields=['password'])

        return Response({'detail': 'Senha alterada com sucesso'}, status=status.HTTP_200_OK)


class BuscarUsuarioEolView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=BuscarUsuarioEolSerializer,
        responses={
            200: OpenApiResponse(description="Dados do usuário no EOL"),
            400: OpenApiResponse(description="Usuário já cadastrado no SIGLA"),
            404: OpenApiResponse(description="Usuário não encontrado no EOL")
        },
        description="Busca dados do usuário no EOL via RF. Retorna 400 se já existir no SIGLA."
    )
    def post(self, request):
        serializer = BuscarUsuarioEolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rf = serializer.validated_data['rf']

        if User.objects.filter(username=rf).exists():
            return Response(
                {'detail': 'Usuário já cadastrado no SIGLA.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            info = SmeIntegracaoService.informacao_usuario(rf)
        except SmeIntegracaoException:
            return Response(
                {'detail': 'Usuário não encontrado no EOL.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Falha ao consultar EOL para RF: %s", rf)
            return Response(
                {'detail': 'Falha ao consultar o EOL.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nome = (info or {}).get('Nome') or (info or {}).get('nome', '')
        email = (info or {}).get('Email') or (info or {}).get('email', '')

        if not nome and not email:
            return Response(
                {'detail': 'Usuário não encontrado no EOL.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'username': rf, 'nome': nome, 'email': email}, status=status.HTTP_200_OK)


class CriarUsuarioView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=CreateUserSerializer,
        responses={
            201: OpenApiResponse(description="Usuário criado com sucesso"),
            400: OpenApiResponse(description="Dados inválidos"),
            409: OpenApiResponse(description="Usuário já cadastrado"),
        },
        description="Cria um novo usuário a partir de username, nome e email."
    )
    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        nome = serializer.validated_data['nome']

        if User.objects.filter(username=username).exists():
            return Response(
                {'detail': 'Nome de usuário já está cadastrado.'},
                status=status.HTTP_409_CONFLICT,
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'E-mail já está cadastrado.'},
                status=status.HTTP_409_CONFLICT,
            )

        partes = nome.strip().split(' ', 1)
        first_name = partes[0]
        last_name = partes[1] if len(partes) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        return Response(
            {'detail': 'Usuário criado com sucesso', 'user': user.username},
            status=status.HTTP_201_CREATED,
        )

