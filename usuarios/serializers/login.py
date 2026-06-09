"""Módulo serializers/login."""
from rest_framework import serializers


class LoginResponseSerializer(serializers.Serializer):
    """Define LoginResponseSerializer."""
    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    token = serializers.CharField(required=False)
    user = serializers.DictField(child=serializers.CharField(), required=False)


class LoginSerializer(serializers.Serializer):
    """Define LoginSerializer."""
    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True)


class EsqueciSenhaSerializer(serializers.Serializer):
    """Define EsqueciSenhaSerializer."""
    rf = serializers.CharField()
