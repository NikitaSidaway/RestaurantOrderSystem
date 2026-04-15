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



def emit_order_update():
    not_ready = query_db("SELECT id, order_number, status FROM Orders WHERE status IS NULL ORDER BY id")
    ready = query_db("SELECT id, order_number, status FROM Orders WHERE status = 1 ORDER BY id")

    socketio.emit('order_update', {
        'not_ready_orders': [{'id': row['id'], 'order_number': row['order_number']} for row in not_ready],
        'ready_orders': [{'id': row['id'], 'order_number': row['order_number']} for row in ready]
    })

@app.route("/")
def cashier_screen():

    orders = query_db("SELECT id, order_number, status FROM Orders ORDER BY id")

    return render_template("cashier_screen.html", orders=orders)


@app.route("/customer_screen")
def customer_screen():

    not_ready = query_db("SELECT id, order_number, status FROM Orders WHERE status IS NULL ORDER BY id")
    ready = query_db("SELECT id, order_number, status FROM Orders WHERE status = 1 ORDER BY id")

    return render_template("customer_screen.html", not_ready_orders=not_ready, ready_orders=ready)


@app.post("/change_order")
def change_order():
    print("test")
    request_change = request.form.get("change")
    order_id = request.form.get("order_id")
    
    if request_change == "delete":

        sql_order_change = ("DELETE FROM Orders WHERE id = (?);")
        query_db(sql_order_change, (order_id,))
        get_db().commit()

    elif request_change == "ready":
        
        sql_order_change = ("UPDATE Orders SET status = 1 WHERE id = (?);")
        query_db(sql_order_change, (order_id,))
        get_db().commit()

    emit_order_update()

    return redirect('/')


@app.post("/add_order")
def order_numpad():
    order_number = request.form["order_number"]

    sql_order_number = ("INSERT INTO Orders (order_number) VALUES (?);")


    query_db(sql_order_number, (order_number,))

    get_db().commit()

    emit_order_update()

    return redirect('/')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit_order_update()
if __name__ == '__main__':
    socketio.run(app, debug=True)