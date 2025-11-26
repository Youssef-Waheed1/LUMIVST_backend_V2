from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.contact import ContactMessage
from app.schemas.contact import ContactCreate, ContactResponse
from app.api.deps import get_current_admin

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """
    Submit a new contact message (Public)
    """
    db_contact = ContactMessage(
        name=contact.name,
        email=contact.email,
        message=contact.message
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.get("/", response_model=List[ContactResponse])
def get_contacts(
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Get all contact messages (Admin only)
    """
    query = db.query(ContactMessage)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (ContactMessage.name.ilike(search_filter)) | 
            (ContactMessage.email.ilike(search_filter))
        )
    
    contacts = query.order_by(ContactMessage.created_at.desc()).offset(skip).limit(limit).all()
    return contacts

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    id: int, 
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Delete a contact message (Admin only)
    """
    contact = db.query(ContactMessage).filter(ContactMessage.id == id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(contact)
    db.commit()
    return None
