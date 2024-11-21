import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET","POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    portfolio = db.execute("SELECT symbol, shares FROM owners WHERE user_id = ?", session["user_id"])

    for stock in portfolio:
        quote = lookup(stock["symbol"])
        stock["current_price"] = quote["price"]
        stock["value"] = stock["current_price"] * stock["shares"]

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash_value = cash[0]["cash"]
    total_value = sum(stock["value"] for stock in portfolio)
    grand_total = cash_value + total_value
    user = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])

    return render_template("index.html", name=user[0]["username"], portfolio=portfolio, cash=cash_value, total_value=total_value, grand_total=grand_total, usd=usd)





@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stock = lookup(symbol)

        #If the shares is not valid number
        if not shares.isdigit() or int(shares) <= 0:
            return apology("the share is not valid", 400)

        shares = int(shares)

        #If the symbol is not valid
        if stock is None:
            return apology("the symbol is not valid", 400)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash_value = cash[0]['cash']
        cash_now = cash_value - shares * stock["price"]

        #Check whether the user has enough cash
        if cash_now < 0:
            return apology("not enough cash", 403)

        #If enough update the new cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_now, session["user_id"])

        #Add transaction to the table as 'bought'
        db.execute("INSERT INTO transactions(user_id, symbol, price, shares, trade, at) VALUES(?, ?, ?, ?, ?, ?)",
                    session["user_id"], symbol, stock["price"], shares, "bought", datetime.now())

        #Update the ownership of the stocks
        rows = db.execute("SELECT * FROM owners WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)

        if len(rows) == 0:
            db.execute("INSERT INTO owners (user_id, symbol, shares) VALUES(?, ?, ?)", session["user_id"], symbol, shares)
        else:
            shares_held = db.execute("SELECT shares FROM owners WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
            db.execute("UPDATE owners SET shares = ? WHERE user_id  = ? AND symbol = ?", shares_held[0]["shares"] + shares, session["user_id"], symbol)


        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT symbol, price, shares, trade, at FROM transactions WHERE user_id = ?", session["user_id"])

    return render_template("history.html", history=history, usd=usd)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        rows = lookup(request.form.get("symbol"))

        #If the symbol is not valid
        if rows is None:
            return apology("the symbol is not valid", 400)

        #If the symbol is valid
        print(rows)
        return render_template("quote.html", symbol=rows["symbol"], price=usd(rows["price"]))

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        #Ensure password is confirmed
        elif not request.form.get("confirmation"):
            return apology("must confirm the password", 400)

        #Ensure the password and the confirmed password are the same
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("confirm the same password", 400)

        #Ensure the username does not already exist
        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                       request.form.get("username"), generate_password_hash(request.form.get("password")))

            # Remember which user has logged in
            rows = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

        except Exception as e:
            print(e)
            return apology("the username already exists", 400)

    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        shares = int(request.form.get("shares"))
        symbol = request.form.get("symbol")

        #If the symbol is not valid
        if stock is None:
            return apology("the symbol is not valid", 400)

        #If the no. shares held are less than the posted
        shares_held = db.execute("SELECT shares FROM owners WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        if shares > shares_held[0]["shares"]:
            return apology("Not enough shares", 400)

        #If the shares held are enough
        db.execute("UPDATE owners SET shares = ? WHERE user_id = ? AND symbol = ?", shares_held[0]["shares"] - shares, session["user_id"], symbol)
        db.execute("INSERT INTO transactions (user_id, symbol, price, shares, trade, at) VALUES(?, ?, ?, ?, ?, ?)",
                   session["user_id"], symbol, stock["price"], shares, "sold", datetime.now())

        #update the user's cash
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash_value = cash[0]["cash"]
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_value + shares*stock["price"], session["user_id"])

        #redirect user to the homepage
        return redirect("/")

    else:
        symbols = db.execute("SELECT symbol FROM owners WHERE user_id = ?", session["user_id"])

        return render_template("sell.html", symbols=symbols )
