from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Base, engine, get_db
from db_models import GroceryItem

app = FastAPI()
Base.metadata.create_all(bind=engine)

@app.post("/items/{item_name}/{quantity}")
def add_item(item_name: str, quantity: int, db: Session = Depends(get_db)):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0.")

    # buscar por nombre
    item = db.execute(select(GroceryItem).where(GroceryItem.item_name == item_name)).scalar_one_or_none()

    if item:
        item.quantity += quantity
    else:
        item = GroceryItem(item_name=item_name, quantity=quantity)
        db.add(item)

    db.commit()
    db.refresh(item)
    return {"item": {"item_id": item.id, "item_name": item.item_name, "quantity": item.quantity}}

@app.get("/items/{item_id}")
def list_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(GroceryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return {"item": {"item_id": item.id, "item_name": item.item_name, "quantity": item.quantity}}

@app.get("/items")
def list_items(db: Session = Depends(get_db)):
    items = db.execute(select(GroceryItem)).scalars().all()
    return {
        "items": [
            {"item_id": i.id, "item_name": i.item_name, "quantity": i.quantity}
            for i in items
        ]
    }

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(GroceryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    db.delete(item)
    db.commit()
    return {"result": "Item deleted."}

@app.delete("/items/{item_id}/{quantity}")
def remove_quantity(item_id: int, quantity: int, db: Session = Depends(get_db)):
    item = db.get(GroceryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0.")

    if item.quantity <= quantity:
        db.delete(item)
        db.commit()
        return {"result": "Item deleted."}
    else:
        item.quantity -= quantity
        db.commit()
        db.refresh(item)
        return {"result": f"{quantity} items removed.", "remaining": item.quantity}
