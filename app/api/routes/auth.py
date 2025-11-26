from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import *
from app.models.user import User
from app.core.auth import *
from app.models.user import User
from app.schemas.auth import *
from app.core.redis import store_reset_token, get_reset_token, delete_reset_token, store_verification_token, get_verification_token, delete_verification_token
import uuid


router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: Session = Depends(get_db)):
    # التحقق من وجود المستخدم
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل")
    
    # إنشاء المستخدم
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        hashed_password=hashed_password, 
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # إنشاء وتخزين التوكن
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    store_token_in_redis(db_user.id, access_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    store_token_in_redis(db_user.id, access_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(user_id: int, token: str = Depends(verify_token)):
    invalidate_token(user_id)
    return {"message": "تم تسجيل الخروج بنجاح"}

@router.get("/me", response_model=UserResponse)
def get_current_user(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import *
from app.models.user import User
from app.core.auth import *
from app.models.user import User
from app.schemas.auth import *
from app.core.redis import store_reset_token, get_reset_token, delete_reset_token, store_verification_token, get_verification_token, delete_verification_token
import uuid


router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: Session = Depends(get_db)):
    # التحقق من وجود المستخدم
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل")
    
    # إنشاء المستخدم
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        hashed_password=hashed_password, 
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # إنشاء وتخزين التوكن
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    store_token_in_redis(db_user.id, access_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    store_token_in_redis(db_user.id, access_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(user_id: int, token: str = Depends(verify_token)):
    invalidate_token(user_id)
    return {"message": "تم تسجيل الخروج بنجاح"}

@router.get("/me", response_model=UserResponse)
def get_current_user(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    return user

@router.post("/forget-password")
async def forget_password(request: ForgetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="البريد غير موجود")
    
    token = str(uuid.uuid4())
    await store_reset_token(user.id, token)
    
    reset_link = f"http://localhost:3000/auth/reset-password?token={token}"
    print(f"📧 Reset Link: {reset_link}")  # Simulate email
    
    return {"message": "تم إرسال رابط الاستعادة"}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = await get_reset_token(request.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="توكن غير صالح")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    user.hashed_password = get_password_hash(request.password)
    db.commit()
    
    await delete_reset_token(request.token)
    return {"message": "تم تغيير كلمة المرور"}

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user_id = await get_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="توكن غير صالح")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    user.is_verified = True
    db.commit()
    
    await delete_verification_token(token)
    return {"message": "تم التحقق من البريد الإلكتروني"}