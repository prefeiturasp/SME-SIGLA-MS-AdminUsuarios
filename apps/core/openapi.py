"""Blocos compartilhados da documentação OpenAPI do microsserviço."""

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import (
    Direction,
    OpenApiExample,
    OpenApiResponse,
    PolymorphicProxySerializer,
)

from core.serializers import (
    ErroAcessoSerializer,
    ErroDetalheSerializer,
    ErrosValidacaoSerializer,
)

# O drf-spectacular tipa `auth` como lista de str, mas publica o valor
# como está em `security`, que é uma lista de objetos.
AUTENTICACAO_JWT: list[Any] = [{"jwtAuth": []}]

EXEMPLO_SEM_CREDENCIAL = {
    "detail": "API key não informada no cabeçalho da requisição"
}

EXEMPLO_TOKEN_INVALIDO = {
    "detail": "O token informado não é válido para qualquer tipo de token",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "O token é inválido",
        }
    ],
}

EXEMPLO_USUARIO_INATIVO = {
    "detail": "Usuário está inativo",
    "code": "user_inactive",
}


class ErrosValidacaoExtension(OpenApiSerializerExtension):
    """Descreve ``ErrosValidacaoSerializer`` como mapa campo → mensagens."""

    target_class = ErrosValidacaoSerializer

    def map_serializer(
        self, auto_schema: AutoSchema, direction: Direction
    ) -> dict[str, Any]:
        """Retorna o schema do mapa de erros de validação."""
        return {
            "type": "object",
            "description": (
                "Erros de validação. Cada chave é o nome de um campo "
                "inválido (ou `non_field_errors`, para erros que dependem "
                "de mais de um campo) e o valor é a lista de mensagens. Em "
                "campos que são listas, o valor é um objeto que liga a "
                "posição do item inválido às mensagens dele."
            ),
            "additionalProperties": {
                "oneOf": [
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "object", "additionalProperties": True},
                ]
            },
        }


ERRO_REQUISICAO = PolymorphicProxySerializer(
    component_name="ErroRequisicao",
    serializers=[ErrosValidacaoSerializer, ErroDetalheSerializer],
    resource_type_field_name=None,
    many=False,
)


def resposta(
    modelo: Any, descricao: str, exemplos: dict[str, Any] | None = None
) -> OpenApiResponse:
    """Monta uma resposta documentada com exemplos nomeados.

    Args:
        modelo: Serializer que descreve o corpo, ou ``None`` se não há corpo.
        descricao: Texto exibido para o código de resposta.
        exemplos: Valores de exemplo, indexados pelo nome do exemplo.

    Returns:
        Resposta pronta para o ``responses`` de ``extend_schema``.
    """
    return OpenApiResponse(
        response=modelo,
        description=descricao,
        examples=[
            OpenApiExample(nome, value=valor)
            for nome, valor in (exemplos or {}).items()
        ],
    )


def exemplos_requisicao(exemplos: dict[str, Any]) -> list[OpenApiExample]:
    """Monta exemplos nomeados para o corpo da requisição.

    Args:
        exemplos: Valores de exemplo, indexados pelo nome do exemplo.

    Returns:
        Exemplos prontos para o ``examples`` de ``extend_schema``.
    """
    return [
        OpenApiExample(nome, value=valor, request_only=True)
        for nome, valor in exemplos.items()
    ]


RESPOSTA_ACESSO_NEGADO = resposta(
    ErroAcessoSerializer,
    (
        "Chamada sem credencial ou com credencial recusada: token JWT "
        "ausente, inválido ou expirado, ou usuário inativo. O serviço "
        "responde 403 nesses casos, e não 401. Sem credencial, a mensagem "
        "cita a chave de API, embora a rota precise do token JWT."
    ),
    {
        "Sem credencial": EXEMPLO_SEM_CREDENCIAL,
        "Token JWT inválido": EXEMPLO_TOKEN_INVALIDO,
        "Usuário inativo": EXEMPLO_USUARIO_INATIVO,
    },
)

RESPOSTA_ERRO_INTERNO = resposta(
    None,
    "Erro inesperado no servidor. O corpo não segue um modelo JSON.",
)


def respostas(especificas: dict[int, Any]) -> dict[int, Any]:
    """Junta as respostas da operação à de erro interno.

    O 403 não entra aqui: só as rotas autenticadas o devolvem, e cada uma
    o declara.

    Args:
        especificas: Respostas próprias da operação, por código HTTP.

    Returns:
        Respostas ordenadas por código, incluindo o 500.
    """
    return dict(sorted({500: RESPOSTA_ERRO_INTERNO, **especificas}.items()))
