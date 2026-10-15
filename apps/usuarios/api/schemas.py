"""Documentação OpenAPI das operações de autenticação e de usuários."""

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import Direction, extend_schema

from core.openapi import (
    AUTENTICACAO_JWT,
    ERRO_REQUISICAO,
    RESPOSTA_ACESSO_NEGADO,
    exemplos_requisicao,
    resposta,
    respostas,
)
from core.serializers import ErroDetalheSerializer, ErrosValidacaoSerializer
from usuarios.serializers import (
    AlterarEmailSerializer,
    AlterarSenhaSerializer,
    BuscarUsuarioEolSerializer,
    ConfirmacaoSerializer,
    CreateUserSerializer,
    CriarNovaSenhaSerializer,
    EsqueciSenhaSerializer,
    LoginRespostaSerializer,
    LoginSerializer,
    MeusDadosSerializer,
    RecuperacaoSenhaRespostaSerializer,
    UsuarioCriadoSerializer,
    UsuarioEolSerializer,
)

TAG_AUTENTICACAO = "Autenticação"
TAG_MINHA_CONTA = "Minha conta"
TAG_USUARIOS = "Usuários"

RF_EXEMPLO = "1234567"
NOME_EXEMPLO = "MARIA APARECIDA DA SILVA"
EMAIL_EXEMPLO = "maria.silva@exemplo.test"
EMAIL_MASCARADO_EXEMPLO = "m*********a@exemplo.test"
SENHA_EXEMPLO = "Senha@2026"
NOVA_SENHA_EXEMPLO = "Nova@2026"
TOKEN_EXEMPLO = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidXNlcl9pZCI6IjEifQ.assinatura"
)
GRUPO_EXEMPLO = "Administrador"

CAMPO_OBRIGATORIO = ["Este campo é obrigatório."]

EXEMPLO_RECUSA_DA_SME = {
    "detail": "Mensagem devolvida pelo serviço de autenticação da SME."
}

EXEMPLO_SENHA_ALTERADA = {"detail": "Senha alterada com sucesso"}

AVISO_ERRO_DA_SME = (
    "Quando a SME recusa a alteração, a resposta é 400 e `detail` traz a "
    "mensagem dela, sem tratamento."
)


class LoginRespostaExtension(OpenApiSerializerExtension):
    """Aceita no login os campos repassados do serviço da SME."""

    target_class = LoginRespostaSerializer

    def map_serializer(
        self, auto_schema: AutoSchema, direction: Direction
    ) -> dict[str, Any]:
        """Retorna o schema dos campos descritos, aberto a outros campos."""
        esquema: dict[str, Any] = auto_schema._map_serializer(
            self.target, direction, bypass_extensions=True
        )
        esquema["additionalProperties"] = True
        return esquema


OPERACOES_LOGIN = {
    "post": extend_schema(
        operation_id="autenticar_usuario",
        summary="Fazer login",
        description=(
            "Confere o usuário e a senha no serviço de autenticação da SME "
            "e devolve o token JWT de acesso, junto com os dados que esse "
            "serviço retorna.\n\n"
            "Só entra quem já tem cadastro neste serviço: um RF sem "
            "cadastro responde 401 antes de a senha ser conferida. A cada "
            "login, o nome e o e-mail do cadastro local são atualizados "
            "com os dados da SME.\n\n"
            "O token vale por 7 dias e é aceito pelos demais "
            "microsserviços do SIGLA."
        ),
        request=LoginSerializer,
        examples=exemplos_requisicao(
            {"Login": {"usuario": RF_EXEMPLO, "senha": SENHA_EXEMPLO}}
        ),
        responses=respostas(
            {
                200: resposta(
                    LoginRespostaSerializer,
                    "Login aceito.",
                    {
                        "Login aceito": {
                            "nome": NOME_EXEMPLO,
                            "email": EMAIL_EXEMPLO,
                            "login": RF_EXEMPLO,
                            "codigoRf": RF_EXEMPLO,
                            "token": TOKEN_EXEMPLO,
                        }
                    },
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "Corpo inválido, ou falha no serviço de "
                        "autenticação da SME: fora do ar, com erro ou com "
                        "resposta ilegível."
                    ),
                    {
                        "Campos ausentes": {
                            "usuario": CAMPO_OBRIGATORIO,
                            "senha": CAMPO_OBRIGATORIO,
                        },
                        "Falha no serviço da SME": {
                            "detail": "Falha no serviço de autenticação"
                        },
                    },
                ),
                401: resposta(
                    ErroDetalheSerializer,
                    "Usuário sem cadastro neste serviço, ou senha incorreta.",
                    {
                        "Usuário sem cadastro": {
                            "detail": "Usuário não encontrado"
                        },
                        "Senha incorreta": {"detail": "Credenciais inválidas"},
                    },
                ),
            }
        ),
    ),
}

OPERACOES_ESQUECI_SENHA = {
    "post": extend_schema(
        operation_id="solicitar_recuperacao_de_senha",
        summary="Solicitar recuperação de senha",
        description=(
            "Envia ao usuário um e-mail com o link para criar uma nova "
            "senha. O usuário é localizado pelo RF ou pelo e-mail do "
            "cadastro, nunca pelos dois. O endereço de destino é o que "
            "consta para ele na SME, e volta mascarado na resposta.\n\n"
            "O link leva o `uid` e o `token` pedidos na criação da nova "
            "senha."
        ),
        request=EsqueciSenhaSerializer,
        examples=exemplos_requisicao(
            {
                "Pelo registro funcional": {"rf": RF_EXEMPLO},
                "Pelo e-mail": {"email": EMAIL_EXEMPLO},
            }
        ),
        responses=respostas(
            {
                200: resposta(
                    RecuperacaoSenhaRespostaSerializer,
                    "E-mail de recuperação enviado.",
                    {
                        "E-mail enviado": {
                            "usuario": RF_EXEMPLO,
                            "email": EMAIL_MASCARADO_EXEMPLO,
                            "email_enviado": True,
                        }
                    },
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "Corpo inválido, ou falha ao consultar os dados do "
                        "usuário na SME."
                    ),
                    {
                        "Nenhum identificador, ou os dois": {
                            "non_field_errors": [
                                "Informe rf ou email (apenas um)."
                            ]
                        },
                        "Falha ao consultar a SME": {
                            "detail": "Falha ao consultar dados do usuário"
                        },
                    },
                ),
                404: resposta(
                    ErroDetalheSerializer,
                    (
                        "Usuário sem cadastro neste serviço, ou sem e-mail "
                        "na SME."
                    ),
                    {
                        "Usuário sem cadastro": {
                            "detail": "Usuário não encontrado"
                        },
                        "Usuário sem e-mail na SME": {
                            "detail": "E-mail não encontrado para o usuário"
                        },
                    },
                ),
                502: resposta(
                    ErroDetalheSerializer,
                    "O e-mail não pôde ser enviado.",
                    {"Falha no envio": {"detail": "Falha ao enviar e-mail"}},
                ),
            }
        ),
    ),
}

OPERACOES_NOVA_SENHA = {
    "post": extend_schema(
        operation_id="redefinir_senha",
        summary="Criar nova senha",
        description=(
            "Troca a senha de quem pediu a recuperação, com o `uid` e o "
            "`token` do link recebido por e-mail. A senha é alterada no "
            "serviço de autenticação da SME e no cadastro local, e o "
            "token deixa de valer.\n\n"
            "Aqui a senha só precisa ter 6 caracteres; a troca de senha "
            "do usuário autenticado é mais exigente."
        ),
        request=CriarNovaSenhaSerializer,
        examples=exemplos_requisicao(
            {
                "Nova senha": {
                    "uid": "MQ",
                    "token": "dgb2sq-453303acf89407f9a3557a6a6c1e5506",
                    "nova_senha": NOVA_SENHA_EXEMPLO,
                }
            }
        ),
        responses=respostas(
            {
                200: resposta(
                    ConfirmacaoSerializer,
                    "Senha trocada.",
                    {"Senha trocada": EXEMPLO_SENHA_ALTERADA},
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "Corpo inválido, `uid` ou `token` recusado, ou "
                        "recusa da troca pela SME."
                    ),
                    {
                        "Senha curta": {
                            "nova_senha": [
                                "Certifique-se de que este campo tenha "
                                "mais de 6 caracteres."
                            ]
                        },
                        "UID inválido": {"detail": "UID inválido"},
                        "Token inválido ou já usado": {
                            "detail": "Token inválido"
                        },
                        "Recusa da SME": {
                            "detail": (
                                "Falha ao redefinir senha no SME Integração"
                            )
                        },
                    },
                ),
            }
        ),
    ),
}

OPERACOES_MEUS_DADOS = {
    "get": extend_schema(
        operation_id="consultar_meus_dados",
        summary="Consultar meus dados",
        description=(
            "Retorna o registro funcional, o nome, o e-mail e os grupos "
            "do usuário dono do token."
        ),
        auth=AUTENTICACAO_JWT,
        responses=respostas(
            {
                200: resposta(
                    MeusDadosSerializer,
                    "Dados do usuário autenticado.",
                    {
                        "Usuário com um grupo": {
                            "rf": RF_EXEMPLO,
                            "nome_completo": NOME_EXEMPLO,
                            "email": EMAIL_EXEMPLO,
                            "perfil_acesso": [GRUPO_EXEMPLO],
                        }
                    },
                ),
                403: RESPOSTA_ACESSO_NEGADO,
            }
        ),
    ),
}

OPERACOES_ALTERAR_SENHA = {
    "post": extend_schema(
        operation_id="alterar_senha",
        summary="Alterar minha senha",
        description=(
            "Troca a senha do usuário dono do token, no serviço de "
            "autenticação da SME e no cadastro local. A senha atual é "
            f"conferida com a usada no último login.\n\n{AVISO_ERRO_DA_SME}"
        ),
        auth=AUTENTICACAO_JWT,
        request=AlterarSenhaSerializer,
        examples=exemplos_requisicao(
            {
                "Troca de senha": {
                    "senha_atual": SENHA_EXEMPLO,
                    "nova_senha": NOVA_SENHA_EXEMPLO,
                    "confirmacao_nova_senha": NOVA_SENHA_EXEMPLO,
                }
            }
        ),
        responses=respostas(
            {
                200: resposta(
                    ConfirmacaoSerializer,
                    "Senha trocada.",
                    {"Senha trocada": EXEMPLO_SENHA_ALTERADA},
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "Corpo inválido, senha atual incorreta ou recusa "
                        "da troca pela SME."
                    ),
                    {
                        "Senha fora das regras": {
                            "nova_senha": [
                                "A senha deve ter entre 8 e 12 caracteres."
                            ]
                        },
                        "Confirmação diferente": {
                            "confirmacao_nova_senha": [
                                "As senhas não conferem."
                            ]
                        },
                        "Senha atual incorreta": {
                            "detail": "Senha atual incorreta."
                        },
                        "Recusa da SME": EXEMPLO_RECUSA_DA_SME,
                    },
                ),
                403: RESPOSTA_ACESSO_NEGADO,
            }
        ),
    ),
}

OPERACOES_ALTERAR_EMAIL = {
    "post": extend_schema(
        operation_id="alterar_email",
        summary="Alterar meu e-mail",
        description=(
            "Troca o e-mail do usuário dono do token, no CoreSSO e no "
            f"cadastro local.\n\n{AVISO_ERRO_DA_SME}"
        ),
        auth=AUTENTICACAO_JWT,
        request=AlterarEmailSerializer,
        examples=exemplos_requisicao(
            {"Novo e-mail": {"novo_email": EMAIL_EXEMPLO}}
        ),
        responses=respostas(
            {
                200: resposta(
                    ConfirmacaoSerializer,
                    "E-mail trocado.",
                    {
                        "E-mail trocado": {
                            "detail": "Email alterado com sucesso"
                        }
                    },
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "E-mail inválido ou em uso por outro usuário, ou "
                        "recusa da troca pela SME."
                    ),
                    {
                        "E-mail em uso": {
                            "novo_email": ["E-mail já está cadastrado."]
                        },
                        "E-mail malformado": {
                            "novo_email": [
                                "Insira um endereço de email válido."
                            ]
                        },
                        "Recusa da SME": EXEMPLO_RECUSA_DA_SME,
                    },
                ),
                403: RESPOSTA_ACESSO_NEGADO,
            }
        ),
    ),
}

OPERACOES_BUSCAR_USUARIO_EOL = {
    "post": extend_schema(
        operation_id="buscar_usuario_no_eol",
        summary="Buscar servidor no EOL",
        description=(
            "Consulta na SME o nome e o e-mail de um servidor pelo "
            "registro funcional, para preencher o cadastro de um novo "
            "usuário. A consulta usa POST e não altera nada.\n\n"
            "Responde 400 em todos os casos de erro: RF que já tem "
            "cadastro neste serviço, RF não encontrado no EOL ou falha na "
            "consulta."
        ),
        request=BuscarUsuarioEolSerializer,
        examples=exemplos_requisicao({"Consulta": {"rf": RF_EXEMPLO}}),
        responses=respostas(
            {
                200: resposta(
                    UsuarioEolSerializer,
                    "Servidor encontrado no EOL.",
                    {
                        "Servidor encontrado": {
                            "username": RF_EXEMPLO,
                            "nome": NOME_EXEMPLO,
                            "email": EMAIL_EXEMPLO,
                        }
                    },
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    (
                        "Corpo inválido, RF já cadastrado, RF não "
                        "encontrado no EOL ou falha na consulta."
                    ),
                    {
                        "RF ausente": {"rf": CAMPO_OBRIGATORIO},
                        "RF já cadastrado": {
                            "detail": "Usuário já cadastrado no SIGLA."
                        },
                        "RF não encontrado": {
                            "detail": "Usuário não encontrado no EOL."
                        },
                        "Falha na consulta": {
                            "detail": "Falha ao consultar o EOL."
                        },
                    },
                ),
            }
        ),
    ),
}

OPERACOES_CRIAR_USUARIO = {
    "post": extend_schema(
        operation_id="criar_usuario",
        summary="Criar usuário",
        description=(
            "Cadastra um usuário neste serviço. Ele nasce ativo, sem "
            "senha e sem grupo: a senha é a do serviço de autenticação da "
            "SME, conferida no login. O registro funcional não é "
            "conferido no EOL."
        ),
        request=CreateUserSerializer,
        examples=exemplos_requisicao(
            {
                "Novo usuário": {
                    "username": RF_EXEMPLO,
                    "nome": NOME_EXEMPLO,
                    "email": EMAIL_EXEMPLO,
                }
            }
        ),
        responses=respostas(
            {
                201: resposta(
                    UsuarioCriadoSerializer,
                    "Usuário criado.",
                    {
                        "Usuário criado": {
                            "detail": "Usuário criado com sucesso",
                            "user": RF_EXEMPLO,
                        }
                    },
                ),
                400: resposta(
                    ErrosValidacaoSerializer,
                    "Dados inválidos.",
                    {
                        "Campos ausentes": {
                            "username": CAMPO_OBRIGATORIO,
                            "nome": CAMPO_OBRIGATORIO,
                            "email": CAMPO_OBRIGATORIO,
                        },
                        "E-mail malformado": {
                            "email": ["Insira um endereço de email válido."]
                        },
                    },
                ),
                409: resposta(
                    ErroDetalheSerializer,
                    "Registro funcional ou e-mail já cadastrado.",
                    {
                        "RF já cadastrado": {
                            "detail": "Nome de usuário já está cadastrado."
                        },
                        "E-mail já cadastrado": {
                            "detail": "E-mail já está cadastrado."
                        },
                    },
                ),
            }
        ),
    ),
}
