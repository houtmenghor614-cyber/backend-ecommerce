# create_admin.py
from database import SessionLocal
from models import User
from auth import get_password_hash

def create_admin():
    db = SessionLocal()
    
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == "admin@dynastore.com").first()
    if existing_admin:
        print("Admin user already exists!")
        db.close()
        return
    
    # Create admin user
    admin = User(
        full_name="Admin User",
        email="admin@dynastore.com",
        phone_number="012345678",
        password_hash=get_password_hash("admin123"),
        role="admin",
        is_google_user=False
    )
    
    db.add(admin)
    db.commit()
    print("=" * 50)
    print("Admin user created successfully!")
    print("Email: admin@dynastore.com")
    print("Password: admin123")
    print("=" * 50)
    db.close()

if __name__ == "__main__":
    create_admin()