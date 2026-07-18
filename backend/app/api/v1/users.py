"""Public user profile routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.me import PublicUserResponse
from app.services.profile import ProfileService

router = APIRouter(tags=["users"])


@router.get("/users/{username}", response_model=PublicUserResponse)
async def get_public_user(
    username: str,
    session: AsyncSession = Depends(get_db_session),
) -> PublicUserResponse:
    return await ProfileService(session).get_public_user(username)
