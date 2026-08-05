import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status
from app.auth.dependencies import get_current_user, get_current_active_user
from app.conftest import create_fake_user
from app.schemas.user import UserResponse
from app.models.user import User
from uuid import uuid4

# Fixture for mocking token verification
@pytest.fixture
def mock_verify_token():
    with patch.object(User, 'verify_token') as mock:
        yield mock

# Test get_current_user with a valid token for a real, existing user
def test_get_current_user_valid_token_existing_user(mock_verify_token, db_session, test_user):
    """Test get_current_user looks the user up in the database and returns
    their real, current data (not data assumed from the token)."""
    mock_verify_token.return_value = test_user.id

    user_response = get_current_user(token="validtoken", db=db_session)

    assert isinstance(user_response, UserResponse)
    assert user_response.id == test_user.id
    assert user_response.username == test_user.username
    assert user_response.email == test_user.email
    assert user_response.first_name == test_user.first_name
    assert user_response.last_name == test_user.last_name
    assert user_response.is_active == test_user.is_active

    mock_verify_token.assert_called_once_with("validtoken")

# Test get_current_user with invalid token (returns None)
def test_get_current_user_invalid_token(mock_verify_token, db_session):
    mock_verify_token.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="invalidtoken", db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

    mock_verify_token.assert_called_once_with("invalidtoken")

# Test get_current_user rejects a token for a user id that no longer exists
def test_get_current_user_deleted_user_rejected(mock_verify_token, db_session):
    """Test the core of the fix: a validly-signed token referencing a user id
    that isn't in the database (e.g. the user was deleted) must not
    authenticate, since get_current_user now does a real DB lookup instead
    of trusting the token payload alone."""
    mock_verify_token.return_value = uuid4()  # No such user exists.

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="validtoken", db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

# Test get_current_user turns an unexpected DB error into a clean 401
def test_get_current_user_db_error_rejected(mock_verify_token):
    mock_verify_token.return_value = uuid4()
    broken_db = MagicMock()
    broken_db.query.side_effect = RuntimeError("connection lost")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="validtoken", db=broken_db)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

# Test get_current_user with a minimal dict payload containing only 'sub'
def test_get_current_user_minimal_dict_payload(mock_verify_token, db_session, test_user):
    """Test get_current_user also accepts a dict payload with a 'sub' key,
    in case User.verify_token's return shape changes, and still resolves it
    to the real user via a DB lookup."""
    mock_verify_token.return_value = {"sub": test_user.id}

    user_response = get_current_user(token="validtoken", db=db_session)

    assert isinstance(user_response, UserResponse)
    assert user_response.id == test_user.id
    assert user_response.username == test_user.username

# Test get_current_user with a dict payload missing both 'id' and 'sub'
def test_get_current_user_dict_payload_missing_id(mock_verify_token, db_session):
    mock_verify_token.return_value = {"username": "someone"}

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="validtoken", db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

# Test get_current_user with a payload that is neither a dict, UUID, nor None
def test_get_current_user_unsupported_payload_type(mock_verify_token, db_session):
    mock_verify_token.return_value = "not-a-dict-or-uuid"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="validtoken", db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

    mock_verify_token.assert_called_once_with("validtoken")

# Test get_current_active_user with an active user
def test_get_current_active_user_active(mock_verify_token, db_session, test_user):
    mock_verify_token.return_value = test_user.id

    current_user = get_current_user(token="validtoken", db=db_session)
    active_user = get_current_active_user(current_user=current_user)

    assert isinstance(active_user, UserResponse)
    assert active_user.is_active is True

# Test get_current_active_user with a real, database-backed inactive user
def test_get_current_active_user_inactive(mock_verify_token, db_session):
    inactive_user = User(**create_fake_user(), is_active=False)
    db_session.add(inactive_user)
    db_session.commit()
    db_session.refresh(inactive_user)

    mock_verify_token.return_value = inactive_user.id
    current_user = get_current_user(token="validtoken", db=db_session)

    with pytest.raises(HTTPException) as exc_info:
        get_current_active_user(current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Inactive user"
