"""Serializers compartilhados do projeto."""

from rest_framework import serializers


class ErroDetalheSerializer(serializers.Serializer):
    """Erro com mensagem única."""

    detail = serializers.CharField(help_text="Mensagem que descreve o erro.")


class MotivoTokenSerializer(serializers.Serializer):
    """Motivo da rejeição de um token JWT."""

    token_class = serializers.CharField(
        help_text="Classe de token avaliada, por exemplo `AccessToken`."
    )
    token_type = serializers.CharField(
        help_text="Tipo de token avaliado, por exemplo `access`."
    )
    message = serializers.CharField(help_text="Motivo da rejeição.")


class ErroAcessoSerializer(serializers.Serializer):
    """Erro de autenticação."""

    detail = serializers.CharField(help_text="Mensagem que descreve o erro.")
    code = serializers.CharField(
        required=False,
        help_text=(
            "Código do erro. Presente quando o token JWT é rejeitado "
            "(`token_not_valid`) ou quando o usuário do token está inativo "
            "(`user_inactive`)."
        ),
    )
    messages = MotivoTokenSerializer(
        many=True,
        required=False,
        help_text="Motivos da rejeição do token JWT, quando houver.",
    )


class ErrosValidacaoSerializer(serializers.Serializer):
    """Erros de validação no formato padrão do Django REST Framework."""
