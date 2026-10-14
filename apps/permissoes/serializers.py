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

DESCRICOES_PERMISSAO = {
    "id": {"help_text": "Identificador numérico da permissão."},
    "codename": {
        "help_text": (
            "Código da permissão, por exemplo `view_user`. É por ele que "
            "os grupos recebem e perdem permissões."
        )
    },
    "name": {"help_text": "Descrição legível da permissão."},
}

DESCRICOES_GRUPO = {
    "id": {"help_text": "Identificador numérico do grupo."},
    "name": {"help_text": "Nome do grupo."},
}


class PermissionSerializer(serializers.ModelSerializer):
    """Permissão do sistema."""

    app_label = serializers.CharField(
        source="content_type.app_label",
        read_only=True,
        help_text=(
            "Nome do app a que a permissão pertence, por exemplo `auth`."
        ),
    )
    model = serializers.CharField(
        source="content_type.model",
        read_only=True,
        help_text=(
            "Nome do model a que a permissão se refere, em minúsculas, por "
            "exemplo `user`."
        ),
    )

    class Meta:
        """Representa Meta."""

        model = Permission
        fields = ["id", "codename", "name", "app_label", "model"]
        extra_kwargs = DESCRICOES_PERMISSAO


class GroupSerializer(serializers.ModelSerializer):
    """Grupo de usuários, com as permissões dele."""

    permissoes = PermissionSerializer(
        source="permissions",
        many=True,
        read_only=True,
        help_text="Permissões do grupo.",
    )

    class Meta:
        """Representa Meta."""

        model = Group
        fields = ["id", "name", "permissoes"]
        extra_kwargs = DESCRICOES_GRUPO


class CreatePermissionSerializer(serializers.Serializer):
    """Dados da permissão a criar."""

    app_label = serializers.CharField(
        help_text="Nome do app do model, por exemplo `auth`."
    )
    model = serializers.CharField(
        help_text=(
            "Nome do model, sem diferenciar maiúsculas de minúsculas, por "
            "exemplo `user`."
        )
    )
    codename = serializers.CharField(
        help_text="Código da permissão. Não pode se repetir no mesmo model."
    )
    name = serializers.CharField(help_text="Descrição legível da permissão.")

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
    """Dados do grupo a criar."""

    grupo = serializers.CharField(
        help_text="Nome do grupo. Não pode repetir o de um grupo existente."
    )
    permissoes_codenames = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Códigos das permissões do grupo. Códigos que não existem são "
            "ignorados."
        ),
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
    """Permissões a incluir e a retirar de um grupo."""

    grupo = serializers.CharField(
        help_text="Nome exato do grupo, com maiúsculas e minúsculas."
    )
    adicionar_codenames = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Códigos das permissões a incluir. Códigos que não existem "
            "são ignorados."
        ),
    )
    remover_codenames = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Códigos das permissões a retirar, aplicados depois das "
            "inclusões."
        ),
    )


class UpdateGroupUsersSerializer(serializers.Serializer):
    """Usuários a incluir e a retirar de um grupo."""

    grupo = serializers.CharField(
        help_text="Nome exato do grupo, com maiúsculas e minúsculas."
    )
    adicionar_usuarios = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Registros funcionais dos usuários a incluir. Os que não "
            "existem são ignorados."
        ),
    )
    remover_usuarios = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Registros funcionais dos usuários a retirar, aplicados depois "
            "das inclusões."
        ),
    )


class UpdateUsuarioSerializer(serializers.Serializer):
    """Dados a alterar em um usuário."""

    usuario = serializers.CharField(
        help_text="Registro funcional do usuário a alterar."
    )
    nome = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text=(
            "Nome completo. A primeira palavra é gravada como nome e o "
            "restante, como sobrenome."
        ),
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text=(
            "E-mail do usuário. Um e-mail diferente do atual é alterado "
            "também no CoreSSO. Vazio apaga o e-mail só neste serviço."
        ),
    )
    is_active = serializers.BooleanField(
        required=False,
        help_text=(
            "Indica se o usuário está ativo. Um usuário inativo é "
            "recusado nas rotas que exigem token."
        ),
    )
    grupos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Lista final de grupos do usuário: os que faltam são "
            "incluídos e os demais, retirados. Lista vazia tira o usuário "
            "de todos os grupos."
        ),
    )
    adicionar_grupos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Os nomes são conferidos, mas o campo não tem efeito hoje. "
            "Use `grupos`."
        ),
    )
    remover_grupos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Os nomes são conferidos, mas o campo não tem efeito hoje. "
            "Use `grupos`."
        ),
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


class AtualizarUsuarioRequisicaoSerializer(UpdateUsuarioSerializer):
    """Dados a alterar em um usuário.

    Em PATCH, o drf-spectacular marca o corpo como parcial e publica todos
    os campos como opcionais. Esta rota não é uma atualização parcial:
    `usuario` é sempre exigido.
    """

    @property
    def partial(self) -> bool:
        """Indica que o corpo nunca é tratado como parcial."""
        return False

    @partial.setter
    def partial(self, valor: bool) -> None:
        """Ignora a marcação de parcial feita na geração do schema."""


class UsuarioComGruposSerializer(serializers.Serializer):
    """Usuário com os grupos a que pertence."""

    usuario = serializers.CharField(help_text="Registro funcional do usuário.")
    nome = serializers.CharField(
        allow_null=True,
        help_text="Nome e sobrenome, ou nulo se não estão preenchidos.",
    )
    email = serializers.CharField(
        allow_null=True, help_text="E-mail, ou nulo se não está preenchido."
    )
    is_active = serializers.BooleanField(
        help_text="Indica se o usuário está ativo."
    )
    grupos = serializers.ListField(
        child=serializers.CharField(),
        help_text="Nomes dos grupos do usuário.",
    )


class UsuariosComGruposSerializer(serializers.Serializer):
    """Usuários cadastrados, com os grupos de cada um."""

    count = serializers.IntegerField(
        help_text="Quantidade de usuários retornados."
    )
    results = UsuarioComGruposSerializer(
        many=True, help_text="Usuários, em ordem de registro funcional."
    )


class UsuarioPermissoesSerializer(serializers.Serializer):
    """Usuário com os grupos e as permissões que tem."""

    usuario = serializers.CharField(help_text="Registro funcional do usuário.")
    nome = serializers.CharField(
        allow_null=True,
        help_text="Nome e sobrenome, ou nulo se não estão preenchidos.",
    )
    email = serializers.CharField(
        allow_null=True, help_text="E-mail, ou nulo se não está preenchido."
    )
    grupos = serializers.ListField(
        child=serializers.CharField(),
        help_text="Nomes dos grupos do usuário, em ordem alfabética.",
    )
    total_permissoes = serializers.IntegerField(
        help_text="Quantidade de itens em `permissoes`."
    )
    permissoes = PermissionSerializer(
        many=True,
        help_text=(
            "Permissões do usuário, diretas ou recebidas dos grupos, sem "
            "repetição."
        ),
    )
