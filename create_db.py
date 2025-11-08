from database import engine, Base
from models import User  # import all models

Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")
