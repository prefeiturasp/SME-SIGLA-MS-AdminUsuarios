from rest_framework import serializers


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    token = serializers.CharField(required=False)
    user = serializers.DictField(child=serializers.CharField(), required=False)


class LoginSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True)


class EsqueciSenhaSerializer(serializers.Serializer):
    rf = serializers.CharField()

