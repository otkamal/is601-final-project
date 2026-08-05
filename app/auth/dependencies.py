from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserResponse
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Dependency to get the current user from the JWT token.

    Looks the user up in the database so the returned profile -- and
    crucially is_active -- reflects the user's real, current state rather
    than data assumed from the token alone. This also means a token for a
    user who has since been deactivated or deleted stops working immediately
    instead of remaining valid until the token's natural expiry.

    User.verify_token() currently always returns a bare UUID (or None), but
    a dict payload with an 'id'/'sub' key is also accepted here in case its
    return shape changes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = User.verify_token(token)
    if token_data is None:
        raise credentials_exception

    if isinstance(token_data, UUID):
        user_id = token_data
    elif isinstance(token_data, dict):
        user_id = token_data.get("id") or token_data.get("sub")
    else:
        raise credentials_exception

    if user_id is None:
        raise credentials_exception

    try:
        user = db.query(User).filter(User.id == user_id).first()
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return UserResponse.model_validate(user)

def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency to ensure that the current user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
