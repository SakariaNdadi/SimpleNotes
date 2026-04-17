from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Label


def get_labels(db: Session, user_id: str) -> list[Label]:
    return db.query(Label).filter(Label.user_id == user_id).order_by(Label.title).all()


def get_label(db: Session, label_id: str, user_id: str) -> Label | None:
    return db.query(Label).filter(Label.id == label_id, Label.user_id == user_id).first()


def create_label(db: Session, user_id: str, title: str, description: str) -> Label | str:
    label = Label(user_id=user_id, title=title.strip(), description=description.strip())
    db.add(label)
    try:
        db.commit()
        db.refresh(label)
        return label
    except IntegrityError:
        db.rollback()
        return "Label with that title already exists"


def update_label(db: Session, label: Label, title: str, description: str) -> Label | str:
    label.title = title.strip()
    label.description = description.strip()
    try:
        db.commit()
        db.refresh(label)
        return label
    except IntegrityError:
        db.rollback()
        return "Label with that title already exists"


def delete_label(db: Session, label: Label) -> None:
    # Unlink notes from this label before deleting
    for note in label.notes:
        note.label_id = None
    db.delete(label)
    db.commit()
