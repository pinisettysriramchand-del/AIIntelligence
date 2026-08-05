from fastapi import APIRouter, Depends, Header, HTTPException, status

from stratiq.domain.exceptions import AuthenticationError, ConflictError, ValidationError
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from stratiq.domain.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, services: Services = Depends(get_services)) -> UserResponse:
    try:
        user = await services.auth.register(body.email, body.password, body.full_name)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, services: Services = Depends(get_services)) -> TokenResponse:
    try:
        tokens = await services.auth.login(body.email, body.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, services: Services = Depends(get_services)) -> TokenResponse:
    try:
        tokens = await services.auth.refresh(body.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest | None = None,
    authorization: str | None = Header(default=None),
    services: Services = Depends(get_services),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access = authorization.split(" ", 1)[1].strip()
    refresh_token = body.refresh_token if body else None
    await services.auth.logout(access, refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name)
