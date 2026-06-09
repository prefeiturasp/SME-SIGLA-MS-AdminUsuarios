"""Módulo serializers/email."""
from __future__ import annotations
from typing import Any
from django.contrib.auth.models import User
from rest_framework import serializers

class AlterarEmailSerializer(serializers.Serializer):
    """Define AlterarEmailSerializer."""
    novo_email = serializers.EmailField()

    def validate_novo_email(self, value: Any) -> Any:
        """Executa validate novo email."""
        user = self.context.get('user')
        if user is None:
            raise serializers.ValidationError('Usuário não fornecido no contexto.')
        qs = User.objects.filter(email__iexact=value)
        if user.id:
            qs = qs.exclude(id=user.id)
        if qs.exists():
            raise serializers.ValidationError('E-mail já está cadastrado.')
        return value
