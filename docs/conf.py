"""Configuração do Sphinx para o Módulo Admin Usuários."""

project = "Módulo Admin Usuários"
author = "SME - SIGLA"
copyright = "2026, SME - SIGLA"

extensions = []

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "pt_BR"

html_theme = "alabaster"

html_theme_options = {
    "description": (
        "Documentação do módulo de administração de usuários da SIGLA."
    ),
    "github_button": False,
}
