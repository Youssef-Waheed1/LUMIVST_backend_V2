
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import *
from app.models.user import User
from app.schemas.auth import *
from app.core.redis import store_reset_token, get_reset_token, delete_reset_token, store_verification_token, get_verification_token, delete_verification_token
from app.services.email import send_email
from app.core.config import settings
import uuid
import traceback

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # التحقق من وجود المستخدم
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل بالفعل")
    
    # إنشاء المستخدم
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        hashed_password=hashed_password, 
        full_name=user.full_name,
        is_verified=False # Ensure user is not verified initially
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # إنشاء وتخزين التوكن
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    try:
        await store_token_in_redis(db_user.id, access_token)
    except Exception as e:
        print(f"⚠️ Redis error during register: {e}")

    # Send Verification Email
    try:
        verification_token = str(uuid.uuid4())
        await store_verification_token(db_user.id, verification_token)
        verification_link = f"http://localhost:3000/auth/verify-email?token={verification_token}"
        
        email_body = f"""
        <h1>مرحباً {db_user.full_name}</h1>
        <p>شكراً لتسجيلك في LUMIVST. يرجى تأكيد بريدك الإلكتروني بالضغط على الرابط أدناه:</p>
        <a href="{verification_link}" style="background-color: #2563EB; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">تأكيد البريد الإلكتروني</a>
        <p>أو انسخ الرابط التالي:</p>
        <p>{verification_link}</p>
        """
        
        background_tasks.add_task(send_email, db_user.email, "تأكيد البريد الإلكتروني - LUMIVST", email_body)
    except Exception as e:
        print(f"⚠️ Failed to queue verification email: {e}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        
        if not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="كلمة المرور غير صحيحة")
        
        access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
        
        # Store token in Redis (safely)
        try:
            await store_token_in_redis(db_user.id, access_token)
        except Exception as e:
            print(f"⚠️ Redis error during login: {e}")
            # Continue even if Redis fails
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "is_verified": db_user.is_verified
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/logout")
async def logout(user_id: int, token: str = Depends(verify_token)):
    await invalidate_token(user_id)
    return {"message": "تم تسجيل الخروج بنجاح"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    # verify_token returns the token string after validation
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    return user

@router.put("/profile", response_model=UserResponse)
async def update_profile(user_update: UserUpdate, token: str = Depends(verify_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    # Update fields
    if user_update.full_name:
        db_user.full_name = user_update.full_name
    
    if user_update.email:
        # Check if email is taken by another user
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم بالفعل")
        db_user.email = user_update.email
    
    # Only update password if provided and not empty
    if user_update.password and len(user_update.password) >= 6:
        db_user.hashed_password = get_password_hash(user_update.password)
        
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.delete("/delete-account")
async def delete_account(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Delete user from database
    db.delete(db_user)
    db.commit()
    
    # Invalidate token
    await invalidate_token(user_id)
    
    return {"message": "تم حذف الحساب بنجاح"}

@router.post("/forget-password")
async def forget_password(request: ForgetPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Return success even if email not found to prevent enumeration
        return {"message": "تم إرسال رابط الاستعادة إذا كان البريد مسجلاً"}
    
    token = str(uuid.uuid4())
    await store_reset_token(user.id, token)
    
    reset_link = f"http://localhost:3000/auth/reset-password?token={token}"
    
    email_body = f"""
    <h1>استعادة كلمة المرور</h1>
    <p>لقد طلبت استعادة كلمة المرور لحسابك في LUMIVST.</p>
    <p>اضغط على الرابط أدناه لتعيين كلمة مرور جديدة:</p>
    <a href="{reset_link}" style="background-color: #2563EB; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">تغيير كلمة المرور</a>
    <p>أو انسخ الرابط التالي:</p>
    <p>{reset_link}</p>
    <p>هذا الرابط صالح لمدة 15 دقيقة.</p>
    """
    
    background_tasks.add_task(send_email, user.email, "استعادة كلمة المرور - LUMIVST", email_body)
    
    return {"message": "تم إرسال رابط الاستعادة"}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = await get_reset_token(request.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="توكن غير صالح أو منتهي")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    user.hashed_password = get_password_hash(request.password)
    db.commit()
    
    await delete_reset_token(request.token)
    return {"message": "تم تغيير كلمة المرور بنجاح"}

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user_id = await get_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="توكن غير صالح أو منتهي")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
        
    user.is_verified = True
    db.commit()
    
    await delete_verification_token(token)
    return {"message": "تم التحقق من البريد الإلكتروني بنجاح"}

# Social Login - Google
import httpx

@router.get("/google/login")
async def google_login():
    redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/google"
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&scope=openid%20email%20profile"
    }

@router.post("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/google"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        token_data = response.json()
        
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error_description", "Google Login Failed"))
        
    id_token = token_data["id_token"]
    
    # Get user info
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token_data['access_token']}")
        user_info = response.json()
        
    email = user_info.get("email")
    name = user_info.get("name")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user
        # Generate random password
        random_password = str(uuid.uuid4())
        hashed_password = get_password_hash(random_password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            is_verified=True # Email verified by Google
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    # Create JWT
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    await store_token_in_redis(user.id, access_token)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified
        }
    }

# Social Login - Facebook
@router.get("/facebook/login")
async def facebook_login():
    redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/facebook"
    return {
        "url": f"https://www.facebook.com/v18.0/dialog/oauth?client_id={settings.FACEBOOK_CLIENT_ID}&redirect_uri={redirect_uri}&scope=public_profile,email"
    }

@router.post("/facebook/callback")
async def facebook_callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/facebook"
    params = {
        "client_id": settings.FACEBOOK_CLIENT_ID,
        "client_secret": settings.FACEBOOK_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(token_url, params=params)
        token_data = response.json()
        
    if "error" in token_data:
        raise HTTPException(status_code=400, detail=token_data.get("error", {}).get("message", "Facebook Login Failed"))
        
    access_token = token_data["access_token"]
    
    # Get user info
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={access_token}")
        user_info = response.json()
        
    email = user_info.get("email")
    name = user_info.get("name")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Facebook")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user
        random_password = str(uuid.uuid4())
        hashed_password = get_password_hash(random_password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            is_verified=True  # Email verified by Facebook
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    # Create JWT
    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    await store_token_in_redis(user.id, jwt_token)
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified
        }
    }
