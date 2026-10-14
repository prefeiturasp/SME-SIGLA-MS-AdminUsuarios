"""Documentação OpenAPI das operações de grupos, permissões e usuários."""

from __future__ import annotations

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from core.openapi import (
    ERRO_REQUISICAO,
    exemplos_requisicao,
    resposta,
    respostas,
)
from core.serializers import ErroDetalheSerializer, ErrosValidacaoSerializer
from permissoes.serializers import (
    AtualizarUsuarioRequisicaoSerializer,
    CreateGroupSerializer,
    CreatePermissionSerializer,
    GroupSerializer,
    PermissionSerializer,
    UpdateGroupPermissionsSerializer,
    UpdateGroupUsersSerializer,
    UsuarioComGruposSerializer,
    UsuarioPermissoesSerializer,
    UsuariosComGruposSerializer,
)
from usuarios.api.schemas import (
    AVISO_ERRO_DA_SME,
    CAMPO_OBRIGATORIO,
    EMAIL_EXEMPLO,
    EXEMPLO_RECUSA_DA_SME,
    GRUPO_EXEMPLO,
    RF_EXEMPLO,
)

TAG_GRUPOS = "Grupos"
TAG_PERMISSOES = "Permissões"

RF_2_EXEMPLO = "7654321"
NOME_USUARIO_EXEMPLO = "Maria Aparecida da Silva"
GRUPO_2_EXEMPLO = "Consulta"

AVISO_NOME_EXATO = (
    "O grupo é localizado pelo nome exato, com maiúsculas e minúsculas."
)

EXEMPLO_PERMISSAO = {
    "id": 16,
    "codename": "view_user",
    "name": "Can view user",
    "app_label": "auth",
    "model": "user",
}

EXEMPLO_PERMISSAO_NOVA = {
    "id": 25,
    "codename": "exportar_usuarios",
    "name": "Pode exportar usuários",
    "app_label": "auth",
    "model": "user",
}

EXEMPLO_GRUPO = {
    "id": 1,
    "name": GRUPO_EXEMPLO,
    "permissoes": [EXEMPLO_PERMISSAO, EXEMPLO_PERMISSAO_NOVA],
}

EXEMPLO_GRUPO_SEM_PERMISSOES = {
    "id": 2,
    "name": GRUPO_2_EXEMPLO,
    "permissoes": [],
}

EXEMPLO_USUARIO_COM_GRUPOS = {
    "usuario": RF_EXEMPLO,
    "nome": NOME_USUARIO_EXEMPLO,
    "email": EMAIL_EXEMPLO,
    "is_active": True,
    "grupos": [GRUPO_EXEMPLO],
}

EXEMPLO_USUARIO_SEM_DADOS: dict[str, Any] = {
    "usuario": RF_2_EXEMPLO,
    "nome": None,
    "email": None,
    "is_active": True,
    "grupos": [],
}

ERRO_GRUPO_AUSENTE = {"grupo": CAMPO_OBRIGATORIO}

RESPOSTA_GRUPO = resposta(
    GroupSerializer,
    "Grupo com as permissões atuais.",
    {"Grupo": EXEMPLO_GRUPO},
)

RESPOSTA_GRUPO_NAO_ENCONTRADO = resposta(
    ErroDetalheSerializer,
    "Não há grupo com o nome informado.",
    {"Grupo inexistente": {"detail": "Grupo não encontrado"}},
)

RESPOSTA_USUARIO_NAO_ENCONTRADO = resposta(
    ErroDetalheSerializer,
    "Não há usuário com o registro funcional informado.",
    {"Usuário inexistente": {"detail": "Usuário não encontrado"}},
)

RESPOSTA_GRUPO_INVALIDO = resposta(
    ErrosValidacaoSerializer,
    "Dados inválidos.",
    {"Grupo ausente": ERRO_GRUPO_AUSENTE},
)

OPERACOES_PERMISSOES = {
    "get": extend_schema(
        operation_id="listar_permissoes",
        summary="Listar permissões",
        description=(
            "Retorna todas as permissões do sistema, ordenadas por app e, "
            "em cada app, pela ordem de criação. A lista não é paginada."
        ),
        responses=respostas(
            {
                200: resposta(
                    PermissionSerializer(many=True),
                    "Permissões cadastradas.",
                    {"Permissão": EXEMPLO_PERMISSAO},
                )
            }
        ),
    ),
    "post": extend_schema(
        operation_id="criar_permissao",
        summary="Criar permissão",
        description=(
            "Cria uma permissão para um model que já existe no sistema. "
            "Responde 400 se o model não é encontrado ou se ele já tem "
            "uma permissão com o mesmo código."
        ),
        request=CreatePermissionSerializer,
        examples=exemplos_requisicao(
            {
                "Nova permissão": {
                    "app_label": "auth",
                    "model": "user",
                    "codename": "exportar_usuarios",
                    "name": "Pode exportar usuários",
                }
            }
        ),
        responses=respostas(
            {
                201: resposta(
                    PermissionSerializer,
                    "Permissão criada.",
                    {"Permissão criada": EXEMPLO_PERMISSAO_NOVA},
                ),
                400: resposta(
                    ErrosValidacaoSerializer,
                    "Dados inválidos.",
                    {
                        "Model inexistente": {
                            "non_field_errors": [
                                "ContentType não encontrado para "
                                "app_label/model informados."
                            ]
                        },
                        "Código repetido no model": {
                            "non_field_errors": [
                                "Permissão já existe para este content "
                                "type e codename."
                            ]
                        },
                    },
                ),
            }
        ),
    ),
}

OPERACOES_GRUPOS = {
    "get": extend_schema(
        operation_id="listar_grupos",
        summary="Listar grupos",
        description=(
            "Retorna os grupos em ordem alfabética, cada um com as "
            "permissões dele. A lista não é paginada. Com `grupo`, "
            "retorna só o grupo com aquele nome, ou 404 se ele não existe."
        ),
        parameters=[
            OpenApiParameter(
                name="grupo",
                type=OpenApiTypes.STR,
                description=(
                    "Nome exato do grupo, com maiúsculas e minúsculas. Sem "
                    "o parâmetro, vêm todos os grupos."
                ),
            )
        ],
        responses=respostas(
            {
                200: resposta(
                    GroupSerializer(many=True),
                    "Grupos encontrados.",
                    {"Grupo": EXEMPLO_GRUPO},
                ),
                404: RESPOSTA_GRUPO_NAO_ENCONTRADO,
            }
        ),
    ),
    "post": extend_schema(
        operation_id="criar_grupo",
        summary="Criar grupo",
        description=(
            "Cria um grupo e, se informados, vincula a ele as permissões "
            "dos códigos enviados. Códigos que não existem são ignorados, "
            "sem erro."
        ),
        request=CreateGroupSerializer,
        examples=exemplos_requisicao(
            {
                "Grupo com duas permissões": {
                    "grupo": GRUPO_EXEMPLO,
                    "permissoes_codenames": [
                        "view_user",
                        "exportar_usuarios",
                    ],
                },
                "Grupo sem permissões": {"grupo": GRUPO_2_EXEMPLO},
            }
        ),
        responses=respostas(
            {
                201: resposta(
                    GroupSerializer,
                    "Grupo criado.",
                    {
                        "Grupo com duas permissões": EXEMPLO_GRUPO,
                        "Grupo sem permissões": EXEMPLO_GRUPO_SEM_PERMISSOES,
                    },
                ),
                400: resposta(
                    ErrosValidacaoSerializer,
                    "Dados inválidos.",
                    {
                        "Nome já usado": {"grupo": ["Grupo já existe."]},
                        "Grupo ausente": ERRO_GRUPO_AUSENTE,
                    },
                ),
            }
        ),
    ),
    "put": extend_schema(
        operation_id="atualizar_permissoes_do_grupo",
        summary="Incluir e retirar permissões de um grupo",
        description=(
            "Inclui no grupo as permissões de `adicionar_codenames` e, "
            "depois, retira as de `remover_codenames`. As demais "
            f"permissões do grupo não mudam. {AVISO_NOME_EXATO}\n\n"
            "As permissões são localizadas só pelo código, que pode se "
            "repetir entre models: todas as que têm o código informado "
            "entram ou saem. Códigos que não existem são ignorados, sem "
            "erro."
        ),
        request=UpdateGroupPermissionsSerializer,
        examples=exemplos_requisicao(
            {
                "Incluir uma permissão e retirar outra": {
                    "grupo": GRUPO_EXEMPLO,
                    "adicionar_codenames": ["exportar_usuarios"],
                    "remover_codenames": ["delete_user"],
                }
            }
        ),
        responses=respostas(
            {
                200: RESPOSTA_GRUPO,
                400: RESPOSTA_GRUPO_INVALIDO,
                404: RESPOSTA_GRUPO_NAO_ENCONTRADO,
            }
        ),
    ),
}

OPERACOES_USUARIOS_DO_GRUPO = {
    "put": extend_schema(
        operation_id="atualizar_usuarios_do_grupo",
        summary="Incluir e retirar usuários de um grupo",
        description=(
            "Inclui no grupo os usuários de `adicionar_usuarios` e, "
            "depois, retira os de `remover_usuarios`. Os demais usuários "
            f"do grupo não mudam. {AVISO_NOME_EXATO}\n\n"
            "Registros funcionais que não existem são ignorados, sem "
            "erro. A resposta traz o grupo e as permissões dele, e não a "
            "lista de usuários."
        ),
        request=UpdateGroupUsersSerializer,
        examples=exemplos_requisicao(
            {
                "Incluir um usuário e retirar outro": {
                    "grupo": GRUPO_EXEMPLO,
                    "adicionar_usuarios": [RF_EXEMPLO],
                    "remover_usuarios": [RF_2_EXEMPLO],
                }
            }
        ),
        responses=respostas(
            {
                200: RESPOSTA_GRUPO,
                400: RESPOSTA_GRUPO_INVALIDO,
                404: RESPOSTA_GRUPO_NAO_ENCONTRADO,
            }
        ),
    ),
}

OPERACOES_PERMISSOES_DO_USUARIO = {
    "get": extend_schema(
        operation_id="consultar_permissoes_do_usuario",
        summary="Consultar permissões de um usuário",
        description=(
            "Retorna os grupos de um usuário e todas as permissões que "
            "ele tem, atribuídas direto a ele ou recebidas dos grupos, "
            "sem repetição."
        ),
        parameters=[
            OpenApiParameter(
                name="usuario",
                type=OpenApiTypes.STR,
                required=True,
                description="Registro funcional do usuário.",
            ),
            OpenApiParameter(
                name="model",
                type=OpenApiTypes.STR,
                description=(
                    "Nomes de models separados por vírgula, por exemplo "
                    "`user,group`. Restringe `permissoes` às desses "
                    "models, sem diferenciar maiúsculas de minúsculas."
                ),
            ),
        ],
        responses=respostas(
            {
                200: resposta(
                    UsuarioPermissoesSerializer,
                    "Grupos e permissões do usuário.",
                    {
                        "Usuário com um grupo": {
                            "usuario": RF_EXEMPLO,
                            "nome": NOME_USUARIO_EXEMPLO,
                            "email": EMAIL_EXEMPLO,
                            "grupos": [GRUPO_EXEMPLO],
                            "total_permissoes": 2,
                            "permissoes": [
                                EXEMPLO_PERMISSAO_NOVA,
                                EXEMPLO_PERMISSAO,
                            ],
                        },
                        "Usuário sem nome, e-mail e grupos": {
                            "usuario": RF_2_EXEMPLO,
                            "nome": None,
                            "email": None,
                            "grupos": [],
                            "total_permissoes": 0,
                            "permissoes": [],
                        },
                    },
                ),
                400: resposta(
                    ErroDetalheSerializer,
                    "Parâmetro `usuario` ausente.",
                    {
                        "Usuário não informado": {
                            "detail": "usuario é obrigatório"
                        }
                    },
                ),
                404: RESPOSTA_USUARIO_NAO_ENCONTRADO,
            }
        ),
    ),
}

OPERACOES_USUARIOS_COM_GRUPOS = {
    "get": extend_schema(
        operation_id="listar_usuarios_com_grupos",
        summary="Listar usuários com os grupos",
        description=(
            "Retorna todos os usuários, em ordem de registro funcional, "
            "cada um com a situação e os grupos. A lista não é paginada: "
            "`count` é só a quantidade de itens em `results`."
        ),
        parameters=[
            OpenApiParameter(
                name="usuario",
                type=OpenApiTypes.STR,
                description=(
                    "Trecho do registro funcional, sem diferenciar "
                    "maiúsculas de minúsculas."
                ),
            )
        ],
        responses=respostas(
            {
                200: resposta(
                    UsuariosComGruposSerializer,
                    "Usuários encontrados. `results` vazio se nenhum casa.",
                    {
                        "Dois usuários": {
                            "count": 2,
                            "results": [
                                EXEMPLO_USUARIO_COM_GRUPOS,
                                EXEMPLO_USUARIO_SEM_DADOS,
                            ],
                        }
                    },
                )
            }
        ),
    ),
    "patch": extend_schema(
        operation_id="atualizar_usuario",
        summary="Alterar usuário",
        description=(
            "Altera o nome, o e-mail, a situação e os grupos de um "
            "usuário, identificado por `usuario`. Só os campos enviados "
            "mudam.\n\n"
            "`grupos` define a lista final de grupos do usuário. "
            "`adicionar_grupos` e `remover_grupos` têm os nomes "
            "conferidos, mas não produzem efeito.\n\n"
            "Um e-mail diferente do atual é alterado também no CoreSSO. "
            f"{AVISO_ERRO_DA_SME}"
        ),
        request=AtualizarUsuarioRequisicaoSerializer,
        examples=exemplos_requisicao(
            {
                "Trocar os grupos": {
                    "usuario": RF_EXEMPLO,
                    "grupos": [GRUPO_EXEMPLO],
                },
                "Desativar o usuário": {
                    "usuario": RF_EXEMPLO,
                    "is_active": False,
                },
            }
        ),
        responses=respostas(
            {
                200: resposta(
                    UsuarioComGruposSerializer,
                    "Usuário com os dados atuais.",
                    {"Usuário alterado": EXEMPLO_USUARIO_COM_GRUPOS},
                ),
                400: resposta(
                    ERRO_REQUISICAO,
                    "Dados inválidos, ou recusa da troca de e-mail pela SME.",
                    {
                        "Usuário ausente": {"usuario": CAMPO_OBRIGATORIO},
                        "Grupo inexistente": {
                            "grupos": ["Grupos inexistentes: Auditoria"]
                        },
                        "E-mail em uso": {
                            "email": [
                                "Email já está em uso por outro usuário."
                            ]
                        },
                        "Recusa da SME": EXEMPLO_RECUSA_DA_SME,
                    },
                ),
                404: RESPOSTA_USUARIO_NAO_ENCONTRADO,
            }
        ),
    ),
}
