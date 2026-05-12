from rest_framework import serializers


class BuscarUsuarioEolSerializer(serializers.Serializer):
    rf = serializers.CharField()


class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True)

