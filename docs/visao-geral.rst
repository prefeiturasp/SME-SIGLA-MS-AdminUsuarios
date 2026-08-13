Visão geral
===========

O que é este módulo?
--------------------

O **Módulo Admin Usuários** é o microserviço responsável por **autenticação,
cadastro e gestão de acesso** dos usuários internos da SIGLA (Secretaria
Municipal de Educação de São Paulo).

Em termos simples: ele concentra o login, a recuperação e alteração de senha,
o cadastro de novos usuários a partir do EOL e a administração de **grupos e
permissões** que controlam o que cada pessoa pode ver e fazer no sistema.

Para que serve?
---------------

O sistema permite que a equipe da SME:

- **Autenticar** usuários com integração ao serviço de autenticação SME/EOL
- **Cadastrar** novos usuários a partir da RF (consulta no EOL)
- **Recuperar e alterar** senha e e-mail (com sincronização no SME Integração)
- Consultar o **perfil** do usuário autenticado (dados e grupos)
- Gerenciar **permissões** e **grupos** de acesso
- Associar usuários a grupos e consultar permissões diretas ou herdadas

Onde ele se encaixa no ecossistema SIGLA?
-----------------------------------------

Este módulo é a **porta de entrada de identidade e autorização** da plataforma.
Outros microserviços e o frontend consomem suas APIs para saber *quem* está
logado e *o que* essa pessoa pode fazer.

.. list-table:: Integrações do ecossistema
   :header-rows: 1
   :widths: 30 70

   * - Sistema
     - Papel em relação ao Admin Usuários
   * - **SME Integração / EOL**
     - Autenticação, consulta de dados do servidor, redefinição de senha e
       alteração de e-mail
   * - **Frontend SIGLA**
     - Interface de login, perfil, cadastro e gestão de acessos
   * - **Demais microserviços SIGLA**
     - Consomem tokens e regras de acesso alinhadas ao usuário autenticado

Exemplo prático do dia a dia
----------------------------

Imagine o seguinte cenário:

1. Um servidor da SME acessa a SIGLA e informa RF e senha.
2. O módulo valida as credenciais no **SME Integração**, atualiza dados locais
   e devolve um **token JWT** para as próximas requisições.
3. Se a pessoa esqueceu a senha, solicita recuperação: o sistema busca o e-mail
   no EOL e envia o link de redefinição.
4. Um administrador cadastra um novo usuário consultando a RF no EOL e define
   os **grupos** de acesso (por exemplo, Gestor ou Operador).
5. Nas telas administrativas, o sistema lista permissões disponíveis, grupos e
   usuários com seus respectivos acessos.

Fluxo resumido
--------------

.. code-block:: text

   Login (RF + senha) ---> SME Integração ---> Token JWT + perfil
            |
            +-- Esqueci senha / Criar nova senha
            +-- Alterar senha / Alterar e-mail
            +-- Criar usuário (consulta EOL)
            |
            v
   Gestão de acesso
            |
            +-- Permissões disponíveis
            +-- Grupos (criar / vincular permissões)
            +-- Usuários x grupos
            +-- Permissões do usuário (diretas + herdadas)

Tecnologias utilizadas (referência rápida)
------------------------------------------

Para quem precisa de contexto técnico sem entrar no código:

- **Django** — framework web que estrutura o projeto
- **Django REST Framework** — expõe a API consumida pelo frontend
- **SimpleJWT** — emissão e validação de tokens de autenticação
- **PostgreSQL** — banco de dados dos usuários, grupos e permissões
- **Docker** — facilita subir o serviço em ambientes padronizados
- **Swagger (documentação da API)** — consulta interativa em ``/api/docs/``
