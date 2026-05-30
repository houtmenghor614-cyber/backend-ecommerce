from database import SessionLocal
from models import Category

db = SessionLocal()

# List of categories you want
categories = [
    "Men",
    "Women", 
    "Kids",
    "Clothes",
    "Accessories",
    "Shoes",
    "Bags",
    "Jewelry",
    "Sportswear",
    "Electronics"
]

print("=" * 50)
print("ADDING CATEGORIES TO DATABASE")
print("=" * 50)

added = 0
exists = 0

for cat_name in categories:
    existing = db.query(Category).filter(Category.name == cat_name).first()
    if not existing:
        new_cat = Category(name=cat_name)
        db.add(new_cat)
        print(f"✅ Added: {cat_name}")
        added += 1
    else:
        print(f"⚠️ Already exists: {cat_name}")
        exists += 1

db.commit()

print("\n" + "=" * 50)
print(f"SUMMARY: {added} added, {exists} already existed")
print("=" * 50)

# Show all categories
print("\n📋 ALL CATEGORIES IN DATABASE:")
all_cats = db.query(Category).all()
for cat in all_cats:
    print(f"   {cat.id}. {cat.name}")

db.close()
print("\n✅ Done! You can close this window.")