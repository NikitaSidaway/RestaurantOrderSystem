from flask import Flask, render_template, g, request, redirect
from flask_socketio import SocketIO, emit
import sqlite3

app = Flask(__name__)

socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE = 'RestaurantDatabase.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    cur = get_db().execute(query, args)
    if commit:
        get_db().commit()
        lastrowid = cur.lastrowid
        cur.close()
        return lastrowid
    else:
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv



def emit_sale_update():
    not_ready = query_db("SELECT id, number, status FROM Sales WHERE status IS NULL ORDER BY id")
    ready = query_db("SELECT id, number, status FROM Sales WHERE status = 1 ORDER BY id")

    socketio.emit('sale_update', {
        'not_ready_sales': [{'id': row['id'], 'number': row['number']} for row in not_ready],
        'ready_sales': [{'id': row['id'], 'number': row['number']} for row in ready]
    })

@app.route("/")
def cashier_screen():

    sales = query_db("SELECT id, number, status FROM Sales ORDER BY id")

    return render_template("cashier_screen.html", sales=sales)

@app.route("/cashier_screen")
def new_cashier_screen():

    items_query = """SELECT
        i.id AS item_id,
        i.name AS item_name,
        i.price AS price,
        i.category AS category,
        c.name AS category_name
    FROM
        items i
    JOIN
        categories c ON i.category = c.id;
    """

    categories_query = "SELECT id, name FROM Categories;"

    items = query_db(items_query)
    categories = query_db(categories_query)

    return render_template("new_cashier_screen.html", items=items, categories=categories)

@app.post("/submit_cart")
def sumbit_cart():
    cart = request.get_json()

    last = query_db("SELECT MAX(number) AS max_number FROM Sales;", one=True)
    current = last["max_number"] or 0
    next_number = current + 1
    if next_number > 100:
        next_number = 1

    sale_id = query_db(
        "INSERT INTO Sales (number) VALUES (?)",
        (next_number,),
        commit=True
    ) 

    for item_id, item in cart.items():
        qty = item.get("qty", 1)
        query_db(
        "INSERT INTO SaleItem (sale_id, item_id, status, quantity) VALUES (?, ?, ?, ?);",
        (sale_id, item_id, None, qty),
        commit=True
        )
    return {"status": "ok"}


@app.route("/customer_screen")
def customer_screen():

    not_ready = query_db("SELECT id, number, status FROM Sales WHERE status IS NULL ORDER BY id")
    ready = query_db("SELECT id, number, status FROM Sales WHERE status = 1 ORDER BY id")

    return render_template("customer_screen.html", not_ready_sales=not_ready, ready_sales=ready)


@app.route("/kitchen_screen")
def kitchen_screen():

    sqlquery = """SELECT 
        Sales.id AS sale_id,
        Sales.number AS sale_number,
        Sales.status AS sale_status,
        Items.id AS item_id,
        Items.name AS item_name,
        SaleItem.status AS item_status,
        SaleItem.quantity AS item_quantity
    FROM Sales
    JOIN SaleItem ON Sales.id = SaleItem.sale_id
    JOIN Items ON SaleItem.item_id = Items.id
    ORDER BY Sales.number, Items.name;"""
    results = query_db(sqlquery)

    grouped_sales = {}
    for row in results:
        sale_id = row["sale_id"]
        quantity = row["item_quantity"] or 1

        if sale_id not in grouped_sales:
            grouped_sales[sale_id] = {
                "sale_number": row["sale_number"],
                "status" : row["sale_status"],
                "items" : []
            }

        for _ in range(quantity):
            grouped_sales[sale_id]["items"].append({
                "item_id": row["item_id"],
                "name": row["item_name"],
                "status": row["item_status"]
            })

    return render_template("kitchen_screen.html", sales=grouped_sales)


@app.post("/item_status")
def item_status():
    data = request.get_json() or {}
    sale_id = data.get("sale_id")
    item_id = data.get("item_id")
    status = data.get("status")

    if sale_id is None or item_id is None or status is None:
        return {"status": "error", "message": "Missing sale_id, item_id, or status"}, 400

    status_value = 1 if int(status) == 1 else None
    query_db(
        "UPDATE SaleItem SET status = ? WHERE sale_id = ? AND item_id = ?;",
        (status_value, sale_id, item_id),
        commit=True
    )

    unready = query_db(
        "SELECT COUNT(*) AS count FROM SaleItem WHERE sale_id = ? AND status IS NULL;",
        (sale_id,), one=True
    )

    if unready["count"] == 0:
        query_db("UPDATE Sales SET status = 1 WHERE id = ?;", (sale_id,), commit=True)
        order_ready = True
    else:
        query_db("UPDATE Sales SET status = NULL WHERE id = ?;", (sale_id,), commit=True)
        order_ready = False

    emit_sale_update()
    return {"status": "ok", "order_ready": order_ready}


@app.post("/change_sale")
def change_sale():
    print("test")
    request_change = request.form.get("change")
    sale_id = request.form.get("sale_id")
    
    if request_change == "delete":

        sql_sale_change = ("DELETE FROM Sales WHERE id = (?);")
        query_db(sql_sale_change, (sale_id,))
        get_db().commit()

    elif request_change == "ready":
        
        sql_sale_change = ("UPDATE Sales SET status = 1 WHERE id = (?);")
        query_db(sql_sale_change, (sale_id,))
        get_db().commit()

    emit_sale_update()

    return redirect('/')


@app.post("/add_sale")
def sale_numpad():
    sale_number = request.form["sale_number"]

    sql_sale_number = ("INSERT INTO Sales (number) VALUES (?);")


    query_db(sql_sale_number, (sale_number,))

    get_db().commit()

    emit_sale_update()

    return redirect('/')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit_sale_update()
if __name__ == '__main__':
    socketio.run(app, debug=True)