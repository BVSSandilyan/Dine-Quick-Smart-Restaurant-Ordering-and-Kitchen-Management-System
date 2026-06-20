import sqlite3
import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dine_quick_secret_2024"

# Use absolute path resolving to protect against Flask reloader path shifting
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "dine_quick.db")

# ─── Database Setup ────────────────────────────────────────────────────────────

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # FORCE WIPE: Drop existing mismatched tables to force a clean layout rebuild
    cur.execute("DROP TABLE IF EXISTS order_items")
    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("DROP TABLE IF EXISTS menu_items")
    cur.execute("DROP TABLE IF EXISTS categories")
    cur.execute("DROP TABLE IF EXISTS tables")
    cur.execute("DROP TABLE IF EXISTS settings")

    cur.executescript("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            available INTEGER DEFAULT 1,
            prep_time INTEGER DEFAULT 15,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE tables (
            number INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            seats INTEGER DEFAULT 4,
            status TEXT DEFAULT 'Vacant'
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER NOT NULL,
            status TEXT DEFAULT 'Placed',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (table_number) REFERENCES tables(number)
        );

        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (item_id) REFERENCES menu_items(id)
        );
    """)

    # 1. Default Settings Seeding
    defaults = {"restaurant_name": "DineQuick Café", "tax_rate": "5", "currency_symbol": "₹"}
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)", (k, v))

    # 2. Re-populate categories
    cats = [("Starters", "🥗", 1), ("Mains", "🍛", 2), ("Drinks", "🥤", 3), ("Desserts", "🍮", 4)]
    for name, icon, order in cats:
        cur.execute("INSERT INTO categories(name, icon, sort_order) VALUES (?,?,?)", (name, icon, order))

    # 3. Clean Fresh Menu Items mapped to category IDs
    items = [
        (1, "Paneer Tikka", "Spicy grilled cottage cheese cubes with peppers.", 240, 12),
        (1, "Spring Rolls", "Crispy wrappers packed with seasoned julienned veggies.", 180, 10),
        (2, "Butter Chicken", "Classic creamy tomato curry with tender chicken pieces.", 340, 20),
        (2, "Dal Makhani", "Slow-cooked black lentils enriched with butter and cream.", 220, 25),
        (3, "Masala Chai", "Freshly brewed milk tea infused with aromatic spices.", 40, 5),
        (3, "Fresh Lime Soda", "Refreshing fizzy citrus drink served sweet or salted.", 80, 4),
        (4, "Gulab Jamun", "Warm, sweet milk-solid balls soaked in cardamom syrup.", 90, 5)
    ]
    for cat_id, name, desc, price, prep in items:
        cur.execute("""INSERT INTO menu_items(category_id, name, description, price, prep_time) 
                       VALUES (?,?,?,?,?)""", (cat_id, name, desc, float(price), prep))

    # 4. Tables seeding
    # 4. Tables seeding (Updated range to 13 to support tables up to 12)
    for i in range(1, 13):
        cur.execute("INSERT INTO tables(number, name, seats) VALUES (?,?,?)", 
                    (i, f"Table {i}", 2 if i < 5 else 4))

    conn.commit()
    conn.close()


# ─── Standard Routes ─────────────────────────────────────────────────────────

@app.route("/")
def home():
    conn = get_db()
    tables = conn.execute("SELECT * FROM tables ORDER BY number ASC").fetchall()
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings").fetchall()}
    conn.close()
    return render_template("index.html", tables=tables, settings=settings)

@app.route("/table/<int:table_num>")
def table_menu(table_num):
    conn = get_db()
    table = conn.execute("SELECT * FROM tables WHERE number = ?", (table_num,)).fetchone()
    if not table:
        conn.close()
        return "Table entry not found.", 404

    categories = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    items = conn.execute("SELECT * FROM menu_items").fetchall()
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings").fetchall()}
    conn.close()
    return render_template("menu.html", table=table, categories=categories, items=items, settings=settings)


# ─── Live Endpoint APIs ──────────────────────────────────────────────────────

@app.route("/api/orders", methods=["POST"])
def place_order():
    data = request.json
    table_num = data.get("table_number")
    notes = data.get("notes", "")
    cart = data.get("cart", [])

    if not cart:
        return jsonify({"success": False, "error": "Your cart selection is empty."})

    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO orders(table_number, status, notes, created_at, updated_at) VALUES (?,?,?,?,?)",
                    (table_num, "Placed", notes, now_str, now_str))
        order_id = cur.lastrowid

        for cart_item in cart:
            item_id = cart_item["id"]
            qty = cart_item["quantity"]
            menu_item = conn.execute("SELECT price FROM menu_items WHERE id = ?", (item_id,)).fetchone()
            if menu_item:
                cur.execute("INSERT INTO order_items(order_id, item_id, quantity, unit_price) VALUES (?,?,?,?)",
                            (order_id, item_id, qty, menu_item["price"]))
        
        cur.execute("UPDATE tables SET status='Occupied' WHERE number=?", (table_num,))
        conn.commit()
        return jsonify({"success": True, "order_id": order_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()

@app.route("/table/<int:table_num>/order-status")
def table_order_status(table_num):
    conn = get_db()
    orders = conn.execute("""SELECT * FROM orders 
                             WHERE table_number = ? AND status != 'Served' 
                             ORDER BY id DESC""", (table_num,)).fetchall()
    res = []
    for o in orders:
        items = conn.execute("""SELECT oi.quantity, mi.name 
                                FROM order_items oi JOIN menu_items mi ON oi.item_id = mi.id 
                                WHERE oi.order_id = ?""", (o["id"],)).fetchall()
        
        totals = conn.execute("SELECT SUM(quantity * unit_price) as total FROM order_items WHERE order_id=?", (o["id"],)).fetchone()
        sub = totals["total"] or 0
        tax_rate = float(conn.execute("SELECT value FROM settings WHERE key='tax_rate'").fetchone()["value"])
        grand = round(sub + (sub * tax_rate / 100), 0)

        res.append({
            "id": o["id"],
            "status": o["status"],
            "created_at": o["created_at"],
            "total": int(grand),
            "items": [{"quantity": i["quantity"], "name": i["name"]} for i in items]
        })
    conn.close()
    return jsonify(res)


# ─── Kitchen Monitor APIs ────────────────────────────────────────────────────

@app.route("/kitchen")
def kitchen_monitor():
    conn = get_db()
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings").fetchall()}
    conn.close()
    return render_template("kitchen.html", settings=settings)

@app.route("/api/orders/live")
def live_orders():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE status IN ('Placed', 'Cooking') ORDER BY id ASC").fetchall()
    res = []
    for o in orders:
        items = conn.execute("""SELECT oi.quantity, mi.name 
                                FROM order_items oi JOIN menu_items mi ON oi.item_id = mi.id 
                                WHERE oi.order_id = ?""", (o["id"],)).fetchall()
        res.append({
            "id": o["id"],
            "table_number": o["table_number"],
            "status": o["status"],
            "notes": o["notes"],
            "created_at": o["created_at"],
            "updated_at": o["updated_at"],
            "items": [{"quantity": i["quantity"], "name": i["name"]} for i in items]
        })
    conn.close()
    return jsonify(res)

@app.route("/api/orders/all")
def all_orders_log():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    res = []
    for o in orders:
        items = conn.execute("""SELECT oi.quantity, mi.name 
                                FROM order_items oi JOIN menu_items mi ON oi.item_id = mi.id 
                                WHERE oi.order_id = ?""", (o["id"],)).fetchall()
        res.append({
            "id": o["id"],
            "table_number": o["table_number"],
            "status": o["status"],
            "updated_at": o["updated_at"],
            "items": [{"quantity": i["quantity"], "name": i["name"]} for i in items]
        })
    conn.close()
    return jsonify(res)

@app.route("/api/orders/<int:order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    new_status = request.json.get("status")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (new_status, now_str, order_id))
    
    if new_status == "Served":
        order = conn.execute("SELECT table_number FROM orders WHERE id=?", (order_id,)).fetchone()
        if order:
            t_num = order["table_number"]
            still_active = conn.execute("SELECT COUNT(*) as c FROM orders WHERE table_number=? AND status IN ('Placed','Cooking')", (t_num,)).fetchone()["c"]
            if still_active == 0:
                conn.execute("UPDATE tables SET status='Vacant' WHERE number=?", (t_num,))
                
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ─── System Administrator Panel ───────────────────────────────────────────────

@app.route("/admin")
def admin_dashboard():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    items = conn.execute("""SELECT mi.*, c.name as category_name 
                            FROM menu_items mi JOIN categories c ON mi.category_id=c.id""").fetchall()
    tables = conn.execute("SELECT * FROM tables ORDER BY number ASC").fetchall()
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings").fetchall()}
    conn.close()
    return render_template("admin.html", categories=categories, items=items, tables=tables, settings=settings)

@app.route("/api/admin/items", methods=["POST"])
def admin_add_item():
    d = request.json
    conn = get_db()
    conn.execute("""INSERT INTO menu_items(category_id, name, description, price, prep_time) 
                    VALUES (?,?,?,?,?)""", (int(d["category_id"]), d["name"], d["description"], float(d["price"]), int(d["prep_time"])))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/items/<int:item_id>", methods=["PATCH", "DELETE"])
def admin_mutate_item(item_id):
    conn = get_db()
    if request.method == "DELETE":
        conn.execute("DELETE FROM menu_items WHERE id=?", (item_id,))
    else:
        d = request.json
        field = list(d.keys())[0]
        val = list(d.values())[0]
        conn.execute(f"UPDATE menu_items SET {field}=? WHERE id=?", (val, item_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/settings", methods=["PATCH"])
def admin_update_settings():
    d = request.json
    conn = get_db()
    for k, v in d.items():
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/admin/stats")
def admin_stats():
    conn = get_db()
    total_orders = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    active_orders = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status IN ('Placed','Cooking')").fetchone()["c"]
    served_today = conn.execute("""SELECT COUNT(*) as c FROM orders 
                                   WHERE status='Served' AND date(created_at)=date('now')""").fetchone()["c"]
    revenue_today = conn.execute("""SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) as r
                                    FROM order_items oi JOIN orders o ON oi.order_id=o.id
                                    WHERE o.status='Served' AND date(o.created_at)=date('now')""").fetchone()["r"]
    conn.close()
    return jsonify({
        "total_orders": total_orders,
        "active_orders": active_orders,
        "served_today": served_today,
        "revenue_today": round(revenue_today, 2)
    })

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)