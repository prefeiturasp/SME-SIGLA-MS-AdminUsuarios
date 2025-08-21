"""
External services for integration with other microservices.
"""
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.exceptions import ValidationError


class AuthenticationService:
    """Class for handling external service integrations."""
    
    def __init__(self):
        self.auth_service_url = settings.EXTERNAL_SERVICES['auth_service']['base_url']
        self.user_service_url = settings.EXTERNAL_SERVICES['user_service']['base_url']
        self.notification_service_url = settings.EXTERNAL_SERVICES['notification_service']['base_url']
        self.document_service_url = settings.EXTERNAL_SERVICES['document_service']['base_url']
        self.timeout = settings.EXTERNAL_SERVICES['auth_service']['timeout']
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user via external auth service."""
        try:
            payload = {"username": username, "password": password}
            response = requests.post(
                f"{self.auth_service_url}/api/auth/login/",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ValidationError(f"Auth service error: {str(exc)}")
    
    def change_password(self, user_id: str, old_password: str, new_password: str, token: Optional[str] = None) -> bool:
        """Change a user's password via external user service."""
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            payload = {"old_password": old_password, "new_password": new_password}
            response = requests.post(
                f"{self.user_service_url}/api/users/{user_id}/change-password/",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            raise ValidationError(f"User service error: {str(exc)}")
    
    def create_user(self, username: str, email: str, password: str, first_name: str = "", last_name: str = "") -> Dict[str, Any]:
        """Create a new user via external user service."""
        try:
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
            }
            response = requests.post(
                f"{self.user_service_url}/api/users/",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ValidationError(f"User service error: {str(exc)}")
