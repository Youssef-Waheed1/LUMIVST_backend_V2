from app.core.database import SessionLocal
from app.models.industry_group import IndustryGroupHistory
from sqlalchemy import text

def debug_group():
    db = SessionLocal()
    try:
        # Check Media and Entertainment specifically
        # Order 18 in screenshot, Rank 4, Last Week 18.
        # Check latest date
        latest_date = db.execute(text("SELECT MAX(date) FROM industry_group_history")).scalar()
        print(f"Latest Date: {latest_date}")
        
        group = db.query(IndustryGroupHistory).filter(
            IndustryGroupHistory.industry_group == 'Media and Entertainment',
            IndustryGroupHistory.date == latest_date
        ).first()
        
        if group:
            print("\n📊 Group: Media and Entertainment")
            print(f"Rank: {group.rank}")
            print(f"Last Week: {group.rank_1_week_ago}")
            print(f"Change vs Last Week (DB Value): {group.change_vs_last_week}")
            
            # Manual Check
            if group.rank and group.rank_1_week_ago:
                calc = group.rank_1_week_ago - group.rank
                print(f"Calculated Should Be: {calc}")
        else:
            print("❌ Group not found")
            
        print("-" * 30)
        # Check another one: Transportation (Rank 9, Last Week 19)
        group2 = db.query(IndustryGroupHistory).filter(
            IndustryGroupHistory.industry_group == 'Transportation',
            IndustryGroupHistory.date == latest_date
        ).first()
        
        if group2:
            print("\n📊 Group: Transportation")
            print(f"Rank: {group2.rank}")
            print(f"Last Week: {group2.rank_1_week_ago}")
            print(f"Change vs Last Week (DB Value): {group2.change_vs_last_week}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_group()
