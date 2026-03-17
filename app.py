from flask import Flask, render_template, g, request, redirect
import sqlite3

app = Flask(__name__)


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




@app.route("/")
def cashier_screen():

    orders = query_db("SELECT order_number, status FROM Orders ORDER BY id")

    return render_template("cashier_screen.html", orders=orders)

@app.post("/add_order")
def order_numpad():
    order_number = request.form["order_number"]

    sql_order_number = ("INSERT INTO Orders (order_number) VALUES (?);")


    query_db(sql_order_number, (order_number,))

    get_db().commit()
    return redirect('/') 

if __name__ == '__main__':
    app.run(debug=True)