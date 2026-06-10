"""Módulo services/sme_integracao."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from rest_framework import status

from usuarios.exceptions import SmeIntegracaoException

logger = logging.getLogger(__name__)


class SmeIntegracaoService:
    """Serviço para operações de smeintegracao."""

    DEFAULT_HEADERS = {
        "accept": "application/json",
        "x-api-eol-key": settings.SME_INTEGRACAO_TOKEN,
    }
    DEFAULT_TIMEOUT = 10

    @classmethod
    def informacao_usuario(cls, username: Any) -> Any:
        """Informacao usuario.

        Args:
            cls: Classe referenciada.
            username: Username utilizado na operação.

        Returns:
            Valor calculado conforme a regra aplicada.

        Raises:
            SmeIntegracaoException: Se ocorrer erro nesta operação.
            RequestException: Se a chamada HTTP falhar.
        """
        logger.info(f"Consultando dados na API externa para: {username}")
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/{username}/dados"  # noqa: E501
            response = requests.get(
                url, headers=cls.DEFAULT_HEADERS, timeout=10
            )
            if response.status_code == status.HTTP_200_OK:
                return response.json()
            else:
                logger.info(f"Dados não encontrados: {response}")
                raise SmeIntegracaoException("Dados não encontrados.")
        except requests.RequestException as err:
            logger.exception("Erro de conexão com a API externa")
            raise requests.RequestException(
                "Erro ao conectar-se à API externa."
            ) from err

    @classmethod
    def redefine_senha(cls, registro_funcional: Any, senha: Any) -> Any:
        """Redefine senha.

        Args:
            cls: Classe referenciada.
            registro_funcional: Registro funcional utilizado na operação.
            senha: Senha informada para autenticação.

        Returns:
            Valor calculado conforme a regra aplicada.

        Raises:
            SmeIntegracaoException: Se ocorrer erro nesta operação.
        """
        if not registro_funcional or not senha:
            raise SmeIntegracaoException(
                "Registro funcional e senha são obrigatórios"
            )
        logger.info(
            "Iniciando redefinição de senha no CoreSSO para usuário: %s",
            registro_funcional,
        )
        data = {"Usuario": registro_funcional, "Senha": senha}
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/AlterarSenha"  # noqa: E501
            response = requests.post(
                url, data=data, headers=cls.DEFAULT_HEADERS
            )
            if response.status_code == status.HTTP_200_OK:
                result = "OK"
                return result
            else:
                texto = response.content.decode("utf-8")
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao redefinir senha: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err)) from err

    @classmethod
    def alterar_email(cls, registro_funcional: Any, email: Any) -> Any:
        """Alterar email.

        Args:
            cls: Classe referenciada.
            registro_funcional: Registro funcional utilizado na operação.
            email: Email utilizado na operação.

        Returns:
            Valor calculado conforme a regra aplicada.

        Raises:
            SmeIntegracaoException: Se ocorrer erro nesta operação.
        """
        if not registro_funcional or not email:
            raise SmeIntegracaoException(
                "Registro funcional e email são obrigatórios"
            )
        logger.info(
            "Iniciando alteração de email no CoreSSO para usuário: %s",
            registro_funcional,
        )
        data = {"Usuario": registro_funcional, "Email": email}
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/AlterarEmail"  # noqa: E501
            response = requests.post(
                url, data=data, headers=cls.DEFAULT_HEADERS
            )
            if response.status_code == status.HTTP_200_OK:
                return "OK"
            else:
                texto = response.content.decode("utf-8")
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao alterar email: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err)) from err
