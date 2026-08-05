from app.conftest import run_async
from datetime import timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.auth.jwt import create_token, decode_token, get_current_user
from app.schemas.token import TokenType
from app.core.config import get_settings
from app.models.user import User

settings = get_settings()

# ======================================================================================
# create_token
# ======================================================================================

def test_create_token_with_explicit_expires_delta():
    """Test create_token honors an explicit expires_delta instead of the type-based default."""
    token = create_token(str(uuid4()), TokenType.ACCESS, expires_delta=timedelta(minutes=5))
    payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["type"] == TokenType.ACCESS.value

def test_create_token_accepts_uuid_user_id():
    """Test create_token converts a UUID user_id to a string 'sub' claim before encoding."""
    user_id = uuid4()
    token = create_token(user_id, TokenType.ACCESS)
    payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)

def test_create_token_encode_failure_raises_http_exception():
    """Test create_token wraps unexpected jose.jwt.encode failures in a 500 HTTPException."""
    with patch("app.auth.jwt.jwt.encode", side_effect=Exception("boom")):
        with pytest.raises(HTTPException) as exc_info:
            create_token(str(uuid4()), TokenType.ACCESS)
    assert exc_info.value.status_code == 500
    assert "Could not create token" in exc_info.value.detail

# ======================================================================================
# decode_token
# ======================================================================================

def test_decode_token_valid():
    """Test decode_token returns the payload for a valid, non-blacklisted token."""
    token = create_token(str(uuid4()), TokenType.ACCESS)
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        payload = run_async(decode_token(token, TokenType.ACCESS))
    assert payload["type"] == TokenType.ACCESS.value

def test_decode_token_wrong_type():
    """Test decode_token rejects a token whose 'type' claim doesn't match the expected type.

    Crafted directly with jose so the signature still matches the secret being
    decoded against; going through create_token would instead hit the (also
    real) signature-mismatch path, since access/refresh tokens use different secrets.
    """
    token = jose_jwt.encode(
        {"sub": str(uuid4()), "type": TokenType.REFRESH.value, "jti": "fake-jti"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        run_async(decode_token(token, TokenType.ACCESS))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token type"

def test_decode_token_blacklisted():
    """Test decode_token rejects a token whose jti has been blacklisted."""
    token = create_token(str(uuid4()), TokenType.ACCESS)
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=True)):
        with pytest.raises(HTTPException) as exc_info:
            run_async(decode_token(token, TokenType.ACCESS))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has been revoked"

def test_decode_token_expired():
    """Test decode_token rejects an expired token."""
    token = create_token(str(uuid4()), TokenType.ACCESS, expires_delta=timedelta(seconds=-1))
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            run_async(decode_token(token, TokenType.ACCESS))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

def test_decode_token_invalid():
    """Test decode_token rejects a malformed/unsigned token."""
    with pytest.raises(HTTPException) as exc_info:
        run_async(decode_token("not.a.validtoken", TokenType.ACCESS))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

# ======================================================================================
# get_current_user (DB-backed version in app.auth.jwt)
# ======================================================================================

def _mock_db_returning(user):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    return db

def test_get_current_user_success():
    """Test get_current_user returns the User instance for a valid token and active user."""
    active_user = MagicMock(spec=User)
    active_user.is_active = True
    db = _mock_db_returning(active_user)

    with patch("app.auth.jwt.decode_token", new=AsyncMock(return_value={"sub": str(uuid4())})):
        result = run_async(get_current_user(token="validtoken", db=db))
    assert result is active_user

def test_get_current_user_not_found():
    """Test get_current_user raises 401 (wrapping the internal 404) when no user matches."""
    db = _mock_db_returning(None)

    with patch("app.auth.jwt.decode_token", new=AsyncMock(return_value={"sub": str(uuid4())})):
        with pytest.raises(HTTPException) as exc_info:
            run_async(get_current_user(token="validtoken", db=db))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "404: User not found"

def test_get_current_user_inactive():
    """Test get_current_user raises 401 (wrapping the internal 400) for an inactive user."""
    inactive_user = MagicMock(spec=User)
    inactive_user.is_active = False
    db = _mock_db_returning(inactive_user)

    with patch("app.auth.jwt.decode_token", new=AsyncMock(return_value={"sub": str(uuid4())})):
        with pytest.raises(HTTPException) as exc_info:
            run_async(get_current_user(token="validtoken", db=db))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "400: Inactive user"
