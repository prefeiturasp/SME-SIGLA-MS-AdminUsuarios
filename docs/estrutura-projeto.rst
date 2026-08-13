Estrutura do projeto
====================

Esta seção explica **cada pasta do repositório** e o papel de cada módulo
dentro de ``apps/``.

Visão da árvore principal
-------------------------

.. code-block:: text

   ms-admin-usuarios/
   ├── apps/              # Módulos de negócio (Django apps)
   ├── config/            # Configurações do projeto Django
   ├── docs/              # Documentação Sphinx (este material)
   ├── requirements/      # Dependências Python por ambiente
   ├── manage.py          # Ponto de entrada do Django
   ├── Dockerfile         # Imagem Docker da API
   ├── docker-compose.yml # Ambiente local (PostgreSQL)
   └── Makefile           # Comandos úteis de desenvolvimento

Pasta ``apps/``
---------------

É onde ficam os **módulos de negócio**. Cada subpasta é um app Django com
responsabilidade bem definida.

``apps/usuarios/``
~~~~~~~~~~~~~~~~~~

**O que faz:** Cuida da **identidade do usuário** — login, cadastro, perfil,
recuperação e alteração de senha/e-mail.

**Para que serve:**

- Autenticar no SME Integração e emitir token JWT
- Criar usuário a partir da RF consultada no EOL
- Recuperar senha por e-mail e redefinir com token
- Alterar senha e e-mail (com sincronização externa)
- Expor o endpoint de “meus dados” do usuário autenticado

**Principais partes internas:**

.. list-table:: Módulos do app usuarios
   :header-rows: 1
   :widths: 35 65

   * - Subpasta / arquivo
     - Função
   * - ``api/``
     - Views e rotas REST (login, senha, cadastro, perfil)
   * - ``services/``
     - Integrações externas (autenticação, SME Integração, e-mail, token)
   * - ``repository.py``
     - Acesso ao banco (consultas e persistência de ``User``)
   * - ``serializers.py``
     - Validação e conversão dos dados da API
   * - ``exceptions.py``
     - Exceções de autenticação e integração
   * - ``management/commands/``
     - Comandos auxiliares (criar, importar e limpar usuários)
   * - ``tests/``
     - Testes automatizados do app

**Exemplo:** Quando o analista faz login, a view chama o serviço de
autenticação, o repositório localiza o usuário e a resposta devolve o token
junto com os dados básicos do perfil.

``apps/permissoes/``
~~~~~~~~~~~~~~~~~~~~

**O que faz:** Administra **grupos e permissões** do Django Auth, além do
vínculo entre usuários e grupos.

**Para que serve:**

- Listar e criar permissões vinculadas a um ContentType
- Listar, criar e atualizar grupos (incluindo permissões por codename)
- Adicionar ou remover usuários de um grupo
- Consultar permissões de um usuário (diretas e herdadas por grupo)
- Atualizar nome, e-mail, status e grupos de um usuário

**Principais partes internas:**

.. list-table:: Módulos do app permissoes
   :header-rows: 1
   :widths: 35 65

   * - Subpasta / arquivo
     - Função
   * - ``api/``
     - Views e rotas REST de permissões, grupos e usuários
   * - ``repository.py``
     - Acesso ao banco (``Permission``, ``Group``, ``ContentType``)
   * - ``serializers.py``
     - Validação e conversão dos dados da API
   * - ``management/commands/``
     - Carga inicial de permissões e grupos via JSON
   * - ``tests/``
     - Testes automatizados do app

**Exemplo:** Ao criar o grupo “Gestores” e vincular codenames de permissão, o
app ``permissoes`` persiste o grupo e associa as permissões encontradas no
banco.

Pasta ``config/``
-----------------

**O que faz:** Configurações centrais do projeto Django.

**Para que serve:**

.. list-table:: Arquivos de configuração
   :header-rows: 1
   :widths: 25 75

   * - Arquivo
     - Função
   * - ``settings.py``
     - Banco, apps instalados, CORS, JWT, SME Integração, ``MS_PATH``
   * - ``urls.py``
     - Rotas da API (``/api/v1/``), healthcheck e Swagger
   * - ``wsgi.py``
     - Ponto de entrada para servidores de produção

**Exemplo:** Em ambientes não locais, as rotas da aplicação ficam sob o
prefixo ``MS_PATH`` (por padrão ``/ms-admin-usuarios``), enquanto static/media
permanecem na raiz.

Pasta ``requirements/``
-----------------------

**O que faz:** Lista as **dependências Python** do projeto, separadas por
ambiente.

**Para que serve:**

.. list-table:: Arquivos de dependências
   :header-rows: 1
   :widths: 25 75

   * - Arquivo
     - Conteúdo
   * - ``base.txt``
     - Dependências essenciais (Django, DRF, JWT, PostgreSQL, SDK)
   * - ``local.txt``
     - Desenvolvimento (testes, lint, type-check, Sphinx)
   * - ``production.txt``
     - Produção (servidor de aplicação)

Pasta ``docs/``
---------------

**O que faz:** Contém esta documentação em formato reStructuredText (``.rst``)
e a configuração do Sphinx.

**Para que serve:** Gerar o site HTML de documentação com ``make docs`` ou
``sphinx-build``.

Arquivos na raiz
----------------

.. list-table:: Arquivos na raiz do projeto
   :header-rows: 1
   :widths: 25 75

   * - Arquivo
     - Função
   * - ``manage.py``
     - Comando Django (migrações, servidor, superusuário)
   * - ``docker-compose.yml``
     - Sobe o PostgreSQL no ambiente local
   * - ``Dockerfile``
     - Constrói a imagem Docker da API
   * - ``Makefile``
     - Atalhos: testes, lint, migrações e documentação
   * - ``README.md``
     - Visão técnica rápida e instruções de execução
   * - ``env.example``
     - Modelo de variáveis de ambiente necessárias

API — endpoints principais (referência)
---------------------------------------

Para consulta rápida, os principais caminhos da API (prefixo ``/api/v1/``):

**Usuários**

- ``POST /login/`` — Autenticar e obter token
- ``POST /esqueci-minha-senha/`` — Solicitar recuperação de senha
- ``POST /criar-nova-senha/`` — Redefinir senha com token
- ``POST /criar-usuario/`` — Cadastrar novo usuário
- ``POST /buscar-usuario-eol/`` — Consultar dados no EOL pela RF
- ``GET /meus-dados/`` — Perfil do usuário autenticado
- ``POST /alterar-senha/`` — Alterar senha do usuário autenticado
- ``POST /alterar-email/`` — Alterar e-mail do usuário autenticado

**Permissões e grupos**

- ``GET/POST /permissoes/`` — Listar ou criar permissões
- ``GET/POST/PUT /grupos/`` — Listar, criar ou atualizar permissões do grupo
- ``PUT /grupos/usuarios/`` — Adicionar ou remover usuários do grupo
- ``GET /usuarios/permissoes/`` — Permissões de um usuário
- ``GET/PATCH /usuarios/grupos/`` — Listar usuários com grupos ou atualizar
  usuário/grupos

A documentação interativa da API (Swagger) está disponível em ``/api/docs/``
quando o servidor está rodando.

Resumo das tecnologias utilizadas
---------------------------------

Sem entrar em detalhes de código, o módulo foi construído com:

- **Django e Django REST Framework** — base da API e da organização do projeto
- **SimpleJWT / PyJWT** — autenticação baseada em token
- **PostgreSQL** — armazenamento de usuários, grupos e permissões
- **Camada de serviços e repositórios** — regras e integrações separadas das
  consultas ao banco
- **Integrações HTTP** com SME Integração / EOL (login, senha, e-mail e dados
  do servidor)
- **sigla-sdk** — biblioteca compartilhada do ecossistema SIGLA
- **drf-spectacular (Swagger)** — documentação interativa dos endpoints
- **Testes automatizados (pytest)** — validação das views, serviços e
  repositórios
- **Ruff, mypy e pre-commit** — qualidade de código e tipagem
- **Docker e Makefile** — padronizar execução local e rotinas do time
- **Sphinx** — geração desta documentação em HTML
