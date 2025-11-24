class AutenticacaoServiceError(Exception):
    """Erro genérico do serviço de autenticação externo (CORESSO)."""


class AutenticacaoRespostaInvalidaError(AutenticacaoServiceError):
    """Resposta inválida (não JSON ou parse falhou) do serviço de autenticação."""


class AutenticacaoRequisicaoError(AutenticacaoServiceError):
    """Falha ao realizar requisição ao serviço de autenticação (rede, timeout, etc)."""


class AutenticacaoCredenciaisInvalidasError(AutenticacaoServiceError):
    """Credenciais inválidas informadas ao serviço de autenticação."""


class AutenticacaoUpstreamError(AutenticacaoServiceError):
    """Erro retornado pelo serviço de autenticação (status não-sucesso)."""


class SmeIntegracaoException(Exception):
    """Erro genérico do serviço de integração com o SME Integracao."""