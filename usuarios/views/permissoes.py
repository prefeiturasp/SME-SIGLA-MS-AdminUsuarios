"""
DRF views for the usuarios module.
"""

import logging
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User, Permission, Group

from usuarios.serializers.permissoes_serializers import (
    PermissionSerializer,
    CreatePermissionSerializer,
    GroupSerializer,
    CreateGroupSerializer,
    UpdateGroupPermissionsSerializer,
    UpdateGroupUsersSerializer,
)

logger = logging.getLogger(__name__)


class GerenciarPermissoesUsuarioView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="usuario",
                description="Nome de usuário para buscar as permissões (inclui diretas e herdadas).",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="model",
                description="(Opcional) Lista de modelos separados por vírgula para filtrar as permissões.",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: PermissionSerializer(many=True)},
        description="Retorna as permissões (diretas e herdadas por grupo) do usuário.",
    )
    def get(self, request):
        username = request.query_params.get("usuario", "").strip()
        model_param = request.query_params.get("model", "").strip()

        if not username:
            return Response({"detail": "usuario é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(username=username).first()
        if not user:
            return Response({"detail": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)

            
        permissoes_diretas = user.user_permissions.select_related("content_type")

        
        permissoes_grupos = Permission.objects.filter(group__user=user).select_related("content_type")

        
        permissoes = (permissoes_diretas | permissoes_grupos).distinct()


        if model_param:
            models_filter = [m.strip().lower() for m in model_param.split(",") if m.strip()]
            permissoes = permissoes.filter(content_type__model__in=models_filter)

        serializer = PermissionSerializer(permissoes.order_by("content_type__app_label", "codename"), many=True)
        grupos = list(user.groups.order_by("name").values_list("name", flat=True))
        return Response(
            {
                "usuario": user.username,
                "grupos": grupos,
                "total_permissoes": len(serializer.data),
                "permissoes": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PermissoesDisponiveisView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={200: PermissionSerializer(many=True)},
        description="Retorna todas as permissões disponíveis no sistema.",
    )
    def get(self, request):
        permissoes = Permission.objects.select_related("content_type").all().order_by(
            "content_type__app_label", "id"
        )
        serializer = PermissionSerializer(permissoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=CreatePermissionSerializer,
        responses={201: PermissionSerializer},
        description="Cria uma nova permissão vinculada a um ContentType.",
    )
    def post(self, request):
        serializer = CreatePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perm = serializer.save()
        return Response(PermissionSerializer(perm).data, status=status.HTTP_201_CREATED)


class GruposDisponiveisView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="grupo",
                description="(Opcional) Nome do grupo para filtrar.",
                required=False,
                type=str,
            ),
 
        ],
        responses={200: GroupSerializer(many=True)},
        description="Retorna permissões de grupos (ou de um grupo específico).",
    )
    def get(self, request):
        grupo_name = request.query_params.get("grupo", "").strip()
 
        grupos_qs = Group.objects.prefetch_related("permissions__content_type").order_by("name")
        if grupo_name:
            grupos_qs = grupos_qs.filter(name=grupo_name)
            if not grupos_qs.exists():
                return Response({"detail": "Grupo não encontrado"}, status=status.HTTP_404_NOT_FOUND)

 
        serializer = GroupSerializer(grupos_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




    @extend_schema(
        request=UpdateGroupPermissionsSerializer,
        responses={200: GroupSerializer},
        description="Adiciona e/ou remove permissões (por codename) de um grupo.",
    )
    def put(self, request):
        serializer = UpdateGroupPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grupo = Group.objects.filter(name=data["grupo"]).first()

        if not grupo:
            return Response({"detail": "Grupo não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        add_codenames = data.get("adicionar_codenames", [])
        remove_codenames = data.get("remover_codenames", [])

        if add_codenames:
            perms_add = Permission.objects.filter(codename__in=add_codenames)
            grupo.permissions.add(*perms_add)

        if remove_codenames:
            perms_rem = Permission.objects.filter(codename__in=remove_codenames)
            grupo.permissions.remove(*perms_rem)

        grupo.save()
        return Response(GroupSerializer(grupo).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=CreateGroupSerializer,
        responses={201: GroupSerializer},
        description="Cria um grupo e associa permissões usando codenames.",
    )
    def post(self, request):
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grupo = serializer.save()
        return Response(GroupSerializer(grupo).data, status=status.HTTP_201_CREATED)


 
class GerenciarUsuariosGrupoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=UpdateGroupUsersSerializer,
        responses={200: GroupSerializer},
        description="Adiciona e/ou remove usuários (por username) de um grupo.",
    )
    @action(detail=False, methods=["put"], url_path="usuarios")
    def put(self, request):
        serializer = UpdateGroupUsersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        grupo = Group.objects.filter(name=data["grupo"]).first()
        if not grupo:
            return Response({"detail": "Grupo não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        add_users = data.get("adicionar_usuarios", [])
        rem_users = data.get("remover_usuarios", [])

        if add_users:
            users_add = User.objects.filter(username__in=add_users)
            grupo.user_set.add(*users_add)

        if rem_users:
            users_rem = User.objects.filter(username__in=rem_users)
            grupo.user_set.remove(*users_rem)

        grupo.save()
        return Response(GroupSerializer(grupo).data, status=status.HTTP_200_OK)


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
            ),
        ],
        responses={200: GroupSerializer(many=True)},
        description="Retorna todos os usuários com os grupos a que pertencem.",
    )
    def get(self, request):
        usuario_filtro = request.query_params.get("usuario", "").strip()
        qs = User.objects.all().prefetch_related("groups").order_by("username")

        if usuario_filtro:
            qs = qs.filter(username__icontains=usuario_filtro)

        data = [
            {"usuario": u.username, "grupos": list(u.groups.values_list("name", flat=True))}
            for u in qs
        ]
        return Response({"count": len(data), "results": data}, status=status.HTTP_200_OK)
