from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.profile import CompanyProfile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_profile_by_symbol(self, symbol: str) -> Optional[CompanyProfile]:
        """البحث عن ملف شركة بالرمز"""
        try:
            return self.db.query(CompanyProfile).filter(CompanyProfile.symbol == symbol).first()
        except Exception as e:
            logger.error(f"خطأ في البحث عن الملف الشخصي للرمز {symbol}: {e}")
            return None
    
    def get_all_profiles(self) -> List[CompanyProfile]:
        """جلب كل الملفات الشخصية"""
        try:
            return self.db.query(CompanyProfile).all()
        except Exception as e:
            logger.error(f"خطأ في جلب كل الملفات الشخصية: {e}")
            return []
    
    def create_or_update_profile(self, profile_data: Dict[str, Any]) -> Optional[CompanyProfile]:
        """إنشاء أو تحديث ملف شخصي"""
        try:
            symbol = profile_data.get('symbol')
            if not symbol:
                return None
            
            existing_profile = self.get_profile_by_symbol(symbol)
            
            if existing_profile:
                # تحديث البيانات
                for key, value in profile_data.items():
                    if hasattr(existing_profile, key) and value is not None:
                        setattr(existing_profile, key, value)
                existing_profile.updated_at = datetime.now()
            else:
                # إنشاء جديد
                existing_profile = CompanyProfile(**profile_data)
                self.db.add(existing_profile)
            
            self.db.commit()
            self.db.refresh(existing_profile)
            return existing_profile
            
        except Exception as e:
            logger.error(f"خطأ في حفظ/تحديث الملف الشخصي {profile_data.get('symbol')}: {e}")
            self.db.rollback()
            return None
    
    def bulk_create_or_update_profiles(self, profiles_data: List[Dict[str, Any]]) -> List[CompanyProfile]:
        """حفظ مجموعة من الملفات الشخصية"""
        results = []
        for profile_data in profiles_data:
            profile = self.create_or_update_profile(profile_data)
            if profile:
                results.append(profile)
        return results