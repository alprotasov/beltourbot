from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User, Route
from .schemas import UserCreate, UserUpdate, RouteCreate, RouteUpdate

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(**user.dict())
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
    except Exception:
        await db.rollback()
        raise
    return db_user

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    try:
        await db.commit()
        await db.refresh(db_user)
    except Exception:
        await db.rollback()
        raise
    return db_user

async def delete_user(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    snapshot = {col.name: getattr(db_user, col.name) for col in db_user.__table__.columns}
    try:
        await db.delete(db_user)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return snapshot

async def get_route(db: AsyncSession, route_id: int) -> Optional[Route]:
    result = await db.execute(select(Route).where(Route.id == route_id))
    return result.scalars().first()

async def list_routes(db: AsyncSession, filters: Dict[str, Any] = None) -> List[Route]:
    filters = filters or {}
    filter_params = filters.copy()
    skip = filter_params.pop("skip", 0)
    limit = filter_params.pop("limit", 100)
    allowed_filters = {col.name for col in Route.__table__.columns}
    unsupported = set(filter_params.keys()) - allowed_filters
    if unsupported:
        raise ValueError(f"Unsupported filter fields: {', '.join(unsupported)}")
    query = select(Route)
    for field, value in filter_params.items():
        if value is not None:
            query = query.where(getattr(Route, field) == value)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def create_route(db: AsyncSession, route: RouteCreate) -> Route:
    db_route = Route(**route.dict())
    db.add(db_route)
    try:
        await db.commit()
        await db.refresh(db_route)
    except Exception:
        await db.rollback()
        raise
    return db_route

async def update_route(db: AsyncSession, route_id: int, data: RouteUpdate) -> Optional[Route]:
    db_route = await get_route(db, route_id)
    if not db_route:
        return None
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_route, field, value)
    try:
        await db.commit()
        await db.refresh(db_route)
    except Exception:
        await db.rollback()
        raise
    return db_route

async def delete_route(db: AsyncSession, route_id: int) -> Optional[Dict[str, Any]]:
    db_route = await get_route(db, route_id)
    if not db_route:
        return None
    snapshot = {col.name: getattr(db_route, col.name) for col in db_route.__table__.columns}
    try:
        await db.delete(db_route)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return snapshot