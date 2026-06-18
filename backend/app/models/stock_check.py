from datetime import datetime

from ..extensions import db


class StockCheck(db.Model):
    __tablename__ = "stock_checks"

    id = db.Column(db.Integer, primary_key=True)
    check_no = db.Column(db.String(40), nullable=False, unique=True)
    status = db.Column(db.String(10), nullable=False, default="draft")
    operator = db.Column(db.String(40), nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship(
        "StockCheckItem", back_populates="stock_check", cascade="all, delete-orphan"
    )

    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "checkNo": self.check_no,
            "status": self.status,
            "operator": self.operator,
            "note": self.note,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        else:
            profit_count = sum(1 for item in self.items if item.diff_type == "profit")
            loss_count = sum(1 for item in self.items if item.diff_type == "loss")
            data["profitCount"] = profit_count
            data["lossCount"] = loss_count
            data["itemCount"] = len(self.items)
        return data


class StockCheckItem(db.Model):
    __tablename__ = "stock_check_items"

    id = db.Column(db.Integer, primary_key=True)
    stock_check_id = db.Column(
        db.Integer, db.ForeignKey("stock_checks.id"), nullable=False
    )
    ingredient_id = db.Column(
        db.Integer, db.ForeignKey("ingredients.id"), nullable=False
    )
    system_stock = db.Column(db.Float, nullable=False)
    actual_stock = db.Column(db.Float, nullable=False)
    diff_quantity = db.Column(db.Float, nullable=False)
    diff_type = db.Column(db.String(10), nullable=False)

    stock_check = db.relationship("StockCheck", back_populates="items")
    ingredient = db.relationship("Ingredient")

    def to_dict(self):
        return {
            "id": self.id,
            "stockCheckId": self.stock_check_id,
            "ingredientId": self.ingredient_id,
            "ingredientName": self.ingredient.name if self.ingredient else None,
            "category": self.ingredient.category if self.ingredient else None,
            "unit": self.ingredient.unit if self.ingredient else None,
            "systemStock": self.system_stock,
            "actualStock": self.actual_stock,
            "diffQuantity": self.diff_quantity,
            "diffType": self.diff_type,
        }
