"""Módulo services/email."""

import logging
from collections.abc import Mapping, Sequence

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from usuarios.services.token_service import TokenService

logger = logging.getLogger(__name__)


class EmailService:
    """Serviço para operações de email."""

    @classmethod
    def enviar_email(
        cls,
        subject: str,
        template_name: str,
        context: Mapping[str, object],
        recipients: Sequence[str],
        *,
        from_email: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Envia email.

        Args:
            cls: Classe referenciada.
            subject: Subject utilizado na operação.
            template_name: Template name utilizado na operação.
            context: Contexto de serialização ou renderização.
            recipients: Recipients utilizado na operação.
            from_email: From email utilizado na operação.
            headers: Headers utilizado na operação.

        Returns:
            Nenhum valor.
        """
        html_content = render_to_string(template_name, context)
        sender = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None)
        text_body = strip_tags(html_content)
        logger.info("Enviando e-mail (HTML) para %s", ",".join(recipients))
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=sender,
            to=list(recipients),
            headers=headers,  # type: ignore[arg-type]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    @classmethod
    def enviar_email_esqueci_senha(
        cls, user: User, email: str, nome: str
    ) -> None:
        """Envia email esqueci senha.

        Args:
            cls: Classe referenciada.
            user: User utilizado na operação.
            email: Email utilizado na operação.
            nome: Nome utilizado na operação.

        Returns:
            Nenhum valor.
        """
        logger.info("Gerando token de reset para usuário: %s", user.username)
        token_data = TokenService.gerar_token_para_reset(user, email)

        link_reset = f"{settings.APLICACAO_URL}criar-nova-senha/{token_data['uid']}/{token_data['token']}"  # noqa: E501
        contexto_email = {
            "nome_usuario": nome,
            "link_reset": link_reset,
            "ms_url": settings.MS_URL,
        }
        cls.enviar_email(
            subject="Esqueci minha senha - SIGLA",
            template_name="reset_senha.html",
            context=contexto_email,
            recipients=[email],
        )
