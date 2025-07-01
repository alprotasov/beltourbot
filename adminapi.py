from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from database import get_db
from models import Route
from schemas import AdminRouteCreate, AdminRouteUpdate, AdminRouteOut
from admin_api import get_current_admin_user

router = APIRouter(
    prefix="/admin/routes",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)]
)

@router.get("/", response_model=List[AdminRouteOut])
def get_admin_routes(
    limit: int = Query(100, gt=0, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return db.query(Route).limit(limit).offset(offset).all()

@router.post("/", response_model=AdminRouteOut, status_code=status.HTTP_201_CREATED)
def create_admin_route(
    route_in: AdminRouteCreate,
    db: Session = Depends(get_db)
):
    route = Route(**route_in.dict())
    db.add(route)
    try:
        db.commit()
        db.refresh(route)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}"
        )
    return route

@router.patch("/{route_id}", response_model=AdminRouteOut)
def update_admin_route(
    route_id: int,
    route_in: AdminRouteUpdate,
    db: Session = Depends(get_db)
):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    data = route_in.dict(exclude_unset=True)
    allowed_fields = set(AdminRouteUpdate.__fields__.keys())
    for field in allowed_fields:
        if field in data:
            setattr(route, field, data[field])
    try:
        db.commit()
        db.refresh(route)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}"
        )
    return route

@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_route(
    route_id: int,
    db: Session = Depends(get_db)
):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    try:
        db.delete(route)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}"
        )