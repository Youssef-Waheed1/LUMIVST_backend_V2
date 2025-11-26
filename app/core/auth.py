from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# إعدادات JWT
SECRET_KEY = os.getenv("SECRET_KEY", "tqsdlvy=jtead%x)jmn5@jl%ior3_5am)k%(6=q+myn0!!v%)i")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# إعدادات Hashing
import bcrypt
# Fix for passlib + bcrypt compatibility
if not hasattr(bcrypt, "__about__"):
    try:
        bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})
    except AttributeError:
        bcrypt.__about__ = type("about", (object,), {"__version__": "3.2.2"})

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ الاستيراد الصحيح من Redis
from app.core.redis import redis_cache

# ✅ مصادقة OAuth2
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ✅ دوال Redis معدلة لتعمل مع redis_cache (مع معالجة الأخطاء)
def store_token_in_redis(user_id: int, token: str):
    """تخزين التوكن في Redis مع expiry"""
    try:
        if redis_cache.redis_client:
            redis_cache.redis_client.setex(
                f"user_token:{user_id}", 
                ACCESS_TOKEN_EXPIRE_MINUTES * 60, 
                token
            )
    except Exception as e:
        print(f"⚠️ Warning: Could not store token in Redis: {e}")

def invalidate_token(user_id: int):
    """إلغاء التوكن (logout)"""
    try:
        if redis_cache.redis_client:
            redis_cache.redis_client.delete(f"user_token:{user_id}")
    except Exception as e:
        print(f"⚠️ Warning: Could not invalidate token in Redis: {e}")

def verify_token_exists(user_id: int, token: str) -> bool:
    """التحقق من أن التوكن لا يزال صالحاً في Redis"""
    try:
        if not redis_cache.redis_client:
            # إذا Redis غير متصل، اعتبر الـ token صالح (سيتم التحقق من JWT فقط)
            return True
        stored_token = redis_cache.redis_client.get(f"user_token:{user_id}")
        return stored_token and stored_token == token
    except Exception as e:
        print(f"⚠️ Warning: Could not verify token in Redis: {e}")
        return True  # Fallback to JWT validation only

def decode_token(token: str):
    """فك تشفير التوكن والتحقق منه"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توكن غير صالح",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ✅ دالة الاعتمادية (Dependency) للـ FastAPI
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and check if it's valid in Redis"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    # التحقق من وجود التوكن في Redis (مع معالجة حالة عدم الاتصال)
    if not verify_token_exists(user_id, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توكن غير صالح أو منتهي",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token