"""Serializers de autenticação e cadastro de usuários."""

from __future__ import annotations

import re
from typing import Any

from rest_framework import serializers

from usuarios.repository import UserRepository


class LoginSerializer(serializers.Serializer):
    """Serializer do modelo Login."""

    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True)


class EsqueciSenhaSerializer(serializers.Serializer):
    """Serializer do modelo EsqueciSenha."""

    rf = serializers.CharField()


class CriarNovaSenhaSerializer(serializers.Serializer):
    """Serializer do modelo CriarNovaSenha."""

    uid = serializers.CharField()
    token = serializers.CharField()
    nova_senha = serializers.CharField(write_only=True, min_length=6)


class AlterarSenhaSerializer(serializers.Serializer):
    """Serializer do modelo AlterarSenha."""

    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(write_only=True)
    confirmacao_nova_senha = serializers.CharField(write_only=True)

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
    """Serializer do modelo AlterarEmail."""

    novo_email = serializers.EmailField()

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
    """Serializer do modelo BuscarUsuarioEol."""

    rf = serializers.CharField()


class CreateUserSerializer(serializers.Serializer):
    """Serializer do modelo CreateUser."""

    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.EmailField()
