# db_models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from database import Base

class GroceryItem(Base):
    __tablename__ = "grocery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
