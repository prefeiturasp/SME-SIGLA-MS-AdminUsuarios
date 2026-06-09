"""Módulo serializers/password."""
from __future__ import annotations
from typing import Any
import re
from rest_framework import serializers

class ChangePasswordSerializer(serializers.Serializer):
    """Define ChangePasswordSerializer."""
    user_id = serializers.CharField()
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class CriarNovaSenhaSerializer(serializers.Serializer):
    """Define CriarNovaSenhaSerializer."""
    uid = serializers.CharField()
    token = serializers.CharField()
    nova_senha = serializers.CharField(write_only=True, min_length=6)

class AlterarSenhaSerializer(serializers.Serializer):
    """Define AlterarSenhaSerializer."""
    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(write_only=True)
    confirmacao_nova_senha = serializers.CharField(write_only=True)

    def validate_nova_senha(self, value: Any) -> Any:
        """Executa validate nova senha.
        
        Args:
            self: Instância do objeto.
            value: Valor recebido para validação.
        
        Returns:
            Valor validado do campo nova senha.
        
        Raises:
            ValidationError: Se ocorrer erro nesta operação.
        """
        if len(value) < 8 or len(value) > 12:
            raise serializers.ValidationError('A senha deve ter entre 8 e 12 caracteres.')
        if not re.search('[A-Z]', value):
            raise serializers.ValidationError('A senha deve conter ao menos uma letra maiúscula.')
        if not re.search('[a-z]', value):
            raise serializers.ValidationError('A senha deve conter ao menos uma letra minúscula.')
        if not re.search('[0-9]', value):
            raise serializers.ValidationError('A senha deve conter ao menos um número.')
        if not re.search('[^A-Za-z0-9]', value):
            raise serializers.ValidationError('A senha deve conter ao menos um símbolo.')
        if re.search('\\s', value):
            raise serializers.ValidationError('A senha não deve conter espaços em branco.')
        if re.search('[À-ÿ]', value):
            raise serializers.ValidationError('A senha não deve conter caracteres acentuados.')
        return value

    def validate(self, attrs: Any) -> Any:
        """Executa validate.
        
        Args:
            self: Instância do objeto.
            attrs: Atributos em validação.
        
        Returns:
            Resultado da operação.
        
        Raises:
            ValidationError: Se ocorrer erro nesta operação.
        """
        if attrs['nova_senha'] != attrs['confirmacao_nova_senha']:
            raise serializers.ValidationError({'confirmacao_nova_senha': 'As senhas não conferem.'})
        return attrs
