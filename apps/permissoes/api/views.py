"""DRF views for the permissoes module."""

from __future__ import annotations

import logging
from typing import Any

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from permissoes.api.schemas import (
    OPERACOES_GRUPOS,
    OPERACOES_PERMISSOES,
    OPERACOES_PERMISSOES_DO_USUARIO,
    OPERACOES_USUARIOS_COM_GRUPOS,
    OPERACOES_USUARIOS_DO_GRUPO,
    TAG_GRUPOS,
    TAG_PERMISSOES,
)
from permissoes.repository import GroupRepository, PermissionRepository
from permissoes.serializers import (
    CreateGroupSerializer,
    CreatePermissionSerializer,
    UpdateGroupPermissionsSerializer,
    UpdateGroupUsersSerializer,
    UpdateUsuarioSerializer,
)
from usuarios.api.schemas import TAG_USUARIOS
from usuarios.exceptions import SmeIntegracaoException
from usuarios.repository import UserRepository
from usuarios.services.sme_integracao import SmeIntegracaoService

logger = logging.getLogger(__name__)


@extend_schema(tags=[TAG_USUARIOS])
@extend_schema_view(**OPERACOES_PERMISSOES_DO_USUARIO)
class GerenciarPermissoesUsuarioView(APIView):
    """Representa GerenciarPermissoesUsuarioView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        username = request.query_params.get("usuario", "").strip()
        model_param = request.query_params.get("model", "").strip()
        if not username:
            return Response(
                {"detail": "usuario é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = UserRepository.obter_por_username(username)
        if not user:
            return Response(
                {"detail": "Usuário não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        models_filter = None
        if model_param:
            models_filter = [
                m.strip().lower() for m in model_param.split(",") if m.strip()
            ]
        permissoes = PermissionRepository.permissoes_do_usuario(
            user, models_filter=models_filter
        )
        permissoes_data = PermissionRepository.serializar_lista(permissoes)
        grupos = UserRepository.nomes_grupos(user)
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
                "total_permissoes": len(permissoes_data),
                "permissoes": permissoes_data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=[TAG_PERMISSOES])
@extend_schema_view(**OPERACOES_PERMISSOES)
class PermissoesDisponiveisView(APIView):
    """Representa PermissoesDisponiveisView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        permissoes = PermissionRepository.listar_todas()
        return Response(
            PermissionRepository.serializar_lista(permissoes),
            status=status.HTTP_200_OK,
        )

    def post(self, request: Any) -> Any:
        """Registra ou processa o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        serializer = CreatePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perm = serializer.save()
        return Response(
            PermissionRepository.serializar(perm),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=[TAG_GRUPOS])
@extend_schema_view(**OPERACOES_GRUPOS)
class GruposDisponiveisView(APIView):
    """Representa GruposDisponiveisView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        grupo_name = request.query_params.get("grupo", "").strip()
        grupos_qs = GroupRepository.listar_com_permissoes(
            nome=grupo_name or None
        )
        if grupo_name and not grupos_qs.exists():
            return Response(
                {"detail": "Grupo não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            GroupRepository.serializar_lista(grupos_qs),
            status=status.HTTP_200_OK,
        )

    def put(self, request: Any) -> Any:
        """Atualiza o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        serializer = UpdateGroupPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grupo = GroupRepository.obter_por_nome(data["grupo"])
        if not grupo:
            return Response(
                {"detail": "Grupo não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        add_codenames = data.get("adicionar_codenames", [])
        remove_codenames = data.get("remover_codenames", [])
        if add_codenames:
            perms_add = PermissionRepository.listar_por_codenames(
                add_codenames
            )
            GroupRepository.adicionar_permissoes(grupo, perms_add)
        if remove_codenames:
            perms_rem = PermissionRepository.listar_por_codenames(
                remove_codenames
            )
            GroupRepository.remover_permissoes(grupo, perms_rem)
        GroupRepository.salvar(grupo)
        return Response(
            GroupRepository.serializar(grupo), status=status.HTTP_200_OK
        )

    def post(self, request: Any) -> Any:
        """Registra ou processa o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grupo = serializer.save()
        return Response(
            GroupRepository.serializar(grupo), status=status.HTTP_201_CREATED
        )


@extend_schema(tags=[TAG_GRUPOS])
@extend_schema_view(**OPERACOES_USUARIOS_DO_GRUPO)
class GerenciarUsuariosGrupoView(APIView):
    """Representa GerenciarUsuariosGrupoView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def put(self, request: Any) -> Any:
        """Atualiza o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        serializer = UpdateGroupUsersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grupo = GroupRepository.obter_por_nome(data["grupo"])
        if not grupo:
            return Response(
                {"detail": "Grupo não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        add_users = data.get("adicionar_usuarios", [])
        rem_users = data.get("remover_usuarios", [])
        if add_users:
            users_add = UserRepository.listar_por_usernames(add_users)
            GroupRepository.adicionar_usuarios(grupo, users_add)
        if rem_users:
            users_rem = UserRepository.listar_por_usernames(rem_users)
            GroupRepository.remover_usuarios(grupo, users_rem)
        GroupRepository.salvar(grupo)
        return Response(
            GroupRepository.serializar(grupo), status=status.HTTP_200_OK
        )


@extend_schema(tags=[TAG_USUARIOS])
@extend_schema_view(**OPERACOES_USUARIOS_COM_GRUPOS)
class UsuariosComGruposView(APIView):
    """Representa UsuariosComGruposView."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request: Any) -> Any:
        """Consulta o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        usuario_filtro = request.query_params.get("usuario", "").strip()
        qs = UserRepository.listar_com_grupos(
            username_filtro=usuario_filtro or None
        )
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
                    "grupos": UserRepository.nomes_grupos_sem_ordem(u),
                }
            )
        return Response(
            {"count": len(data), "results": data}, status=status.HTTP_200_OK
        )

    def patch(self, request: Any) -> Any:
        """Altera parcialmente o recurso solicitado.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP com os dados solicitados.
        """
        serializer = UpdateUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = UserRepository.obter_por_username_com_grupos(data["usuario"])
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
        UserRepository.salvar(user)
        if "grupos" in data:
            grupos_desejados = [
                g.strip()
                for g in data.get("grupos") or []
                if (g or "").strip()
            ]
            desired_set = set(grupos_desejados)
            current_set = set(UserRepository.nomes_grupos_sem_ordem(user))
            to_add = sorted(desired_set - current_set)
            to_remove = sorted(current_set - desired_set)
            if to_add:
                grupos_add = GroupRepository.listar_por_nomes(to_add)
                UserRepository.adicionar_grupos(user, grupos_add)
            if to_remove:
                grupos_rem = GroupRepository.listar_por_nomes(to_remove)
                UserRepository.remover_grupos(user, grupos_rem)
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
            "grupos": UserRepository.nomes_grupos_sem_ordem(user),
        }
        return Response(payload, status=status.HTTP_200_OK)
