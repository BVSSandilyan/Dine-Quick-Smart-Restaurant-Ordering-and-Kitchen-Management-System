# 🍽️ Dine Quick — QR Table Ordering App

A contactless in-restaurant ordering platform. Customers scan a table-specific QR code (or link), browse the digital menu, place orders directly to the kitchen, and track progress in real time.

---

## Tech Stack
- **Backend:** Python 3 + Flask
- **Database:** SQLite3 (zero config, file-based)
- **Frontend:** Jinja2 templates, Vanilla JS (Fetch API), Bootstrap-free custom CSS
- **Fonts:** Google Fonts (Syne + DM Sans)

---

## Quick Start

```bash
# 1. Install dependency
pip install flask

# 2. Run the app (auto-creates & seeds DB on first run)
python app.py

# 3. Open in browser
#    Customer view  →  http://localhost:5000/
#    Kitchen KDS    →  http://localhost:5000/kitchen
#    Admin panel    →  http://localhost:5000/admin
```

---

## Project Structure

```
dine_quick/
├── app.py                  # Flask app — all routes + SQLite logic
├── dine_quick.db           # SQLite DB (auto-created)
├── requirements.txt
├── README.md
└── templates/
    ├── base.html           # Shared nav, CSS variables, toast system
    ├── index.html          # Table selection landing page
    ├── menu.html           # Customer menu + cart + order tracker
    ├── kitchen.html        # Kitchen Display System (KDS)
    └── admin.html          # Admin dashboard
```

---

## Features

### 👤 Customer Experience (`/table/<number>`)
- Browse full menu with **category tabs** (Starters, Mains, Drinks, Desserts)
- Per-item quantity controls with live cart updates
- **Live bill calculator** — subtotal, GST, total before placing
- Special request notes field
- Order placed via JSON API to the kitchen instantly
- **Live order tracker** — polls every 12s, shows Placed → Cooking → Served progress bar

### 🍳 Kitchen Display System (`/kitchen`)
- **Three-column Kanban board**: New Orders | Cooking | Recently Served
- Auto-refreshes every 8 seconds
- Urgent order highlighting (15+ min age)
- One-click: "Start Cooking" → "Mark Served"
- New order toast notifications

### ⚙️ Admin Dashboard (`/admin`)
- **Overview tab**: live stats (total orders, active, served today, today's revenue)
- **Menu Items tab**: add items, inline-edit price/prep time, toggle availability, delete
- **Orders Log tab**: filterable order history with totals
- **Settings tab**: restaurant name, tax/GST rate, currency symbol

---

## Order State Machine

```
Placed  ──→  Cooking  ──→  Served
  ↑ customer places     ↑ chef clicks        ↑ chef clicks
  order via cart        "Start Cooking"       "Mark Served"
```

States are stored in the `orders` table and drive UI display across customer and kitchen panels.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/menu` | All menu items with categories |
| POST | `/api/orders` | Place a new order |
| PATCH | `/api/orders/<id>/status` | Update order status |
| GET | `/api/orders/active` | Active orders (Placed + Cooking) |
| GET | `/api/orders/all` | Full order history |
| GET | `/table/<n>/order-status` | Status of orders for a table |
| GET | `/api/admin/stats` | Dashboard stats |
| POST | `/api/admin/items` | Add menu item |
| PATCH | `/api/admin/items/<id>` | Update menu item |
| DELETE | `/api/admin/items/<id>` | Delete menu item |
| PATCH | `/api/admin/settings` | Update restaurant settings |

---

## Seeded Data
- **12 tables** (2-seat, 4-seat, 6-seat mix)
- **20 menu items** across 4 categories
- Default GST: 5% | Currency: ₹

## Project video
URL -> [https://drive.google.com/file/d/1Ec8iEv6fps7LBsQ-BM8kR9m_FkUrq329/view?usp=drivesdk](https://drive.google.com/file/d/18sZ0qXpoF9IoGUrRsyAfddOa_-cpXIgp/view?usp=drive_link)

                        
