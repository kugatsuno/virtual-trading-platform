import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get Cash amount of current user
    currentUserID = session["user_id"]

    # Query database for how much cash the user has
    rows = db.execute("SELECT * FROM users WHERE id = :userID",
                      userID=currentUserID)

    # Ensure data returned from db exists
    if len(rows) != 1:
        return apology("database error", 403)

    # Store how much cash user currently have in variable
    cash = usd(rows[0]["cash"])

    # Get overall value of portfolio
    portfolioValue = 0
    portfolioValue = portfolioValue + rows[0]['cash']

    # Get all stocks owned from db for current user
    stocksOwned = db.execute("SELECT * FROM stock WHERE id = :userID", userID=currentUserID)

    # Get number of items in list
    length = len(stocksOwned)

    # Iterate over every item in list of stocks owned
    for i in range(length):
        stockInfo = lookup(stocksOwned[i]["symbol"])
        stocksOwned[i]["price"] = usd(stockInfo['price'])
        stocksOwned[i]["total"] = usd(float(stocksOwned[i]["qty"]) * stockInfo['price'])
        portfolioValue = portfolioValue + float(stocksOwned[i]["qty"]) * stockInfo['price']

    totalValue = usd(portfolioValue)

    return render_template("portfolio.html", cash=cash, stocksOwned=stocksOwned, portfolioValue=totalValue)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # Get current datetime
        now = datetime.now()

        # Ensure symbol is submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure quantity to buy is submitted
        if not request.form.get("shares"):
            return apology("must specify how much to buy", 403)

        symbol = request.form.get("symbol")
        qtyToPurchase = request.form.get("shares")

        # Ensure symbol is valid
        if not lookup(symbol):
            return apology("must provide valid symbol", 403)

        # Save dict returned from lookup
        stockInfo = lookup(symbol)

        # Save info from dict
        name = stockInfo['name']
        price = stockInfo['price']
        stock = stockInfo['symbol']

        # Store username of current session
        currentUserID = session["user_id"]

        # Amount needed to purchase
        payable = float(qtyToPurchase) * price

        # Query database for how much cash the user has
        rows = db.execute("SELECT * FROM users WHERE id = :userID",
                          userID=currentUserID)

        # Ensure data returned from db exists
        if len(rows) != 1:
            return apology("database error", 403)

        # Store how much cash user currently have in variable
        currentCash = rows[0]["cash"]

        # Check if enough cash to make the purchase
        if payable > currentCash:
            return apology("you do not have enough cash", 403)

        # Check if user already have existing same stock purchased
        stockdb = db.execute("SELECT * FROM stock WHERE symbol = :symbol AND id = :userID",
                            symbol=symbol, userID=currentUserID)

        if len(stockdb) != 1:
            db.execute("INSERT INTO stock (id, symbol, name, qty) VALUES(?, ?, ?, ?)", currentUserID, symbol, name, qtyToPurchase)
        else:
            ownedQty = stockdb[0]["qty"]
            totalQty = ownedQty + int(qtyToPurchase)
            db.execute("UPDATE stock SET qty = :totalQty WHERE symbol = :symbol AND id = :userID", totalQty=totalQty, symbol=symbol, userID=currentUserID)

        # Update cash of user
        endingCash = currentCash - payable
        db.execute("UPDATE users SET cash = :cash WHERE id = :userid", cash=endingCash, userid=currentUserID)

        priceUSD = usd(price)

        db.execute("INSERT INTO history (id, symbol, name, qty, price, time) VALUES(?, ?, ?, ?, ?, ?)", currentUserID, symbol, name, qtyToPurchase, priceUSD, now)

        buy = "Bought!"
        return redirect("/")


    # User reached route via GET
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    currentUserID = session["user_id"]
    histories = db.execute("SELECT * FROM history WHERE id = :userID ORDER BY time DESC", userID=currentUserID)

    return render_template("history.html", histories=histories)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
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

        # Check if symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 403)

        # Save symbol into variable
        symbol = request.form.get("symbol")

        # Check if symbol is valid
        if not lookup(symbol):
            return apology("must provide valid symbol", 403)

        # Save dict returned from lookup
        stockInfo = lookup(symbol)

        # Save info from dict
        name = stockInfo['name']
        price = stockInfo['price']
        stock = stockInfo['symbol']

        return render_template("quoted.html", name=name, stock=stock, price=price)

    # Display quote input page
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password and confirm password are the same
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password confirmation don't match", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Check if username already exists
        if len(rows) == 1:
            return apology("Username already exists, please select another", 403)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"), generate_password_hash(request.form.get("confirmation")))

        return redirect("/")

    # Default register page
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    now = datetime.now()

    # Get current user ID
    currentUserID = session["user_id"]

    # Get lists of stock symbols that user owns
    stocks = db.execute("SELECT * FROM stock WHERE id = :userID", userID=currentUserID)

    # Get user info
    user = db.execute("SELECT * FROM users WHERE id = :userID", userID=currentUserID)

    if request.method == "POST":
        # Ensure symbol is submitted
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 403)

        if request.form.get("symbol") == "Symbol":
            return apology("must provide stock symbol", 403)

        # Ensure quantity is submitted
        if not request.form.get("shares"):
            return apology("must provide number of shares to be sold", 403)

        # Check that quantity sold is not more than what is owned
        checkQty = db.execute("SELECT * FROM stock WHERE symbol = :symbol", symbol=request.form.get("symbol"))
        qty = int(checkQty[0]['qty'])
        if int(request.form.get("shares")) > qty:
            return apology("you do not have that many to sell", 403)

        # Update remaining amount of shares after selling
        newQty = int(checkQty[0]['qty']) - int(request.form.get("shares"))

        # If remaining quantity is zero, remove entry from finance.db, if not, update
        if newQty == 0:
            db.execute("DELETE FROM stock WHERE symbol = :symbol", symbol=request.form.get("symbol"))
        else:
            db.execute("UPDATE stock SET qty = :newQty WHERE symbol = :symbol", newQty=newQty, symbol=request.form.get("symbol"))

        # Get cash from shares sold, add to user's total cash
        stockInfo = lookup(request.form.get("symbol"))
        name = stockInfo['name']
        price = stockInfo['price']
        symbol = stockInfo['symbol']
        qtyToSell = int(request.form.get("shares")) * -1
        earnings = price * float(request.form.get("shares"))
        endingCash = earnings + user[0]['cash']
        db.execute("UPDATE users SET cash = :endingCash WHERE id = :userID", endingCash=endingCash, userID=currentUserID)

        priceUSD = usd(price)
        db.execute("INSERT INTO history (id, symbol, name, qty, price, time) VALUES(?, ?, ?, ?, ?, ?)", currentUserID, symbol, name, qtyToSell, price, now)

        return redirect("/")

    else:
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
