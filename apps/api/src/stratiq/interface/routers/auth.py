"""Auth router: register, login, refresh, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from stratiq.application.auth import AuthService
from stratiq.domain.exceptions import AuthenticationError, ConflictError
from stratiq.interface.deps import CurrentUser, get_auth_service, get_security
from stratiq.interface.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from stratiq.interface.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    auth_svc: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        user = await auth_svc.register(
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
            ip_address=_ip(request),
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    auth_svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        access, refresh = await auth_svc.login(
            email=str(body.email),
            password=body.password,
            ip_address=_ip(request),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    auth_svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        access, refresh = await auth_svc.refresh(body.refresh_token, ip_address=_ip(request))
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: CurrentUser,
    security=Depends(get_security),
    auth_svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    await auth_svc.logout(current_user.id, token, ip_address=_ip(request))
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
