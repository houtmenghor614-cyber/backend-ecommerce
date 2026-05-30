from database import SessionLocal
from models import User

db = SessionLocal()
users = db.query(User).all()

print("All users in database:")
for u in users:
    print(f"  Email: {u.email}, Role: {u.role}")

if len(users) == 0:
    print("No users found! Creating admin user...")
    from auth import get_password_hash
    admin = User(
        full_name="Administrator",
        email="admin@dynastore.com",
        phone_number="0123456789",
        password_hash=get_password_hash("admin123"),
        role="admin",
        is_google_user=False
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created!")
    print("Email: admin@dynastore.com")
    print("Password: admin123")

db.close()