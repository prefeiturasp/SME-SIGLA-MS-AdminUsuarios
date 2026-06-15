"""Módulo serializers/login."""

from rest_framework import serializers


class LoginResponseSerializer(serializers.Serializer):
    """Serializer do modelo LoginResponse."""

    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    token = serializers.CharField(required=False)
    user = serializers.DictField(child=serializers.CharField(), required=False)


class LoginSerializer(serializers.Serializer):
    """Serializer do modelo Login."""

    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True)


class EsqueciSenhaSerializer(serializers.Serializer):
    """Serializer do modelo EsqueciSenha."""

    rf = serializers.CharField()
