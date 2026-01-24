from app.core.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('prices')
print("Columns in prices table:")
for c in columns:
    print(c['name'])
