"""DRF views for the usuarios module."""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import Group, Permission, User
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.exceptions import SmeIntegracaoException
from usuarios.serializers.permissoes_serializers import (
    CreateGroupSerializer,
    CreatePermissionSerializer,
    GroupSerializer,
    PermissionSerializer,
    UpdateGroupPermissionsSerializer,
    UpdateGroupUsersSerializer,
    UpdateUsuarioSerializer,
)
from usuarios.services.sme_integracao import SmeIntegracaoService

logger = logging.getLogger(__name__)


class GerenciarPermissoesUsuarioView(APIView):
    """Representa GerenciarPermissoesUsuarioView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="usuario",
                description=(
                    "Nome de usuário para buscar permissões "
                    "(diretas e herdadas)."
                ),
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="model",
                description=(
                    "(Opcional) Modelos separados por vírgula "
                    "para filtrar permissões."
                ),
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: PermissionSerializer(many=True)},
        description=(
            "Retorna permissões diretas e herdadas por grupo do usuário."
        ),
    )
    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
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
        permissoes_diretas = user.user_permissions.select_related(
            "content_type"
        )
        permissoes_grupos = Permission.objects.filter(
            group__user=user
        ).select_related("content_type")
        permissoes = (permissoes_diretas | permissoes_grupos).distinct()
        if model_param:
            models_filter = [
                m.strip().lower() for m in model_param.split(",") if m.strip()
            ]
            permissoes = permissoes.filter(
                content_type__model__in=models_filter
            )
        serializer = PermissionSerializer(
            permissoes.order_by("content_type__app_label", "codename"),
            many=True,
        )
        grupos = list(
            user.groups.order_by("name").values_list("name", flat=True)
        )
        nome = (
            f"{user.first_name} {user.last_name}".strip()
            if user.first_name or user.last_name
            else ""
        ) or None
        return Response(
            {
                "usuario": user.username,
                "nome": nome,
                "email": user.email or None,
                "grupos": grupos,
                "total_permissoes": len(serializer.data),
                "permissoes": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PermissoesDisponiveisView(APIView):
    """Representa PermissoesDisponiveisView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={200: PermissionSerializer(many=True)},
        description="Retorna todas as permissões disponíveis no sistema.",
    )
    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        permissoes = (
            Permission.objects.select_related("content_type")
            .all()
            .order_by("content_type__app_label", "id")
        )
        serializer = PermissionSerializer(permissoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=CreatePermissionSerializer,
        responses={201: PermissionSerializer},
        description="Cria uma nova permissão vinculada a um ContentType.",
    )
    def post(self, request: Any) -> Any:
        """Registra ou processa o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        serializer = CreatePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perm = serializer.save()
        return Response(
            PermissionSerializer(perm).data, status=status.HTTP_201_CREATED
        )


class GruposDisponiveisView(APIView):
    """Representa GruposDisponiveisView."""

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
            )
        ],
        responses={200: GroupSerializer(many=True)},
        description="Retorna permissões de grupos (ou de um grupo).",
    )
    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        grupo_name = request.query_params.get("grupo", "").strip()
        grupos_qs = Group.objects.prefetch_related(
            "permissions__content_type"
        ).order_by("name")
        if grupo_name:
            grupos_qs = grupos_qs.filter(name=grupo_name)
            if not grupos_qs.exists():
                return Response(
                    {"detail": "Grupo não encontrado"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        serializer = GroupSerializer(grupos_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UpdateGroupPermissionsSerializer,
        responses={200: GroupSerializer},
        description="Adiciona ou remove permissões (codename) de um grupo.",
    )
    def put(self, request: Any) -> Any:
        """Atualiza o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        serializer = UpdateGroupPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grupo = Group.objects.filter(name=data["grupo"]).first()
        if not grupo:
            return Response(
                {"detail": "Grupo não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        add_codenames = data.get("adicionar_codenames", [])
        remove_codenames = data.get("remover_codenames", [])
        if add_codenames:
            perms_add = Permission.objects.filter(codename__in=add_codenames)
            grupo.permissions.add(*perms_add)
        if remove_codenames:
            perms_rem = Permission.objects.filter(
                codename__in=remove_codenames
            )
            grupo.permissions.remove(*perms_rem)
        grupo.save()
        return Response(GroupSerializer(grupo).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=CreateGroupSerializer,
        responses={201: GroupSerializer},
        description="Cria um grupo e associa permissões usando codenames.",
    )
    def post(self, request: Any) -> Any:
        """Registra ou processa o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grupo = serializer.save()
        return Response(
            GroupSerializer(grupo).data, status=status.HTTP_201_CREATED
        )


class GerenciarUsuariosGrupoView(APIView):
    """Representa GerenciarUsuariosGrupoView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        request=UpdateGroupUsersSerializer,
        responses={200: GroupSerializer},
        description="Adiciona ou remove usuários (username) de um grupo.",
    )
    @action(detail=False, methods=["put"], url_path="usuarios")
    def put(self, request: Any) -> Any:
        """Atualiza o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        serializer = UpdateGroupUsersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grupo = Group.objects.filter(name=data["grupo"]).first()
        if not grupo:
            return Response(
                {"detail": "Grupo não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
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
    """Representa UsuariosComGruposView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="usuario",
                description="(Opcional) Filtra por username (sem case).",
                required=False,
                type=str,
            )
        ],
        responses={200: GroupSerializer(many=True)},
        description="Retorna todos os usuários com os grupos a que pertencem.",
    )
    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        usuario_filtro = request.query_params.get("usuario", "").strip()
        qs = User.objects.all().prefetch_related("groups").order_by("username")
        if usuario_filtro:
            qs = qs.filter(username__icontains=usuario_filtro)
        data = []
        for u in qs:
            nome = (
                f"{u.first_name} {u.last_name}".strip()
                if u.first_name or u.last_name
                else ""
            ) or None
            data.append(
                {
                    "usuario": u.username,
                    "nome": nome,
                    "email": u.email or None,
                    "is_active": u.is_active,
                    "grupos": list(u.groups.values_list("name", flat=True)),
                }
            )
        return Response(
            {"count": len(data), "results": data}, status=status.HTTP_200_OK
        )

    @extend_schema(
        request=UpdateUsuarioSerializer,
        responses={
            200: OpenApiResponse(
                description="Usuário atualizado com sucesso."
            ),
            400: OpenApiResponse(description="Dados inválidos."),
            404: OpenApiResponse(description="Usuário não encontrado."),
        },
        description=(
            "Atualiza nome, e-mail e is_active do usuário e gerencia grupos. "
            'Se "grupos" for enviado, define a lista final (pode ser []). '
            "E-mail deve ser único."
        ),
    )
    def patch(self, request: Any) -> Any:
        """Altera parcialmente o recurso solicitado.

        Args:
            self: Instância do objeto.
            request: Requisição HTTP recebida.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        serializer = UpdateUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = (
            User.objects.filter(username=data["usuario"])
            .prefetch_related("groups")
            .first()
        )
        if not user:
            return Response(
                {"detail": "Usuário não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if "nome" in data:
            nome = (data.get("nome") or "").strip()
            if nome:
                parts = [p for p in nome.split(" ") if p]
                user.first_name = parts[0] if parts else ""
                user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            else:
                user.first_name = ""
                user.last_name = ""
        if "email" in data:
            novo_email = (data.get("email") or "").strip()
            if novo_email and novo_email.lower() != (user.email or "").lower():
                try:
                    SmeIntegracaoService.alterar_email(
                        user.username, novo_email
                    )
                except SmeIntegracaoException as e:
                    logger.error(
                        f"Falha ao alterar email no SME Integração: {e}"
                    )
                    return Response(
                        {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )
            user.email = novo_email
        if "is_active" in data:
            user.is_active = data["is_active"]
        user.save()
        if "grupos" in data:
            grupos_desejados = [
                g.strip()
                for g in data.get("grupos") or []
                if (g or "").strip()
            ]
            desired_set = set(grupos_desejados)
            current_set = set(user.groups.values_list("name", flat=True))
            to_add = sorted(desired_set - current_set)
            to_remove = sorted(current_set - desired_set)
            if to_add:
                grupos_add = Group.objects.filter(name__in=to_add)
                user.groups.add(*grupos_add)
            if to_remove:
                grupos_rem = Group.objects.filter(name__in=to_remove)
                user.groups.remove(*grupos_rem)
        nome_resp = (
            f"{user.first_name} {user.last_name}".strip()
            if user.first_name or user.last_name
            else ""
        ) or None
        payload = {
            "usuario": user.username,
            "nome": nome_resp,
            "email": user.email or None,
            "is_active": user.is_active,
            "grupos": list(user.groups.values_list("name", flat=True)),
        }
        return Response(payload, status=status.HTTP_200_OK)
