from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, extract
from datetime import date, timedelta
from ..database.models import Contact
from ..schemas import ContactCreate, ContactUpdate

def create_contact(db: Session, contact: ContactCreate):
    db_contact = Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Contact).offset(skip).limit(limit).all()

def get_contact(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()

def update_contact(db: Session, contact_id: int, contact: ContactUpdate):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact:
        for key, value in contact.dict().items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact

def delete_contact(db: Session, contact_id: int):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact

def search_contacts(db: Session, search_query: str):
    return db.query(Contact).filter(
        or_(
            Contact.first_name.ilike(f"%{search_query}%"),
            Contact.last_name.ilike(f"%{search_query}%"),
            Contact.email.ilike(f"%{search_query}%")
        )
    ).all()

def get_upcoming_birthdays(db: Session):
    today = date.today()
    seven_days_later = today + timedelta(days=7)
    
    # Extracting the day and month for comparison
    today_month = today.month
    today_day = today.day
    end_month = seven_days_later.month
    end_day = seven_days_later.day
    
    # If the period does not cross into the next month
    if today_month == end_month:
        contacts = db.query(Contact).filter(
            and_(
                extract('month', Contact.birthday) == today_month,
                extract('day', Contact.birthday) >= today_day,
                extract('day', Contact.birthday) <= end_day
            )
        ).all()
    else:
        # If the period crosses into the next month
        contacts = db.query(Contact).filter(
            or_(
                and_(
                    extract('month', Contact.birthday) == today_month,
                    extract('day', Contact.birthday) >= today_day
                ),
                and_(
                    extract('month', Contact.birthday) == end_month,
                    extract('day', Contact.birthday) <= end_day
                )
            )
        ).all()
    
    return contacts
