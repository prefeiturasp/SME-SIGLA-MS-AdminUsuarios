import logging
import requests
from rest_framework import status
from django.conf import settings
from usuarios.exceptions import SmeIntegracaoException

logger = logging.getLogger(__name__)


class SmeIntegracaoService:
    DEFAULT_HEADERS = {
        'accept': 'application/json',
        "x-api-eol-key": settings.SME_INTEGRACAO_TOKEN,
    }
    DEFAULT_TIMEOUT = 10

    @classmethod
    def informacao_usuario(cls, username):
        logger.info(f"Consultando dados na API externa para: {username}")
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/{username}/dados"
            response = requests.get(url, headers=cls.DEFAULT_HEADERS, timeout=10)

            if response.status_code == status.HTTP_200_OK:
                return response.json()

            else:
                logger.info(f"Dados não encontrados: {response}")
                raise SmeIntegracaoException('Dados não encontrados.')

        except requests.RequestException:
            logger.exception("Erro de conexão com a API externa")
            raise requests.RequestException("Erro ao conectar-se à API externa.")


    @classmethod
    def redefine_senha(cls, registro_funcional, senha):
        if not registro_funcional or not senha:
            raise SmeIntegracaoException("Registro funcional e senha são obrigatórios")

        logger.info(
            "Iniciando redefinição de senha no CoreSSO para usuário: %s",
            registro_funcional
        )
        data = {
            'Usuario': registro_funcional,
            'Senha': senha
        }
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/AlterarSenha"
            response = requests.post(url, data=data, headers=cls.DEFAULT_HEADERS)
            if response.status_code == status.HTTP_200_OK:
                result = "OK"
                return result
            else:
                texto = response.content.decode('utf-8')
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao redefinir senha: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err))


    @classmethod
    def alterar_email(cls, registro_funcional, email):
        if not registro_funcional or not email:
            raise SmeIntegracaoException("Registro funcional e email são obrigatórios")

        logger.info(
            "Iniciando alteração de email no CoreSSO para usuário: %s",
            registro_funcional
        )
        data = {
            'Usuario': registro_funcional,
            'Email': email
        }
        try:
            url = f"{settings.SME_INTEGRACAO_URL}/api/AutenticacaoSgp/AlterarEmail"
            response = requests.post(url, data=data, headers=cls.DEFAULT_HEADERS)
            if response.status_code == status.HTTP_200_OK:
                return "OK"
            else:
                texto = response.content.decode('utf-8')
                mensagem = texto.strip("{}'\"")
                logger.info("Erro ao alterar email: %s", mensagem)
                raise SmeIntegracaoException(mensagem)
        except Exception as err:
            raise SmeIntegracaoException(str(err))
