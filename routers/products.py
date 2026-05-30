import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import User, Product, Category
from schemas import ProductResponse
from auth import get_current_admin
from config import Config
import uuid

router = APIRouter(prefix="/api/products", tags=["Products"])

def save_image(file: UploadFile, product_id: int, is_main: bool = False) -> str:
    ext = file.filename.split(".")[-1]
    filename = f"{product_id}_{'main' if is_main else str(uuid.uuid4())[:8]}.{ext}"
    filepath = os.path.join(Config.UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return f"/uploads/products/{filename}"

@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(Product.title.contains(search))
    
    products = query.all()
    
    result = []
    for product in products:
        product_data = ProductResponse(
            id=product.id,
            title=product.title,
            original_price=product.original_price,
            discount_price=product.discount_price,
            description=product.description,
            main_image=product.main_image,
            sub_images=json.loads(product.sub_images) if product.sub_images else [],
            colors=json.loads(product.colors) if product.colors else [],
            sizes=json.loads(product.sizes) if product.sizes else [],
            category_id=product.category_id,
            category_name=product.category.name if product.category else None,
            stock=product.stock,
            created_at=product.created_at
        )
        result.append(product_data)
    
    return result

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(
        id=product.id,
        title=product.title,
        original_price=product.original_price,
        discount_price=product.discount_price,
        description=product.description,
        main_image=product.main_image,
        sub_images=json.loads(product.sub_images) if product.sub_images else [],
        colors=json.loads(product.colors) if product.colors else [],
        sizes=json.loads(product.sizes) if product.sizes else [],
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        stock=product.stock,
        created_at=product.created_at
    )

@router.post("/")
async def create_product(
    title: str = Form(...),
    original_price: float = Form(...),
    discount_price: Optional[float] = Form(None),
    category_id: int = Form(...),
    description: Optional[str] = Form(None),
    colors: Optional[str] = Form(None),
    sizes: Optional[str] = Form(None),
    stock: int = Form(0),
    main_image: UploadFile = File(...),
    sub_images: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    new_product = Product(
        title=title,
        original_price=original_price,
        discount_price=discount_price,
        category_id=category_id,
        description=description,
        stock=stock,
        colors=json.dumps(json.loads(colors)) if colors else None,
        sizes=json.dumps(json.loads(sizes)) if sizes else None
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    main_image_path = save_image(main_image, new_product.id, is_main=True)
    new_product.main_image = main_image_path
    
    sub_images_paths = []
    for img in sub_images:
        path = save_image(img, new_product.id, is_main=False)
        sub_images_paths.append(path)
    new_product.sub_images = json.dumps(sub_images_paths)
    
    db.commit()
    db.refresh(new_product)
    
    return {
        "id": new_product.id,
        "message": "Product created successfully"
    }

@router.put("/{product_id}")
async def update_product(
    product_id: int,
    title: Optional[str] = Form(None),
    original_price: Optional[float] = Form(None),
    discount_price: Optional[float] = Form(None),
    category_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    colors: Optional[str] = Form(None),
    sizes: Optional[str] = Form(None),
    stock: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if title:
        product.title = title
    if original_price:
        product.original_price = original_price
    if discount_price is not None:
        product.discount_price = discount_price
    if category_id:
        product.category_id = category_id
    if description is not None:
        product.description = description
    if colors:
        product.colors = json.dumps(json.loads(colors))
    if sizes:
        product.sizes = json.dumps(json.loads(sizes))
    if stock is not None:
        product.stock = stock
    
    db.commit()
    
    return {"message": "Product updated successfully"}

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.main_image:
        main_path = os.path.join(".", product.main_image.lstrip("/"))
        if os.path.exists(main_path):
            os.remove(main_path)
    
    if product.sub_images:
        for img_path in json.loads(product.sub_images):
            full_path = os.path.join(".", img_path.lstrip("/"))
            if os.path.exists(full_path):
                os.remove(full_path)
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}