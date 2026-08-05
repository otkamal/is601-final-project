import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate, PasswordUpdate

BASE_FIELDS = dict(
    first_name="John",
    last_name="Doe",
    email="john.doe@example.com",
    username="johndoe",
)

def test_user_create_valid():
    """Test creating a valid UserCreate schema with a matching, strong password."""
    user = UserCreate(**BASE_FIELDS, password="SecurePass123!", confirm_password="SecurePass123!")
    assert user.password == "SecurePass123!"
    assert user.username == "johndoe"

def test_user_create_password_mismatch():
    """Test UserCreate fails if password and confirm_password don't match."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**BASE_FIELDS, password="SecurePass123!", confirm_password="Different123!")
    assert "passwords do not match" in str(exc_info.value).lower()

def test_user_create_password_missing_uppercase():
    """Test UserCreate fails if the password has no uppercase letter."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**BASE_FIELDS, password="securepass123!", confirm_password="securepass123!")
    assert "uppercase" in str(exc_info.value).lower()

def test_user_create_password_missing_lowercase():
    """Test UserCreate fails if the password has no lowercase letter."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**BASE_FIELDS, password="SECUREPASS123!", confirm_password="SECUREPASS123!")
    assert "lowercase" in str(exc_info.value).lower()

def test_user_create_password_missing_digit():
    """Test UserCreate fails if the password has no digit."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**BASE_FIELDS, password="SecurePass!", confirm_password="SecurePass!")
    assert "digit" in str(exc_info.value).lower()

def test_user_create_password_missing_special_char():
    """Test UserCreate fails if the password has no special character."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**BASE_FIELDS, password="SecurePass123", confirm_password="SecurePass123")
    assert "special character" in str(exc_info.value).lower()

def test_user_create_password_too_short_bypasses_field_check():
    """Test the model-level 'at least 8 characters' guard in validate_password_strength directly.

    Field(min_length=8) on `password` already rejects short passwords before
    this validator runs, so it can't be reached through the normal constructor.
    We use model_construct() to bypass field validation and exercise the guard
    itself, since it's meant as defense-in-depth for callers that skip validation.
    """
    user = UserCreate.model_construct(
        **BASE_FIELDS, password="Ab1!", confirm_password="Ab1!"
    )
    with pytest.raises(ValueError, match="at least 8 characters"):
        user.validate_password_strength()

def test_password_update_valid():
    """Test a valid PasswordUpdate where new_password and confirmation match and differ from current."""
    update = PasswordUpdate(
        current_password="OldPass123!",
        new_password="NewPass123!",
        confirm_new_password="NewPass123!",
    )
    assert update.new_password == "NewPass123!"

def test_password_update_confirmation_mismatch():
    """Test PasswordUpdate fails if new_password and confirm_new_password don't match."""
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass123!",
            confirm_new_password="Different123!",
        )
    assert "do not match" in str(exc_info.value).lower()

def test_password_update_same_as_current():
    """Test PasswordUpdate fails if the new password is the same as the current one."""
    with pytest.raises(ValidationError) as exc_info:
        PasswordUpdate(
            current_password="SamePass123!",
            new_password="SamePass123!",
            confirm_new_password="SamePass123!",
        )
    assert "must be different from current password" in str(exc_info.value).lower()
