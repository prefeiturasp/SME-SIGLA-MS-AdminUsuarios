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

        

class PermissoesDisponiveisView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Lista de todas as permissões disponíveis"),
        },
        description="Retorna todas as permissões disponíveis no sistema.")
    def get(self, request):
        permissoes = Permission.objects.select_related("content_type").all().order_by("content_type__app_label", "id")
        data = [
            {
                "id": p.id,
                "codename": p.codename,
                "name": p.name,
                "app_label": p.content_type.app_label,
                "model": p.content_type.model,
            }
            for p in permissoes
        ]
        return Response(data, status=status.HTTP_200_OK)


class GerenciarPermissoesUsuarioView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="usuario",
                description="Nome de usuário para buscar as permissões (inclui permissões diretas e dos grupos aos quais pertence).",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="model",
                description=(
                    "(Opcional) Lista de nomes de modelos para filtrar as permissões. "
                    "Envie valores separados por vírgula, por exemplo: user,group,permission."
                ),
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Permissões diretas e herdadas do usuário (filtradas por modelos, se informado)"),
            400: OpenApiResponse(description="Usuário é obrigatório"),
            404: OpenApiResponse(description="Usuário não encontrado"),
        },
        description="Retorna as permissões associadas a um usuário, incluindo as herdadas dos grupos, com filtro opcional por modelos.",
    )
    def get(self, request):
        username = request.query_params.get("usuario", "").strip()
        model_param = request.query_params.get("model", "").strip()

        
        if not username:
            return Response(
                {"detail": "usuario é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username=username).first()
        if not user:
            return Response(
                {"detail": "Usuário não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        
        permissoes_diretas = user.user_permissions.select_related("content_type")

        
        permissoes_grupos = Permission.objects.filter(group__user=user).select_related("content_type")

        
        permissoes = (permissoes_diretas | permissoes_grupos).distinct()

        
        if model_param:
            models = [m.strip().lower() for m in model_param.split(",") if m.strip()]
            if models:
                permissoes = permissoes.filter(content_type__model__in=models)

        permissoes = permissoes.order_by("content_type__app_label", "codename")

        data = [
            {
                "id": p.id,
                "codename": p.codename,
                "name": p.name,
                "app_label": p.content_type.app_label,
                "model": p.content_type.model,
            }
            for p in permissoes
        ]

        
        grupos = list(user.groups.order_by("name").values_list("name", flat=True))

        return Response(
            {
                "usuario": user.username,
                "grupos": grupos,
                "total_permissoes": len(data),
                "permissoes": data,
            },
            status=status.HTTP_200_OK,
        )


 

class CriarPermissaoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "app_label": {"type": "string"},
                    "model": {"type": "string"},
                    "codename": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["app_label", "model", "codename", "name"],
            }
        },
        responses={
            201: OpenApiResponse(description="Permissão criada com sucesso"),
            400: OpenApiResponse(description="Dados inválidos ou content type não encontrado"),
            409: OpenApiResponse(description="Permissão já existe"),
        },
        description=(
            "Cria uma permissão vinculada a um ContentType específico, informando app_label, model, codename e name."
        ),
    )
    def post(self, request):
        payload = request.data or {}
        app_label = (payload.get("app_label") or "").strip()
        model = (payload.get("model") or "").strip()
        codename = (payload.get("codename") or "").strip()
        name = (payload.get("name") or "").strip()

        if not all([app_label, model, codename, name]):
            return Response({"detail": "app_label, model, codename e name são obrigatórios"}, status=status.HTTP_400_BAD_REQUEST)

        ct = ContentType.objects.filter(app_label=app_label, model__iexact=model).first()
        if not ct:
            return Response({"detail": "ContentType não encontrado para app_label/model informados"}, status=status.HTTP_400_BAD_REQUEST)

        exists = Permission.objects.filter(content_type=ct, codename=codename).exists()
        if exists:
            return Response({"detail": "Permissão já existe para este content type e codename"}, status=status.HTTP_409_CONFLICT)

        perm = Permission.objects.create(name=name, codename=codename, content_type=ct)

        return Response(
            {
                "id": perm.id,
                "codename": perm.codename,
                "name": perm.name,
                "app_label": perm.content_type.app_label,
                "model": perm.content_type.model,
            },
            status=status.HTTP_201_CREATED,
        )


class GruposDisponiveisView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Lista de todos os grupos disponíveis"),
        },
        description="Retorna todos os grupos disponíveis no sistema."
    )
    def get(self, request):
        grupos = Group.objects.all().order_by("name")
        data = [
            {
                "id": g.id,
                "name": g.name,
            }
            for g in grupos
        ]
        return Response(data, status=status.HTTP_200_OK)


class PermissoesGrupoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="grupo",
                description="(Opcional) Nome do grupo para buscar as permissões. Se omitido, retorna as permissões de todos os grupos.",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="model",
                description=(
                    "(Opcional) Lista de nomes de modelos para filtrar as permissões. "
                    "Envie valores separados por vírgula, por exemplo: user,group,permission."
                ),
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Permissões agrupadas por grupo (ou apenas de um grupo, se informado)"),
            404: OpenApiResponse(description="Grupo não encontrado"),
        },
        description="Retorna as permissões associadas a um grupo específico ou de todos os grupos, com filtro opcional por modelo.",
    )
    def get(self, request):
        grupo_name = request.query_params.get("grupo", "").strip()
        model_param = request.query_params.get("model", "").strip()

        
        model_filter = None
        if model_param:
            model_filter = [m.strip().lower() for m in model_param.split(",") if m.strip()]

        
        if grupo_name:
            grupo = Group.objects.filter(name=grupo_name).first()
            if not grupo:
                return Response(
                    {"detail": "Grupo não encontrado"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            permissoes = grupo.permissions.select_related("content_type").all()
            if model_filter:
                permissoes = permissoes.filter(content_type__model__in=model_filter)

            permissoes = permissoes.order_by("content_type__app_label", "codename")

            data = [
                {
                    "id": p.id,
                    "codename": p.codename,
                    "name": p.name,
                    "app_label": p.content_type.app_label,
                    "model": p.content_type.model,
                }
                for p in permissoes
            ]

            return Response(
                {"grupo": grupo.name, "permissoes": data},
                status=status.HTTP_200_OK,
            )

        
        grupos = Group.objects.prefetch_related("permissions__content_type").all()
        resultado = []

        for grupo in grupos:
            permissoes = grupo.permissions.all()
            if model_filter:
                permissoes = permissoes.filter(content_type__model__in=model_filter)

            permissoes = permissoes.order_by("content_type__app_label", "codename")

            resultado.append(
                {
                    "grupo": grupo.name,
                    "permissoes": [
                        {
                            "id": p.id,
                            "codename": p.codename,
                            "name": p.name,
                            "app_label": p.content_type.app_label,
                            "model": p.content_type.model,
                        }
                        for p in permissoes
                    ],
                }
            )

        return Response(resultado, status=status.HTTP_200_OK)



    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "grupo": {"type": "string"},
                    "adicionar_codenames": {"type": "array", "items": {"type": "string"}},
                    "remover_codenames": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["grupo"],
            }
        },
        responses={
            200: OpenApiResponse(description="Permissões atualizadas"),
            400: OpenApiResponse(description="Dados inválidos"),
            404: OpenApiResponse(description="Grupo não encontrado"),
        },
        description=(
            "Adiciona e/ou remove permissões (por codename) de um grupo. "
            "Envie arrays 'adicionar_codenames' e/ou 'remover_codenames' com codenames."
        ),
    )
    def put(self, request):
        payload = request.data or {}
        grupo_name = payload.get("grupo")
        adicionar_codenames = payload.get("adicionar_codenames") or []
        remover_codenames = payload.get("remover_codenames") or []

        if not isinstance(grupo_name, str) or grupo_name.strip() == "":
            return Response({"detail": "grupo é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(adicionar_codenames, list) or not isinstance(remover_codenames, list):
            return Response({"detail": "'adicionar_codenames' e 'remover_codenames' devem ser listas"}, status=status.HTTP_400_BAD_REQUEST)

        grupo = Group.objects.filter(name=grupo_name).first()
        if not grupo:
            return Response({"detail": "Grupo não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        
        adicionar_codenames_validos = [c for c in adicionar_codenames if isinstance(c, str) and c]
        remover_codenames_validos = [c for c in remover_codenames if isinstance(c, str) and c]

        perms_add = list(Permission.objects.filter(codename__in=adicionar_codenames_validos)) if adicionar_codenames_validos else []
        perms_rem = list(Permission.objects.filter(codename__in=remover_codenames_validos)) if remover_codenames_validos else []

        
        unknown_add = sorted(set(adicionar_codenames_validos) - {p.codename for p in perms_add})
        unknown_rem = sorted(set(remover_codenames_validos) - {p.codename for p in perms_rem})
        if unknown_add or unknown_rem:
            return Response(
                {
                    "detail": "Algumas permissões não foram encontradas",
                    "adicionar_desconhecidas": unknown_add,
                    "remover_desconhecidas": unknown_rem,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if perms_add:
            grupo.permissions.add(*perms_add)
        if perms_rem:
            grupo.permissions.remove(*perms_rem)

        grupo.save()

        atuais = (
            grupo.permissions.select_related("content_type").all().order_by("content_type__app_label", "codename")
        )
        atuais_data = [
            {
                "id": p.id,
                "codename": p.codename,
                "name": p.name,
                "app_label": p.content_type.app_label,
                "model": p.content_type.model,
            }
            for p in atuais
        ]

        return Response(
            {
                "grupo": grupo.name,
                "permissoes": atuais_data,
                "adicionadas": [p.codename for p in perms_add],
                "removidas": [p.codename for p in perms_rem],
            },
            status=status.HTTP_200_OK,
        )

        
class CriarGrupoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "grupo": {"type": "string"},
                    "permissoes_codenames": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["grupo"],
            }
        },
        responses={
            201: OpenApiResponse(description="Grupo criado com sucesso"),
            400: OpenApiResponse(description="Dados inválidos"),
            409: OpenApiResponse(description="Grupo já existe"),
        },
        description=(
            "Cria um grupo e associa permissões usando codenames. "
            "Se 'permissoes_codenames' for informado, valida codenames e associa ao grupo."
        ),
    )
    def post(self, request):
        payload = request.data or {}
        grupo_name = (payload.get("grupo") or "").strip()
        permissoes_codenames = payload.get("permissoes_codenames") or []

        if not grupo_name:
            return Response({"detail": "grupo é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(permissoes_codenames, list):
            return Response({"detail": "'permissoes_codenames' deve ser uma lista"}, status=status.HTTP_400_BAD_REQUEST)

        if Group.objects.filter(name=grupo_name).exists():
            return Response({"detail": "Grupo já existe"}, status=status.HTTP_409_CONFLICT)

        codenames_validos = [c for c in permissoes_codenames if isinstance(c, str) and c]
        perms = list(Permission.objects.filter(codename__in=codenames_validos)) if codenames_validos else []
        unknown = sorted(set(codenames_validos) - {p.codename for p in perms})
        if unknown:
            return Response(
                {
                    "detail": "Algumas permissões não foram encontradas",
                    "permissoes_codenames_desconhecidas": unknown,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo = Group.objects.create(name=grupo_name)
        if perms:
            grupo.permissions.add(*perms)

        atuais = grupo.permissions.select_related("content_type").all().order_by("content_type__app_label", "codename")
        atuais_data = [
            {
                "id": p.id,
                "codename": p.codename,
                "name": p.name,
                "app_label": p.content_type.app_label,
                "model": p.content_type.model,
            }
            for p in atuais
        ]

        return Response(
            {"id": grupo.id, "grupo": grupo.name, "permissoes": atuais_data},
            status=status.HTTP_201_CREATED,
        )

class GerenciarUsuariosGrupoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "grupo": {"type": "string"},
                    "adicionar_usuarios": {"type": "array", "items": {"type": "string"}},
                    "remover_usuarios": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["grupo"],
            }
        },
        responses={
            200: OpenApiResponse(description="Usuários atualizados no grupo"),
            400: OpenApiResponse(description="Dados inválidos"),
            404: OpenApiResponse(description="Grupo não encontrado"),
        },
        description=(
            "Adiciona e/ou remove usuários (por username) de um grupo identificado por ID. "
            "Envie arrays 'adicionar_usuarios' e/ou 'remover_usuarios' com usernames."
        ),
    )
    def put(self, request):
        payload = request.data or {}
        grupo_name = payload.get("grupo")
        adicionar_usuarios = payload.get("adicionar_usuarios") or []
        remover_usuarios = payload.get("remover_usuarios") or []

        
        if not isinstance(grupo_name, str):
            return Response({"detail": "'grupo' deve ser um string"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(adicionar_usuarios, list) or not isinstance(remover_usuarios, list):
            return Response(
                {"detail": "'adicionar_usuarios' e 'remover_usuarios' devem ser listas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo = Group.objects.filter(name=grupo_name).first()
        if not grupo:
            return Response({"detail": "Grupo não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        
        adicionar_usernames_validos = [u for u in adicionar_usuarios if isinstance(u, str) and u.strip()]
        remover_usernames_validos = [u for u in remover_usuarios if isinstance(u, str) and u.strip()]

        users_add = list(User.objects.filter(username__in=adicionar_usernames_validos)) if adicionar_usernames_validos else []
        users_rem = list(User.objects.filter(username__in=remover_usernames_validos)) if remover_usernames_validos else []

        unknown_add = sorted(set(adicionar_usernames_validos) - {u.username for u in users_add})
        unknown_rem = sorted(set(remover_usernames_validos) - {u.username for u in users_rem})
        if unknown_add or unknown_rem:
            return Response(
                {
                    "detail": "Alguns usuários não foram encontrados",
                    "adicionar_usuarios_desconhecidos": unknown_add,
                    "remover_usuarios_desconhecidos": unknown_rem,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        
        if users_add:
            grupo.user_set.add(*users_add)
        if users_rem:
            grupo.user_set.remove(*users_rem)

        
        atuais = list(grupo.user_set.order_by("username").values_list("username", flat=True))

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nome": grupo.name,
                "usuarios_atuais": atuais,
                "usuarios_adicionados": [u.username for u in users_add],
                "usuarios_removidos": [u.username for u in users_rem],
            },
            status=status.HTTP_200_OK,
        )


class UsuariosComGruposView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="usuario",
                description="(Opcional) Filtra por username (case-insensitive).",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Lista de usuários com seus grupos"),
        },
        description="Retorna usuários e a lista de grupos a que cada um pertence.",
    )
    def get(self, request):
        usuario_filtro = request.query_params.get("usuario", "").strip()

        qs = User.objects.all().order_by("username").prefetch_related("groups")
        if usuario_filtro:
            qs = qs.filter(username__icontains=usuario_filtro)

        data = [
            {
                "usuario": u.username,
                "grupos": list(u.groups.order_by("name").values_list("name", flat=True)),
            }
            for u in qs
        ]

        return Response({"count": len(data), "results": data}, status=status.HTTP_200_OK)
