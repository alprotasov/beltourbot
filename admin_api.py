import os
from enum import Enum
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_session
from models import Route, User

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserRoleEnum(str, Enum):
    admin = "admin"
    user = "user"
    moderator = "moderator"

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, TypeError, ValueError):
        raise credentials_exception
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRoleEnum.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

class RouteBase(BaseModel):
    name: str
    description: Optional[str] = None
    language: str
    is_active: bool = True

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None

class RouteOut(RouteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserRoleUpdate(BaseModel):
    role: UserRoleEnum

class StatsOut(BaseModel):
    total_routes: int
    total_users: int

router = APIRouter(dependencies=[Depends(get_current_admin_user)])

@router.get("/routes", response_model=List[RouteOut])
async def get_routes(
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    session: AsyncSession = Depends(get_session)
):
    offset = (page - 1) * size
    result = await session.execute(
        select(Route).order_by(Route.id).offset(offset).limit(size)
    )
    return result.scalars().all()

@router.get("/routes/{route_id}", response_model=RouteOut)
async def get_route(
    route_id: int,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Route).where(Route.id == route_id))
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return route

@router.post("/routes", status_code=status.HTTP_201_CREATED, response_model=RouteOut)
async def create_route(
    route: RouteCreate,
    session: AsyncSession = Depends(get_session)
):
    new_route = Route(**route.dict())
    try:
        session.add(new_route)
        await session.commit()
        await session.refresh(new_route)
        return new_route
    except Exception:
        await session.rollback()
        raise

@router.put("/routes/{route_id}", response_model=RouteOut)
async def update_route(
    route_id: int,
    route_update: RouteUpdate,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Route).where(Route.id == route_id))
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    update_data = route_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(route, key, value)
    try:
        session.add(route)
        await session.commit()
        await session.refresh(route)
        return route
    except Exception:
        await session.rollback()
        raise

@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: int,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Route).where(Route.id == route_id))
    route = result.scalars().first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    try:
        session.delete(route)
        await session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        await session.rollback()
        raise

@router.get("/users", response_model=List[UserOut])
async def get_users(
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User))
    return result.scalars().all()

@router.put("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role_update.role.value
    try:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except Exception:
        await session.rollback()
        raise

@router.get("/statistics", response_model=StatsOut)
async def get_statistics(
    session: AsyncSession = Depends(get_session)
):
    result_routes = await session.execute(select(func.count()).select_from(Route))
    total_routes = result_routes.scalar_one()
    result_users = await session.execute(select(func.count()).select_from(User))
    total_users = result_users.scalar_one()
    return StatsOut(total_routes=total_routes, total_users=total_users)

def include_api_routes(app: FastAPI):
    app.include_router(router)

def create_admin_app() -> FastAPI:
    app = FastAPI(title="Admin API", version="1.0.0")
    include_api_routes(app)
    return app

app = create_admin_app()