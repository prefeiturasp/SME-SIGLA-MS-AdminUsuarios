# SME-SIGLA-MS - Admin Usuários

Sistema de administração de usuários desenvolvido com Django REST Framework, integrando-se a serviços externos para autenticação (login), criação de usuários e alteração de senha.

## 📁 Estrutura do Projeto

```
admin-usuarios-sigla-backend/
├── config/                          # Configurações do Django
│   ├── settings.py                  # Configurações principais (DRF, EXTERNAL_SERVICES, DB)
│   ├── urls.py                      # URLs principais (inclui usuarios.urls em /api/v1/)
│   └── wsgi.py                      # Configuração WSGI
├── usuarios/                        # App principal
│   ├── auth.py                      # Autenticação DRF via serviço externo (Bearer)
│   ├── serializers.py               # Serializers (login, criar usuário, alterar senha)
│   ├── services.py                  # Integração com serviços externos (AuthenticationService)
│   ├── urls.py                      # Rotas da API (/login, /criar-usuario, /alterar-senha)
│   ├── views.py                     # Views da API
│   └── management/commands/         # Comandos customizados
│       ├── criar_usuarios.py        # Cria usuários Django (senha fixa 123456)
│       └── limpar_usuarios.py       # Remove usuários não superusuários
├── requirements/                    # Dependências organizadas
│   ├── base.txt                     # Dependências principais
│   ├── local.txt                    # Desenvolvimento local
│   ├── production.txt               # Produção
│   └── README.md                    # Documentação dos requirements
├── docker-compose.yml               # Configuração Docker (PostgreSQL)
├── env.example                      # Variáveis de ambiente (exemplo)
└── README_DOCKER.md                 # Documentação Docker (opcional)
```

## 🚀 Início Rápido

### 1. Configurar ambiente

```bash
# Clonar o repositório
git clone <repository-url>
cd admin-usuarios-sigla-backend

# Copiar arquivo de ambiente (exemplo)
cp env.example .env

# Editar variáveis de ambiente
nano .env
```

### 2. Instalar dependências

```bash
# Para desenvolvimento local
pip install -r requirements/local.txt

# Para produção
pip install -r requirements/production.txt
```

### 3. Banco de dados

```bash
# Subir PostgreSQL com Docker
docker-compose up -d

# Verificar status
docker-compose ps
```

- Conexão PostgreSQL (docker-compose padrão):
  - Host: localhost
  - Porta: 5432
  - Database: escolhas
  - Usuário: postgres
  - Senha: postgres

Ajuste o `.env` para usar os mesmos valores do Docker (ex.: `DB_NAME=escolhas`).

### 4. Migrar banco

```bash
python manage.py makemigrations
python manage.py migrate

# Criar superusuário (opcional)
python manage.py createsuperuser
```

### 5. Executar servidor

```bash
python manage.py runserver
```

## 📊 API Endpoints

Base URL principal: `/api/v1/`

### Autenticação e Usuários

```
POST  /api/v1/login/            # Login via serviço externo
POST  /api/v1/criar-usuario/    # Criação de usuário via serviço externo (e sync local)
POST  /api/v1/alterar-senha/    # Alteração de senha via serviço externo
```

- Exemplos de payloads:
  - Login:
    ```json
    { "username": "usuario1", "password": "123456" }
    ```
  - Criar usuário:
    ```json
    {
      "username": "usuario1",
      "email": "usuario1@example.com",
      "password": "123456",
      "first_name": "Usuario",
      "last_name": "Um"
    }
    ```
  - Alterar senha:
    ```json
    {
      "user_id": "<id-ou-uuid>",
      "old_password": "123456",
      "new_password": "nova_senha"
    }
    ```
    Headers: `Authorization: Bearer <token>`

## 🔐 Autenticação

- A API utiliza uma autenticação customizada (`usuarios.auth.ExternalServiceAuthentication`) que valida o token Bearer em um serviço externo e sincroniza um `User` local do Django (apenas campos básicos: email, first_name, last_name).
- Rotas de login/criar-usuario/alterar-senha estão liberadas (`AllowAny`). Demais rotas seguem `IsAuthenticated` por padrão.

## 🔧 Configuração

### Variáveis de Ambiente

Copie `env.example` para `.env` e configure:

```env
# Django
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco de Dados - PostgreSQL
db_ENGINE=django.db.backends.postgresql
DB_NAME=escolhas
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Serviços Externos
AUTH_SERVICE_BASE_URL=http://localhost:8100
AUTH_SERVICE_TIMEOUT=10
USER_SERVICE_BASE_URL=http://localhost:8101
USER_SERVICE_TIMEOUT=10
```

Observação: os serviços externos são lidos em `config/settings.py` via `EXTERNAL_SERVICES['auth_service'|'user_service']`.

## 🛠️ Comandos Customizados

- Criar usuários de exemplo (senha padrão 123456):

```bash
python manage.py criar_usuarios --count 5
```

- Limpar usuários não superusuários:

```bash
python manage.py limpar_usuarios
```

## 🧪 Testes

```bash
python manage.py test
```

## 📦 Dependências

As principais dependências estão em `requirements/base.txt` e são incluídas pelos perfis `local.txt` e `production.txt` (DRF, django-cors-headers, django-filter, requests, psycopg2-binary, etc.).

## 🤝 Contribuição

1. Faça fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/minha-feature`)
3. Commit suas mudanças (`git commit -m 'Minha feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes. 