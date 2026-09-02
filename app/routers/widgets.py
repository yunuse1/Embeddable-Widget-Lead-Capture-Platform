import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Widget
from app.schemas.widget import WidgetCreate, WidgetResponse, WidgetUpdate


router = APIRouter(prefix="/widgets", tags=["Widgets"])


def generate_public_id() -> str:
    return secrets.token_urlsafe(18)[:24]


@router.post("", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
def create_widget(
    payload: WidgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    widget = Widget(
        tenant_id=current_user.tenant_id,
        public_id=generate_public_id(),
        **payload.model_dump(),
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.get("", response_model=list[WidgetResponse])
def list_widgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(Widget)
            .where(Widget.tenant_id == current_user.tenant_id)
            .order_by(Widget.created_at.desc())
        )
    )


@router.get("/{widget_id}", response_model=WidgetResponse)
def get_widget(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    widget = db.scalar(
        select(Widget).where(
            Widget.id == widget_id,
            Widget.tenant_id == current_user.tenant_id,
        )
    )
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.patch("/{widget_id}", response_model=WidgetResponse)
def update_widget(
    widget_id: int,
    payload: WidgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    widget = db.scalar(
        select(Widget).where(
            Widget.id == widget_id,
            Widget.tenant_id == current_user.tenant_id,
        )
    )
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(widget, key, value)

    db.commit()
    db.refresh(widget)
    return widget


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    widget = db.scalar(
        select(Widget).where(
            Widget.id == widget_id,
            Widget.tenant_id == current_user.tenant_id,
        )
    )
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")

    db.delete(widget)
    db.commit()
