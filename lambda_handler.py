from mangum import Mangum
from app.main import app

# Lambda handler for AWS Lambda
# Mangum adapts FastAPI to work with AWS Lambda's event/context model
handler = Mangum(app, lifespan="off")
