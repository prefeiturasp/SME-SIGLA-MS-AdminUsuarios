from typing import Optional, Tuple
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions

from .services import AuthenticationService


class ExternalServiceAuthentication(BaseAuthentication):
    """Authenticate requests against the external auth service via Bearer token."""

    keyword = b"bearer"

    def authenticate(self, request) -> Optional[Tuple[User, str]]:
        auth = get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].lower() != self.keyword:
            return None
        if len(auth) == 1:
            raise exceptions.AuthenticationFailed("Invalid Authorization header. No credentials provided.")
        if len(auth) > 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header. Token string should not contain spaces.")

        token = auth[1].decode("utf-8")
        services = AuthenticationService()
        try:
            payload = services.validate_token(token)
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        user = self._get_or_create_local_user(payload)
        return (user, token)

    def _get_or_create_local_user(self, payload: dict) -> User:
        """Create or update a local Django User based on payload from external auth."""
        # Try to resolve fields flexibly
        user_info = payload.get("user", {}) if isinstance(payload.get("user"), dict) else {}
        username = user_info.get("username") or payload.get("username") or user_info.get("email") or payload.get("email")
        email = user_info.get("email") or payload.get("email") or ""
        first_name = user_info.get("first_name") or payload.get("first_name") or ""
        last_name = user_info.get("last_name") or payload.get("last_name") or ""
        if not username:
            # Fallback to an id-based username
            ext_id = str(user_info.get("id") or payload.get("id") or payload.get("user_id") or "external")
            username = f"ext_{ext_id}"

        user, created = User.objects.get_or_create(username=username, defaults={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        })
        if not created:
            # Light sync of profile fields
            dirty = False
            if email and user.email != email:
                user.email = email
                dirty = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                dirty = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                dirty = True
            if dirty:
                user.save(update_fields=["email", "first_name", "last_name"])
        return user 