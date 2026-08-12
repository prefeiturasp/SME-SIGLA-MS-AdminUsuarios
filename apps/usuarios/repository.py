"""Repositório de acesso a dados de User (app usuarios)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.db.models import QuerySet


class UserRepository:
    """Consultas e persistência de usuários."""

    @staticmethod
    def serializar(
        user: User,
        serializer_class: type,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Converte um usuário em dicionário via serializer informado."""
        return serializer_class(user, **kwargs).data

    @classmethod
    def serializar_lista(
        cls,
        users: list[User] | QuerySet[User],
        serializer_class: type,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Converte lista/queryset de usuários via serializer informado."""
        return serializer_class(users, many=True, **kwargs).data

    @classmethod
    def buscar_todos(cls) -> QuerySet[User]:
        """Retorna o queryset base de todos os usuários."""
        return User.objects.all()

    @classmethod
    def listar_com_grupos(
        cls, username_filtro: str | None = None
    ) -> QuerySet[User]:
        """Lista usuários com grupos, opcionalmente filtrados."""
        qs = User.objects.all().prefetch_related("groups").order_by("username")
        if username_filtro:
            qs = qs.filter(username__icontains=username_filtro)
        return qs

    @classmethod
    def obter_por_username(cls, username: str) -> User | None:
        """Retorna o usuário pelo username, ou None."""
        return User.objects.filter(username=username).first()

    @classmethod
    def obter_por_username_com_grupos(cls, username: str) -> User | None:
        """Retorna o usuário com groups prefetch pelo username, ou None."""
        return (
            User.objects.filter(username=username)
            .prefetch_related("groups")
            .first()
        )

    @classmethod
    def obter_por_username_apenas_id(cls, username: str) -> User | None:
        """Retorna o usuário pelo username carregando apenas o id."""
        return User.objects.filter(username=username).only("id").first()

    @classmethod
    def obter_por_pk(cls, pk: Any) -> User:
        """Retorna o usuário pela PK (raises DoesNotExist)."""
        return User.objects.get(pk=pk)

    @classmethod
    def existe_por_username(cls, username: str) -> bool:
        """Verifica se já existe usuário com o username informado."""
        return User.objects.filter(username=username).exists()

    @classmethod
    def existe_por_email(cls, email: str) -> bool:
        """Verifica se já existe usuário com o e-mail informado."""
        return User.objects.filter(email__iexact=email).exists()

    @classmethod
    def existe_email_em_outro_usuario(
        cls, email: str, user_id: int | None
    ) -> bool:
        """Verifica se o e-mail está em uso por outro usuário."""
        qs = User.objects.filter(email__iexact=email)
        if user_id:
            qs = qs.exclude(id=user_id)
        return qs.exists()

    @classmethod
    def criar(
        cls,
        *,
        username: str,
        email: str = "",
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        **extra: Any,
    ) -> User:
        """Cria e persiste um usuário."""
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    @classmethod
    def salvar(
        cls,
        user: User,
        *,
        campos_atualizacao: list[str] | None = None,
    ) -> None:
        """Persiste alterações em um usuário."""
        if campos_atualizacao:
            user.save(update_fields=campos_atualizacao)
        else:
            user.save()

    @classmethod
    def filtrar_nao_superusers(cls) -> QuerySet[User]:
        """Retorna queryset de usuários que não são superusuários."""
        return User.objects.filter(is_superuser=False)

    @classmethod
    def contar_nao_superusers(cls) -> int:
        """Conta usuários que não são superusuários."""
        return User.objects.filter(is_superuser=False).count()

    @classmethod
    def excluir_queryset(
        cls, qs: QuerySet[User]
    ) -> tuple[int, dict[str, int]]:
        """Exclui o queryset informado."""
        return qs.delete()

    @classmethod
    def listar_por_usernames(cls, usernames: list[str]) -> QuerySet[User]:
        """Retorna usuários cujos usernames estão na lista."""
        return User.objects.filter(username__in=usernames)

    @classmethod
    def nomes_grupos(cls, user: User) -> list[str]:
        """Retorna os nomes dos grupos do usuário ordenados."""
        return list(
            user.groups.order_by("name").values_list("name", flat=True)
        )

    @classmethod
    def nomes_grupos_sem_ordem(cls, user: User) -> list[str]:
        """Retorna os nomes dos grupos do usuário sem ordenação."""
        return list(user.groups.values_list("name", flat=True))

    @classmethod
    def adicionar_grupos(cls, user: User, grupos: Any) -> None:
        """Associa os grupos informados ao usuário."""
        user.groups.add(*grupos)

    @classmethod
    def remover_grupos(cls, user: User, grupos: Any) -> None:
        """Remove os grupos informados do usuário."""
        user.groups.remove(*grupos)
