from database import engine, Base

try:
    Base.metadata.create_all(bind=engine)
    print("Database connected successfully!")
except Exception as e:
    print("Error:", e)
