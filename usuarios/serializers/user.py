"""Módulo serializers/user."""

from rest_framework import serializers


class BuscarUsuarioEolSerializer(serializers.Serializer):
    """Serializer do modelo BuscarUsuarioEol."""

    rf = serializers.CharField()


class CreateUserSerializer(serializers.Serializer):
    """Serializer do modelo CreateUser."""

    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.EmailField()
