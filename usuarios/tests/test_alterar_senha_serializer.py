import pytest
from rest_framework.exceptions import ValidationError

from usuarios.serializers.password import AlterarSenhaSerializer


def _valid_payload(**overrides):
    base = {
        "senha_atual": "qualquer",
        "nova_senha": "Abc1@xyz9",
        "confirmacao_nova_senha": "Abc1@xyz9",
    }
    base.update(overrides)
    return base


def test_senha_valida_aceita():
    s = AlterarSenhaSerializer(data=_valid_payload())
    assert s.is_valid(), s.errors


@pytest.mark.parametrize("nova_senha,fragment", [
    ("Ab1@", "entre 8 e 12"),
    ("Ab1@xxxxxxxxxxxxxx", "entre 8 e 12"),
    ("abc1@xyz9", "maiúscula"),
    ("ABC1@XYZ9", "minúscula"),
    ("Abcdefgh@", "número"),
    ("Abc12345678", "símbolo"),
    ("Abc1@ xyz", "espaços"),
    ("Abc1@xyzã", "acentuados"),
])
def test_validacao_nova_senha(nova_senha, fragment):
    s = AlterarSenhaSerializer(data=_valid_payload(nova_senha=nova_senha, confirmacao_nova_senha=nova_senha))
    assert not s.is_valid()
    errors = str(s.errors)
    assert fragment in errors


def test_confirmacao_diferente_retorna_erro():
    s = AlterarSenhaSerializer(data=_valid_payload(confirmacao_nova_senha="Outra@Sen1ha"))
    assert not s.is_valid()
    assert "confirmacao_nova_senha" in str(s.errors)
