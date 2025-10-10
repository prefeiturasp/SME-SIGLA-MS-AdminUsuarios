import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from usuarios.exceptions import (
    AutenticacaoRespostaInvalidaError,
    AutenticacaoRequisicaoError,
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoUpstreamError,
)

logger = logging.getLogger(__name__)


class AutenticacaoService:
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {settings.CORESSO_API_TOKEN}'}
    DEFAULT_TIMEOUT = 10

    @classmethod
    def autentica(cls, login, senha) -> Dict[str, Any]:
        payload = {'login': login, 'senha': senha}
        try:
            logger.info("Autenticando no coresso. Login: %s", login)
            response = requests.post(
                f"{settings.CORESSO_API_URL}/autenticacao/",
                headers=cls.DEFAULT_HEADERS,
                timeout=cls.DEFAULT_TIMEOUT,
                json=payload
            )
            try:
                data = response.json()
            except Exception as exc:
                raise AutenticacaoRespostaInvalidaError("Resposta inválida do serviço de autenticação") from exc
            if response.status_code == 401:
                raise AutenticacaoCredenciaisInvalidasError("Credenciais inválidas")
            if response.status_code < 200 or response.status_code >= 300:
                raise AutenticacaoUpstreamError("Erro no serviço de autenticação")
            return data
        except requests.RequestException as exc:
            logger.info("ERROR request - %s", str(exc))
            raise AutenticacaoRequisicaoError("Falha ao conectar com serviço de autenticação") from exc
        except Exception as exc:
            logger.info("ERROR - %s", str(exc))
            raise


    @classmethod
    def gerar_tokens_para_usuario(cls, user: User) -> Dict[str, str]:
        """Gera par de tokens JWT (access/refresh) para o usuário informado."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


    @classmethod
    def montar_resposta_login(cls, dados: Any, user: User) -> Dict[str, Any]:
        """Monta o payload de resposta do login mesclando dados externos e gerando tokens locais."""
        resposta: Dict[str, Any] = {}
        if isinstance(dados, dict):
            resposta.update(dados)
        tokens = cls.gerar_tokens_para_usuario(user)
        resposta['token'] = tokens['access']
        return resposta

