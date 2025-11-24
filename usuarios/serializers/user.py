from rest_framework import serializers


class CreateUserSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    senha = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    
    def validate(self, data):
        # Converte usuario -> username e senha -> password após validação
        data['username'] = data.pop('usuario')
        data['password'] = data.pop('senha')
        return data


