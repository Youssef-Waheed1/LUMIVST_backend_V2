from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# إعدادات JWT
SECRET_KEY = os.getenv("SECRET_KEY", "tqsdlvy=jtead%x)jmn5@jl%ior3_5am)k%(6=q+myn0!!v%)i")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# إعدادات Hashing - using pbkdf2_sha256 instead of bcrypt to avoid 72-byte limit
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

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
async def store_token_in_redis(user_id: int, token: str):
    """تخزين التوكن في Redis مع expiry"""
    try:
        if redis_cache.redis_client:
            await redis_cache.redis_client.setex(
                f"user_token:{user_id}", 
                ACCESS_TOKEN_EXPIRE_MINUTES * 60, 
                token
            )
            print(f"✅ Token stored in Redis for user {user_id}")
        else:
            print("⚠️ Redis not connected, token not stored")
    except Exception as e:
        print(f"⚠️ Warning: Could not store token in Redis: {e}")

async def invalidate_token(user_id: int):
    """إلغاء التوكن (logout)"""
    try:
        if redis_cache.redis_client:
            await redis_cache.redis_client.delete(f"user_token:{user_id}")
            print(f"✅ Token invalidated for user {user_id}")
    except Exception as e:
        print(f"⚠️ Warning: Could not invalidate token in Redis: {e}")

async def verify_token_exists(user_id: int, token: str) -> bool:
    """التحقق من أن التوكن لا يزال صالحاً في Redis"""
    try:
        if not redis_cache.redis_client:
            print("⚠️ Redis not connected, skipping token check")
            return True
            
        stored_token = await redis_cache.redis_client.get(f"user_token:{user_id}")
        
        if not stored_token:
            print(f"❌ Token not found in Redis for user {user_id}")
            return False
            
        if stored_token != token:
            print(f"❌ Token mismatch for user {user_id}")
            return False
            
        print(f"✅ Token verified for user {user_id}")
        return True
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
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and check if it's valid in Redis"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    
    # التحقق من وجود التوكن في Redis (مع معالجة حالة عدم الاتصال)
    if not await verify_token_exists(user_id, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توكن غير صالح أو منتهي",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token