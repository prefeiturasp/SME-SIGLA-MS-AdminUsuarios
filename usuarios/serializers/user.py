"""Módulo serializers/user."""

from rest_framework import serializers


class BuscarUsuarioEolSerializer(serializers.Serializer):
    """Define BuscarUsuarioEolSerializer."""

    rf = serializers.CharField()


class CreateUserSerializer(serializers.Serializer):
    """Define CreateUserSerializer."""

    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.EmailField()
