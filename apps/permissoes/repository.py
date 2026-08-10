"""Repositório de acesso a dados de permissões e grupos."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet


class ContentTypeRepository:
    """Consultas e persistência de ContentType."""

    @classmethod
    def obter_por_app_e_model(
        cls, app_label: str, model: str
    ) -> ContentType | None:
        """Retorna ContentType por app_label e model (case-insensitive)."""
        return ContentType.objects.filter(
            app_label=app_label, model__iexact=model
        ).first()

    @classmethod
    def obter_por_app_e_model_exato(
        cls, app_label: str, model: str
    ) -> ContentType:
        """Retorna ContentType por app_label e model (raises DoesNotExist)."""
        return ContentType.objects.get(
            app_label=app_label, model__iexact=model
        )

    @classmethod
    def get_or_create(
        cls, *, app_label: str, model: str
    ) -> tuple[ContentType, bool]:
        """Obtém ou cria ContentType pelo app_label/model."""
        return ContentType.objects.get_or_create(
            app_label=app_label, model=model
        )


class PermissionRepository:
    """Consultas e persistência de Permission."""

    @staticmethod
    def serializar(permission: Permission, **kwargs: Any) -> dict[str, Any]:
        """Converte uma permissão em dicionário."""
        from permissoes.serializers import PermissionSerializer

        return PermissionSerializer(permission, **kwargs).data

    @classmethod
    def serializar_lista(
        cls,
        permissions: list[Permission] | QuerySet[Permission],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Converte lista/queryset de permissões em dicionários."""
        from permissoes.serializers import PermissionSerializer

        return PermissionSerializer(permissions, many=True, **kwargs).data

    @classmethod
    def listar_todas(cls) -> QuerySet[Permission]:
        """Lista todas as permissões com content_type, ordenadas."""
        return (
            Permission.objects.select_related("content_type")
            .all()
            .order_by("content_type__app_label", "id")
        )

    @classmethod
    def listar_por_codenames(
        cls, codenames: list[str]
    ) -> QuerySet[Permission]:
        """Retorna permissões cujos codenames estão na lista."""
        return Permission.objects.filter(codename__in=codenames)

    @classmethod
    def existe_por_content_type_e_codename(
        cls, content_type: ContentType, codename: str
    ) -> bool:
        """Verifica se já existe permissão para o content type e codename."""
        return Permission.objects.filter(
            content_type=content_type, codename=codename
        ).exists()

    @classmethod
    def criar(
        cls,
        *,
        name: str,
        codename: str,
        content_type: ContentType,
    ) -> Permission:
        """Cria e persiste uma permissão."""
        return Permission.objects.create(
            name=name,
            codename=codename,
            content_type=content_type,
        )

    @classmethod
    def get_or_create(
        cls,
        *,
        codename: str,
        content_type: ContentType,
        name: str,
    ) -> tuple[Permission, bool]:
        """Obtém ou cria permissão pelo codename e content_type."""
        return Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={"name": name},
        )

    @classmethod
    def obter_por_codename_e_content_type(
        cls, *, codename: str, app_label: str, model: str
    ) -> Permission:
        """Retorna permissão por codename e content type (raises)."""
        return Permission.objects.get(
            codename=codename,
            content_type__app_label=app_label,
            content_type__model=model,
        )

    @classmethod
    def permissoes_do_usuario(
        cls,
        user: User,
        models_filter: list[str] | None = None,
    ) -> QuerySet[Permission]:
        """Retorna permissões diretas e de grupos do usuário, distintas."""
        permissoes_diretas = user.user_permissions.select_related(
            "content_type"
        )
        permissoes_grupos = Permission.objects.filter(
            group__user=user
        ).select_related("content_type")
        permissoes = (permissoes_diretas | permissoes_grupos).distinct()
        if models_filter:
            permissoes = permissoes.filter(
                content_type__model__in=models_filter
            )
        return permissoes.order_by("content_type__app_label", "codename")


class GroupRepository:
    """Consultas e persistência de Group."""

    @staticmethod
    def serializar(group: Group, **kwargs: Any) -> dict[str, Any]:
        """Converte um grupo em dicionário."""
        from permissoes.serializers import GroupSerializer

        return GroupSerializer(group, **kwargs).data

    @classmethod
    def serializar_lista(
        cls,
        groups: list[Group] | QuerySet[Group],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Converte lista/queryset de grupos em dicionários."""
        from permissoes.serializers import GroupSerializer

        return GroupSerializer(groups, many=True, **kwargs).data

    @classmethod
    def listar_com_permissoes(
        cls, nome: str | None = None
    ) -> QuerySet[Group]:
        """Lista grupos com permissões, opcionalmente filtrados."""
        qs = Group.objects.prefetch_related(
            "permissions__content_type"
        ).order_by("name")
        if nome:
            qs = qs.filter(name=nome)
        return qs

    @classmethod
    def obter_por_nome(cls, nome: str) -> Group | None:
        """Retorna o grupo pelo nome, ou None."""
        return Group.objects.filter(name=nome).first()

    @classmethod
    def existe_por_nome(cls, nome: str) -> bool:
        """Verifica se já existe grupo com o nome informado."""
        return Group.objects.filter(name=nome).exists()

    @classmethod
    def listar_por_nomes(cls, nomes: list[str] | set[str]) -> QuerySet[Group]:
        """Retorna grupos cujos nomes estão na lista."""
        return Group.objects.filter(name__in=nomes)

    @classmethod
    def nomes_existentes(cls, nomes: list[str] | set[str]) -> set[str]:
        """Retorna o subconjunto de nomes que existem no cadastro."""
        return set(
            Group.objects.filter(name__in=nomes).values_list("name", flat=True)
        )

    @classmethod
    def criar(cls, nome: str) -> Group:
        """Cria e persiste um grupo."""
        return Group.objects.create(name=nome)

    @classmethod
    def get_or_create(cls, nome: str) -> tuple[Group, bool]:
        """Obtém ou cria grupo pelo nome."""
        return Group.objects.get_or_create(name=nome)

    @classmethod
    def salvar(cls, group: Group) -> None:
        """Persiste alterações em um grupo."""
        group.save()

    @classmethod
    def adicionar_permissoes(cls, group: Group, permissoes: Any) -> None:
        """Associa permissões ao grupo."""
        group.permissions.add(*permissoes)

    @classmethod
    def remover_permissoes(cls, group: Group, permissoes: Any) -> None:
        """Remove permissões do grupo."""
        group.permissions.remove(*permissoes)

    @classmethod
    def definir_permissoes(cls, group: Group, permissoes: Any) -> None:
        """Substitui o conjunto de permissões do grupo."""
        group.permissions.set(permissoes)

    @classmethod
    def adicionar_usuarios(cls, group: Group, users: Any) -> None:
        """Associa usuários ao grupo."""
        group.user_set.add(*users)

    @classmethod
    def remover_usuarios(cls, group: Group, users: Any) -> None:
        """Remove usuários do grupo."""
        group.user_set.remove(*users)
