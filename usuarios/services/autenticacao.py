"""Módulo services/autenticacao."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.exceptions import (
    AutenticacaoCredenciaisInvalidasError,
    AutenticacaoRequisicaoError,
    AutenticacaoRespostaInvalidaError,
    AutenticacaoUpstreamError,
)

logger = logging.getLogger(__name__)


class AutenticacaoService:
    """Serviço para operações de autenticacao."""

    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "x-api-eol-key": settings.SME_INTEGRACAO_TOKEN,
    }
    DEFAULT_TIMEOUT = 100

    @classmethod
    def autentica(cls, login: Any, senha: Any) -> dict[str, Any]:
        """Autentica o usuário no serviço externo.

        Args:
            cls: Classe referenciada.
            login: Identificador de login do usuário.
            senha: Senha informada para autenticação.

        Returns:
            Dicionário com os dados retornados pela operação.

        Raises:
            AutenticacaoCredenciaisInvalidasError: Login ou senha incorretos.
            AutenticacaoUpstreamError: Erro retornado pelo serviço externo.
            AutenticacaoRequisicaoError: Falha de conexão com o serviço.
            AutenticacaoRespostaInvalidaError: Resposta inválida do serviço.
        """
        payload = {"usuario": login, "senha": senha, "codigoSistema": 1}
        try:
            logger.info("Autenticando no coresso. Login: %s", login)
            response = requests.post(
                f"{settings.SME_INTEGRACAO_URL}/api/v1/autenticacao/externa",
                headers=cls.DEFAULT_HEADERS,
                timeout=cls.DEFAULT_TIMEOUT,
                json=payload,
            )
            try:
                data = response.json()
            except Exception as exc:
                raise AutenticacaoRespostaInvalidaError(
                    "Resposta inválida do serviço de autenticação"
                ) from exc
            if response.status_code == 401:
                raise AutenticacaoCredenciaisInvalidasError(
                    "Credenciais inválidas"
                )
            if response.status_code < 200 or response.status_code >= 300:
                raise AutenticacaoUpstreamError(
                    "Erro no serviço de autenticação"
                )
            return data  # type: ignore[no-any-return]
        except requests.RequestException as exc:
            logger.info("ERROR request - %s", str(exc))
            raise AutenticacaoRequisicaoError(
                "Falha ao conectar com serviço de autenticação"
            ) from exc
        except Exception as exc:
            logger.info("ERROR - %s", str(exc))
            raise

    @classmethod
    def gerar_tokens_para_usuario(cls, user: User) -> dict[str, str]:
        """Gera tokens para usuario.

        Args:
            cls: Classe referenciada.
            user: User utilizado na operação.

        Returns:
            Dicionário com os dados retornados pela operação.
        """
        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}

    @classmethod
    def montar_resposta_login(cls, dados: Any, user: User) -> dict[str, Any]:
        """Monta resposta login.

        Args:
            cls: Classe referenciada.
            dados: Dados utilizado na operação.
            user: User utilizado na operação.

        Returns:
            Dicionário com os dados retornados pela operação.
        """
        resposta: dict[str, Any] = {}
        if isinstance(dados, dict):
            resposta.update(dados)
        tokens = cls.gerar_tokens_para_usuario(user)
        resposta["token"] = tokens["access"]
        return resposta

    @classmethod
    def atualizar_usuario_com_dados_autenticacao(
        cls, *, user: User, dados: Any, senha: str
    ) -> User:
        """Atualiza usuario com dados autenticacao.

        Args:
            cls: Classe referenciada.
            user: User utilizado na operação.
            dados: Dados utilizado na operação.
            senha: Senha informada para autenticação.

        Returns:
            Valor calculado conforme a regra aplicada.
        """
        if not isinstance(dados, dict):
            return user
        nome = dados.get("nome")
        email = dados.get("email")
        update_fields = []
        if isinstance(nome, str):
            nome = nome.strip()
            if nome:
                parts = [p for p in nome.split(" ") if p]
                first_name = parts[0] if parts else ""
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    update_fields.append("first_name")
                if user.last_name != last_name:
                    user.last_name = last_name
                    update_fields.append("last_name")
        if isinstance(email, str):
            email = email.strip()
            if email and user.email != email:
                user.email = email
                update_fields.append("email")
        user.set_password(senha)
        update_fields.append("password")
        if update_fields:
            user.save(update_fields=update_fields)
        return user
