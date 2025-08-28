"""
DRF views for the usuarios module.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from django.contrib.auth.models import User

from .serializers import (
    LoginSerializer,
    ChangePasswordSerializer,
    CreateUserSerializer,
)
from .services import ExternalServices


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services = ExternalServices()
        result = services.login(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        return Response(result, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = request.headers.get('Authorization', '').replace('Bearer ', '') or None
        services = ExternalServices()
        success = services.change_password(
            user_id=serializer.validated_data['user_id'],
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password'],
            token=token,
        )
        return Response({"success": success}, status=status.HTTP_200_OK)


class CreateUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services = ExternalServices()
        remote_user = services.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
        )
        # Optional local sync with Django's User model
        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=email,
                password=serializer.validated_data['password'],
                first_name=first_name,
                last_name=last_name,
            )
        return Response(remote_user, status=status.HTTP_201_CREATED)

