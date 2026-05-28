import logging

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


class TokenService:
    """
    Serviço para gerar tokens para reset de senha.
    """

    @classmethod
    def gerar_token_para_usuario(cls, user: User):
        """
        Gera token e UID para reset de senha.
        :param user: Usuário
        :return: UID e token
        """
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return uid, token

    @classmethod
    def gerar_token_para_reset(cls, user: User, email: str):
        """
        Busca usuário pelo username e retorna dados para reset de senha.
        :param user: Usuário
        :param email: Email do usuário
        :return: UID e token
        """
        logger.info(
            f"Iniciando geração de token para usuário: {user.username}"
        )

        uid, token = cls.gerar_token_para_usuario(user)

        name = user.first_name

        resultado = {
            "token": token,
            "uid": uid,
            "name": name,
        }

        logger.info(f"Token de reset gerado com sucesso para {user.username}")
        return resultado
