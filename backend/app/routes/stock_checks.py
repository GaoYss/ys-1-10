import time
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Ingredient, StockCheck, StockCheckItem, StockRecord

stock_checks_bp = Blueprint("stock_checks", __name__)


def generate_check_no():
    now = datetime.utcnow()
    return f"PD{now.strftime('%Y%m%d%H%M%S')}"


def generate_unique_check_no(max_retries=10):
    for i in range(max_retries):
        check_no = generate_check_no()
        if i > 0:
            check_no = f"{check_no}{i}"
        existing = StockCheck.query.filter_by(check_no=check_no).first()
        if not existing:
            return check_no
        time.sleep(0.01)
    timestamp = int(time.time() * 1000)
    return f"PD{timestamp}"


def calc_diff(system_stock, actual_stock):
    diff = actual_stock - system_stock
    if diff > 0:
        return diff, "profit"
    elif diff < 0:
        return diff, "loss"
    else:
        return 0, "normal"


@stock_checks_bp.get("")
def list_stock_checks():
    status = request.args.get("status", "").strip()
    query = StockCheck.query
    if status:
        query = query.filter_by(status=status)
    checks = query.order_by(StockCheck.created_at.desc()).all()
    return jsonify([check.to_dict(include_items=False) for check in checks])


@stock_checks_bp.get("/<int:check_id>")
def get_stock_check(check_id):
    check = StockCheck.query.get_or_404(check_id)
    return jsonify(check.to_dict(include_items=True))


@stock_checks_bp.post("")
def create_stock_check():
    data = request.get_json() or {}
    operator = data.get("operator", "系统管理员")
    note = data.get("note", "")
    items_data = data.get("items", [])

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            check = StockCheck(
                check_no=generate_unique_check_no(),
                status="draft",
                operator=operator,
                note=note,
            )
            db.session.add(check)
            db.session.flush()

            for item_data in items_data:
                ingredient = Ingredient.query.get_or_404(item_data["ingredientId"])
                actual_stock = float(item_data.get("actualStock", ingredient.stock))
                diff_quantity, diff_type = calc_diff(ingredient.stock, actual_stock)
                item = StockCheckItem(
                    stock_check_id=check.id,
                    ingredient_id=ingredient.id,
                    system_stock=ingredient.stock,
                    actual_stock=actual_stock,
                    diff_quantity=diff_quantity,
                    diff_type=diff_type,
                )
                db.session.add(item)

            db.session.commit()
            return check.to_dict(include_items=True), 201
        except IntegrityError:
            db.session.rollback()
            if attempt == max_attempts - 1:
                raise
            time.sleep(0.05)
    return {"message": "创建盘点单失败，请重试"}, 500


@stock_checks_bp.put("/<int:check_id>")
def update_stock_check(check_id):
    check = StockCheck.query.get_or_404(check_id)
    if check.status != "draft":
        return {"message": "仅草稿状态的盘点单可以修改"}, 400

    data = request.get_json() or {}
    check.operator = data.get("operator", check.operator)
    check.note = data.get("note", check.note)
    items_data = data.get("items")

    if items_data is not None:
        StockCheckItem.query.filter_by(stock_check_id=check.id).delete()
        for item_data in items_data:
            ingredient = Ingredient.query.get_or_404(item_data["ingredientId"])
            actual_stock = float(item_data.get("actualStock", ingredient.stock))
            diff_quantity, diff_type = calc_diff(ingredient.stock, actual_stock)
            item = StockCheckItem(
                stock_check_id=check.id,
                ingredient_id=ingredient.id,
                system_stock=ingredient.stock,
                actual_stock=actual_stock,
                diff_quantity=diff_quantity,
                diff_type=diff_type,
            )
            db.session.add(item)

    db.session.commit()
    return check.to_dict(include_items=True)


@stock_checks_bp.post("/<int:check_id>/submit")
def submit_stock_check(check_id):
    check = StockCheck.query.get_or_404(check_id)
    if check.status != "draft":
        return {"message": "仅草稿状态的盘点单可以提交"}, 400
    if not check.items:
        return {"message": "盘点单没有明细项"}, 400

    for item in check.items:
        ingredient = Ingredient.query.get(item.ingredient_id)
        if not ingredient:
            continue
        if item.diff_type == "profit":
            ingredient.stock = item.actual_stock
            record = StockRecord(
                ingredient_id=ingredient.id,
                record_type="in",
                quantity=abs(item.diff_quantity),
                operator=check.operator,
                source="盘点盘盈",
                note=f"盘点单号：{check.check_no}",
            )
            db.session.add(record)
        elif item.diff_type == "loss":
            ingredient.stock = item.actual_stock
            record = StockRecord(
                ingredient_id=ingredient.id,
                record_type="out",
                quantity=abs(item.diff_quantity),
                operator=check.operator,
                source="盘点盘亏",
                note=f"盘点单号：{check.check_no}",
            )
            db.session.add(record)

    check.status = "completed"
    check.completed_at = datetime.utcnow()
    db.session.commit()
    return check.to_dict(include_items=True)


@stock_checks_bp.delete("/<int:check_id>")
def delete_stock_check(check_id):
    check = StockCheck.query.get_or_404(check_id)
    if check.status != "draft":
        return {"message": "仅草稿状态的盘点单可以删除"}, 400
    db.session.delete(check)
    db.session.commit()
    return {"message": "删除成功"}
