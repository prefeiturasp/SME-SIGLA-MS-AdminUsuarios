"""Serializers de grupos e permissões."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from permissoes.repository import (
    ContentTypeRepository,
    GroupRepository,
    PermissionRepository,
)
from usuarios.repository import UserRepository


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer do modelo Permission."""

    app_label = serializers.CharField(
        source="content_type.app_label", read_only=True
    )
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        """Representa Meta."""

        model = Permission
        fields = ["id", "codename", "name", "app_label", "model"]


class GroupSerializer(serializers.ModelSerializer):
    """Serializer do modelo Group."""

    permissoes = PermissionSerializer(
        source="permissions", many=True, read_only=True
    )

    class Meta:
        """Representa Meta."""

        model = Group
        fields = ["id", "name", "permissoes"]


class CreatePermissionSerializer(serializers.Serializer):
    """Serializer do modelo CreatePermission."""

    app_label = serializers.CharField()
    model = serializers.CharField()
    codename = serializers.CharField()
    name = serializers.CharField()

    def validate(self, attrs: Any) -> Any:
        """Valida content type informado e codename livre para cadastro."""
        app_label, model = (attrs["app_label"], attrs["model"])
        ct = ContentTypeRepository.obter_por_app_e_model(app_label, model)
        if not ct:
            raise serializers.ValidationError(
                "ContentType não encontrado para app_label/model informados."
            )
        if PermissionRepository.existe_por_content_type_e_codename(
            ct, attrs["codename"]
        ):
            raise serializers.ValidationError(
                "Permissão já existe para este content type e codename."
            )
        attrs["content_type"] = ct
        return attrs

    def create(self, validated_data: Any) -> Any:
        """Cria a permissão vinculada ao content type informado."""
        validated_data.pop("content_type", None)
        ct = ContentTypeRepository.obter_por_app_e_model_exato(
            self.validated_data["app_label"],
            self.validated_data["model"],
        )
        return PermissionRepository.criar(
            name=validated_data["name"],
            codename=validated_data["codename"],
            content_type=ct,
        )


class CreateGroupSerializer(serializers.Serializer):
    """Serializer do modelo CreateGroup."""

    grupo = serializers.CharField()
    permissoes_codenames = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def validate_grupo(self, value: Any) -> Any:
        """Impede cadastro de grupo com nome já existente."""
        if GroupRepository.existe_por_nome(value):
            raise serializers.ValidationError("Grupo já existe.")
        return value

    def create(self, validated_data: Any) -> Any:
        """Cria o grupo e vincula as permissões informadas."""
        grupo = GroupRepository.criar(validated_data["grupo"])
        codenames = validated_data.get("permissoes_codenames", [])
        if codenames:
            perms = PermissionRepository.listar_por_codenames(codenames)
            GroupRepository.adicionar_permissoes(grupo, perms)
        return grupo


class UpdateGroupPermissionsSerializer(serializers.Serializer):
    """Serializer do modelo UpdateGroupPermissions."""

    grupo = serializers.CharField()
    adicionar_codenames = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    remover_codenames = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class UpdateGroupUsersSerializer(serializers.Serializer):
    """Serializer do modelo UpdateGroupUsers."""

    grupo = serializers.CharField()
    adicionar_usuarios = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    remover_usuarios = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class UpdateUsuarioSerializer(serializers.Serializer):
    """Atualiza campos básicos do usuário nativo do Django."""

    usuario = serializers.CharField(
        help_text="Username do usuário a ser atualizado."
    )
    nome = serializers.CharField(required=False, allow_blank=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    grupos = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    adicionar_grupos = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    remover_grupos = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def validate_email(self, value: str) -> str:
        """Confere se o e-mail não está em uso por outro usuário."""
        email = (value or "").strip()
        if not email:
            return ""
        username = (self.initial_data or {}).get("usuario", "")
        user = UserRepository.obter_por_username_apenas_id(username)
        if user and UserRepository.existe_email_em_outro_usuario(
            email, user.id
        ):
            raise serializers.ValidationError(
                "Email já está em uso por outro usuário."
            )
        return email

    def validate(self, attrs: Any) -> Any:
        """Confere se os grupos informados existem no cadastro."""
        grupos_final = attrs.get("grupos")
        adicionar = attrs.get("adicionar_grupos") or []
        remover = attrs.get("remover_grupos") or []
        grupos_informados = []
        if grupos_final is not None:
            grupos_informados.extend(grupos_final)
        grupos_informados.extend(adicionar)
        grupos_informados.extend(remover)
        grupos_set = {
            g.strip() for g in grupos_informados if (g or "").strip()
        }
        if grupos_set:
            existentes = GroupRepository.nomes_existentes(grupos_set)
            faltando = sorted(grupos_set - existentes)
            if faltando:
                raise serializers.ValidationError(
                    {"grupos": f"Grupos inexistentes: {', '.join(faltando)}"}
                )
        return attrs
