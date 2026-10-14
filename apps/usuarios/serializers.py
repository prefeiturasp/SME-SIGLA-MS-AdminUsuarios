"""Serializers de autenticação e cadastro de usuários."""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers

from usuarios.repository import UserRepository


class LoginSerializer(serializers.Serializer):
    """Credenciais do login."""

    usuario = serializers.CharField(
        help_text="Registro funcional (RF) do usuário, usado como login."
    )
    senha = serializers.CharField(
        write_only=True,
        help_text="Senha do usuário no serviço de autenticação da SME.",
    )


class EsqueciSenhaSerializer(serializers.Serializer):
    """Identificação de quem pede a recuperação de senha."""

    rf = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text=(
            "Registro funcional do usuário. Informe `rf` ou `email`, "
            "nunca os dois."
        ),
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=False,
        help_text=(
            "E-mail do cadastro do usuário, sem diferenciar maiúsculas de "
            "minúsculas. Informe `rf` ou `email`, nunca os dois."
        ),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Exige rf ou email (apenas um identificador)."""
        rf = attrs.get("rf")
        email = attrs.get("email")
        if bool(rf) == bool(email):
            raise serializers.ValidationError(
                "Informe rf ou email (apenas um)."
            )
        return attrs


class CriarNovaSenhaSerializer(serializers.Serializer):
    """Nova senha, com os dados do link de recuperação."""

    uid = serializers.CharField(
        help_text=(
            "Identificador do usuário, recebido no link do e-mail de "
            "recuperação."
        )
    )
    token = serializers.CharField(
        help_text=(
            "Token recebido no mesmo link. Deixa de valer depois que a "
            "senha é trocada."
        )
    )
    nova_senha = serializers.CharField(
        write_only=True,
        min_length=6,
        help_text="Nova senha, com no mínimo 6 caracteres.",
    )


class AlterarSenhaSerializer(serializers.Serializer):
    """Senha atual e nova senha do usuário autenticado."""

    senha_atual = serializers.CharField(
        write_only=True,
        help_text="Senha atual, a mesma usada no último login.",
    )
    nova_senha = serializers.CharField(
        write_only=True,
        help_text=(
            "Nova senha: de 8 a 12 caracteres, com ao menos uma letra "
            "maiúscula, uma minúscula, um número e um símbolo, sem "
            "espaços e sem acentos."
        ),
    )
    confirmacao_nova_senha = serializers.CharField(
        write_only=True, help_text="Repetição da nova senha."
    )

    def validate_nova_senha(self, value: Any) -> Any:
        """Valida nova senha."""
        if len(value) < 8 or len(value) > 12:
            raise serializers.ValidationError(
                "A senha deve ter entre 8 e 12 caracteres."
            )
        if not re.search("[A-Z]", value):
            raise serializers.ValidationError(
                "A senha deve conter ao menos uma letra maiúscula."
            )
        if not re.search("[a-z]", value):
            raise serializers.ValidationError(
                "A senha deve conter ao menos uma letra minúscula."
            )
        if not re.search("[0-9]", value):
            raise serializers.ValidationError(
                "A senha deve conter ao menos um número."
            )
        if not re.search("[^A-Za-z0-9]", value):
            raise serializers.ValidationError(
                "A senha deve conter ao menos um símbolo."
            )
        if re.search("\\s", value):
            raise serializers.ValidationError(
                "A senha não deve conter espaços em branco."
            )
        if re.search("[À-ÿ]", value):
            raise serializers.ValidationError(
                "A senha não deve conter caracteres acentuados."
            )
        return value

    def validate(self, attrs: Any) -> Any:
        """Validate."""
        if attrs["nova_senha"] != attrs["confirmacao_nova_senha"]:
            raise serializers.ValidationError(
                {"confirmacao_nova_senha": "As senhas não conferem."}
            )
        return attrs


class AlterarEmailSerializer(serializers.Serializer):
    """Novo e-mail do usuário autenticado."""

    novo_email = serializers.EmailField(
        help_text="Novo e-mail. Não pode estar em uso por outro usuário."
    )

    def validate_novo_email(self, value: Any) -> Any:
        """Valida novo email."""
        user = self.context.get("user")
        if user is None:
            raise serializers.ValidationError(
                "Usuário não fornecido no contexto."
            )
        if UserRepository.existe_email_em_outro_usuario(value, user.id):
            raise serializers.ValidationError("E-mail já está cadastrado.")
        return value


class BuscarUsuarioEolSerializer(serializers.Serializer):
    """Registro funcional a consultar no EOL."""

    rf = serializers.CharField(help_text="Registro funcional do servidor.")


class CreateUserSerializer(serializers.Serializer):
    """Dados do usuário a cadastrar."""

    username = serializers.CharField(
        help_text="Registro funcional do usuário, usado como login."
    )
    nome = serializers.CharField(
        help_text=(
            "Nome completo. A primeira palavra é gravada como nome e o "
            "restante, como sobrenome."
        )
    )
    email = serializers.EmailField(
        help_text="E-mail do usuário. Não pode repetir o de outro usuário."
    )


class UserSerializer(serializers.ModelSerializer):
    """Serializer de leitura do User."""

    class Meta:
        """Representa Meta."""

        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class LoginRespostaSerializer(serializers.Serializer):
    """Dados de acesso devolvidos pelo login.

    Além de `token`, traz os dados que o serviço de autenticação da SME
    devolve, repassados sem alteração.
    """

    token = serializers.CharField(
        help_text=(
            "Token JWT de acesso, válido por 7 dias. Vai no header "
            "`Authorization: Bearer <token>`."
        )
    )
    nome = serializers.CharField(
        required=False,
        help_text=(
            "Nome do usuário na SME. Quando vem, atualiza o cadastro local."
        ),
    )
    email = serializers.CharField(
        required=False,
        help_text=(
            "E-mail do usuário na SME. Quando vem, atualiza o cadastro "
            "local."
        ),
    )


class RecuperacaoSenhaRespostaSerializer(serializers.Serializer):
    """Confirmação do envio do e-mail de recuperação de senha."""

    usuario = serializers.CharField(
        help_text="Registro funcional do usuário encontrado."
    )
    email = serializers.CharField(
        help_text=(
            "E-mail para o qual o link foi enviado, mascarado: só a "
            "primeira e a última letra antes do `@` aparecem."
        )
    )
    email_enviado = serializers.BooleanField(help_text="Sempre `true`.")


class ConfirmacaoSerializer(serializers.Serializer):
    """Confirmação de que a operação foi concluída."""

    detail = serializers.CharField(help_text="Mensagem de confirmação.")


class UsuarioCriadoSerializer(serializers.Serializer):
    """Confirmação do cadastro de um usuário."""

    detail = serializers.CharField(help_text="Mensagem de confirmação.")
    user = serializers.CharField(
        help_text="Registro funcional do usuário criado."
    )


class UsuarioEolSerializer(serializers.Serializer):
    """Dados de um servidor encontrados no EOL."""

    username = serializers.CharField(
        help_text="Registro funcional consultado."
    )
    nome = serializers.CharField(
        allow_blank=True, help_text="Nome do servidor no EOL."
    )
    email = serializers.CharField(
        allow_blank=True, help_text="E-mail do servidor no EOL."
    )


class MeusDadosSerializer(serializers.Serializer):
    """Dados do usuário autenticado."""

    rf = serializers.CharField(help_text="Registro funcional do usuário.")
    nome_completo = serializers.CharField(
        allow_blank=True, help_text="Nome e sobrenome do usuário."
    )
    email = serializers.CharField(
        allow_blank=True, help_text="E-mail do cadastro local."
    )
    perfil_acesso = serializers.ListField(
        child=serializers.CharField(),
        help_text="Nomes dos grupos a que o usuário pertence.",
    )
