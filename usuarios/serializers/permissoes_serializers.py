from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "app_label", "model"]


class GroupSerializer(serializers.ModelSerializer):
    permissoes = PermissionSerializer(source="permissions", many=True, read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "permissoes"]


class CreatePermissionSerializer(serializers.Serializer):
    app_label = serializers.CharField()
    model = serializers.CharField()
    codename = serializers.CharField()
    name = serializers.CharField()

    def validate(self, attrs):
        app_label, model = attrs["app_label"], attrs["model"]
        ct = ContentType.objects.filter(app_label=app_label, model__iexact=model).first()
        if not ct:
            raise serializers.ValidationError("ContentType não encontrado para app_label/model informados.")
        if Permission.objects.filter(content_type=ct, codename=attrs["codename"]).exists():
            raise serializers.ValidationError("Permissão já existe para este content type e codename.")
        attrs["content_type"] = ct
        return attrs

    def create(self, validated_data):
        validated_data.pop("content_type", None)
        ct = ContentType.objects.get(app_label=self.validated_data["app_label"], model__iexact=self.validated_data["model"])
        perm = Permission.objects.create(
            name=validated_data["name"],
            codename=validated_data["codename"],
            content_type=ct
        )
        return perm


class CreateGroupSerializer(serializers.Serializer):
    grupo = serializers.CharField()
    permissoes_codenames = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def validate_grupo(self, value):
        if Group.objects.filter(name=value).exists():
            raise serializers.ValidationError("Grupo já existe.")
        return value

    def create(self, validated_data):
        grupo = Group.objects.create(name=validated_data["grupo"])
        codenames = validated_data.get("permissoes_codenames", [])
        if codenames:
            perms = Permission.objects.filter(codename__in=codenames)
            grupo.permissions.add(*perms)
        return grupo


class UpdateGroupPermissionsSerializer(serializers.Serializer):
    grupo = serializers.CharField()
    adicionar_codenames = serializers.ListField(child=serializers.CharField(), required=False)
    remover_codenames = serializers.ListField(child=serializers.CharField(), required=False)


class UpdateGroupUsersSerializer(serializers.Serializer):
    grupo = serializers.CharField()
    adicionar_usuarios = serializers.ListField(child=serializers.CharField(), required=False)
    remover_usuarios = serializers.ListField(child=serializers.CharField(), required=False)
