from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def cashier_screen():
    return render_template("cashier_screen.html")

if __name__ == '__main__':
    app.run(debug=True)