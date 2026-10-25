from uuid import uuid4

import jwt
import pytest

from app.auth.tokens import ALGORITHM, create_access_token, decode_access_token
from app.core.config import settings
from app.core.security import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password = "StrongTestPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not-a-valid-token")


def test_non_access_token_type_is_rejected() -> None:
    token = jwt.encode(
        {"sub": str(uuid4()), "type": "refresh"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
