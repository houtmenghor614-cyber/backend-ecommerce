from database import SessionLocal, Base, engine
from models import User, Category, Product, Order, OrderItem
from auth import get_password_hash

print("=" * 50)
print("CLEANING AND RESETTING DATABASE")
print("=" * 50)

# Drop all tables
Base.metadata.drop_all(bind=engine)
print("✅ Dropped all tables")

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ Created all tables")

db = SessionLocal()

# Create admin user
admin = User(
    full_name="Administrator",
    email="admin@dynastore.com",
    phone_number="0123456789",
    password_hash=get_password_hash("admin123"),
    role="admin",
    is_google_user=False
)
db.add(admin)
print("✅ Admin user created")

# Create categories
categories = ["Men", "Women", "Kids", "Clothes", "Accessories", "Shoes", "Bags"]
for cat_name in categories:
    cat = Category(name=cat_name)
    db.add(cat)
    print(f"✅ Category added: {cat_name}")

db.commit()
print("=" * 50)
print("SETUP COMPLETE!")
print("=" * 50)
print("Admin Login:")
print("  Email: admin@dynastore.com")
print("  Password: admin123")
print("=" * 50)

# Verify
admin_check = db.query(User).filter(User.email == "admin@dynastore.com").first()
print(f"\nVerification:")
print(f"  Admin exists: {admin_check is not None}")
print(f"  Admin role: {admin_check.role if admin_check else 'N/A'}")
print(f"  Total categories: {db.query(Category).count()}")

db.close()
print("\n✅ Database is ready!")