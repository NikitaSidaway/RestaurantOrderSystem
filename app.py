from flask import Flask, render_template
import sqlite3

app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("RestaurantDatabse.db")
    return db

@app.teardown_appcontext
def close_connection(exception):
    # session["user"] = None
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, inserting=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    if inserting:
        get_db().commit()
        return cur.lastrowid
    else:
        return (rv[0] if rv else None) if one else rv



@app.route("/")
def cashier_screen():
    return render_template("cashier_screen.html")

@app.post("/")
def

if __name__ == '__main__':
    app.run(debug=True)