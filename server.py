from flask import Flask, request, jsonify
from flask_cors import CORS
import MetaTrader5 as mt5

app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
# CORS(app)
# Global variable to track the login status
is_logged_in = False


# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize():
        print("Initialize() failed, error code =", mt5.last_error())
        return False
    return True


def mt5_login(login, password, server):
    global is_logged_in
    if not initialize_mt5():
        return False

    authorized = mt5.login(login, password=password, server=server)
    if not authorized:
        print(f"Failed to connect to account #{login}, error code: {mt5.last_error()}")
        mt5.shutdown()
        return False
    is_logged_in = True
    return True


@app.before_request
def before_request():
    if request.method == "OPTIONS":
        return "", 204


@app.route("/login", methods=["POST"])
def login_endpoint():
    data = request.json
    login = data.get("login")
    password = data.get("password")
    server = data.get("server")

    if not login or not password or not server:
        return jsonify({"error": "Missing login, password, or server information"}), 400

    if mt5_login(login, password, server):
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"error": "Login failed"}), 401


@app.route("/open_trade", methods=["POST"])
def open_trade():
    global is_logged_in
    if not is_logged_in:
        return jsonify({"error": "Not logged in"}), 401

    try:
        data = request.json
        if not data:
            print("Request data is empty or not JSON")
            return jsonify({"error": "Invalid request"}), 400

        symbol = data.get("symbol")
        volume = data.get("volume")
        take_profit = data.get("take_profit")
        stop_loss = data.get("stop_loss")
        trade_type = data.get("type")

        if not all([symbol, volume, take_profit, stop_loss, trade_type]):
            print("Missing trade parameters")
            return jsonify({"error": "Missing trade parameters"}), 400

        try:
            volume = float(volume)
            take_profit = float(take_profit)
            stop_loss = float(stop_loss)
        except ValueError:
            print("Invalid volume, take_profit, or stop_loss format")
            return (
                jsonify({"error": "Invalid volume, take_profit, or stop_loss format"}),
                400,
            )

        order_type = mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            return jsonify({"error": f"Symbol {symbol} not found"}), 400

        price = symbol_info.ask if order_type == mt5.ORDER_TYPE_BUY else symbol_info.bid

        # Calculate SL and TP based on price and order type
        if order_type == mt5.ORDER_TYPE_BUY:
            sl = price - stop_loss * mt5.symbol_info(symbol).point
            tp = price + take_profit * mt5.symbol_info(symbol).point
        else:
            sl = price + stop_loss * mt5.symbol_info(symbol).point
            tp = price - take_profit * mt5.symbol_info(symbol).point

        # Check if SL and TP are valid
        if (
            sl <= 0
            or tp <= 0
            or (order_type == mt5.ORDER_TYPE_BUY and sl >= price)
            or (order_type == mt5.ORDER_TYPE_SELL and tp >= price)
        ):
            print("Invalid SL or TP values")
            return jsonify({"error": "Invalid SL or TP values"}), 400

        request_params = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 0,
            "comment": "Trade via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        print("Sending order with parameters:", request_params)
        result = mt5.order_send(request_params)
        if result is None:
            return jsonify({"error": "Order send failed, no result returned"}), 500

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(
                f"Trade failed: {result}, Error Code: {result.retcode}, Comment: {result.comment}"
            )
            return jsonify({"error": "Trade failed", "details": str(result)}), 400

        return jsonify({"order_id": result.order})
    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/get_open_trades", methods=["GET"])
def get_open_trades():
    if not is_logged_in:
        return jsonify({"error": "Not logged in"}), 401

    try:
        trades = mt5.positions_get()
        if trades is None:
            return (
                jsonify(
                    {"error": "Failed to retrieve trades", "details": mt5.last_error()}
                ),
                500,
            )

        if len(trades) == 0:
            return jsonify({"message": "No open trades found"})

        trades_list = []
        for trade in trades:
            # Use the correct constants for order types
            trade_type = (
                "BUY" if trade.type == 0 else "SELL"
            )  # Replace 0 and 1 with actual constants

            trades_list.append(
                {
                    "order_id": trade.ticket,
                    "symbol": trade.symbol,
                    "volume": trade.volume,
                    "price": trade.price_open,
                    "type": trade_type,
                }
            )

        return jsonify(trades_list)

    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/close_all_trades", methods=["POST"])
def close_all_trades():
    global is_logged_in
    if not is_logged_in:
        return jsonify({"error": "Not logged in"}), 401

    try:
        # Fetch open positions
        positions = mt5.positions_get()
        if positions is None:
            return (
                jsonify(
                    {
                        "error": "Failed to retrieve positions",
                        "details": mt5.last_error(),
                    }
                ),
                500,
            )

        if len(positions) == 0:
            return jsonify({"message": "No open trades to close"}), 200

        results = []
        for position in positions:
            # Determine the correct order type and price for closing
            if position.type == mt5.ORDER_TYPE_BUY:
                close_order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            elif position.type == mt5.ORDER_TYPE_SELL:
                close_order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            else:
                results.append(
                    {
                        "ticket": position.ticket,
                        "status": "failed",
                        "error": "Unknown position type",
                    }
                )
                continue

            # Prepare request parameters to close the position
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": position.ticket,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_order_type,
                "price": price,
                "deviation": 10,
                "magic": position.magic,
                "comment": "Close trade via API",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Log request parameters for debugging
            print(f"Close request parameters: {close_request}")

            # Send the close request
            result = mt5.order_send(close_request)
            if result is None:
                results.append(
                    {
                        "ticket": position.ticket,
                        "status": "failed",
                        "error": "Order send failed, no result returned",
                    }
                )
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                results.append(
                    {
                        "ticket": position.ticket,
                        "status": "failed",
                        "error": f"Error Code: {result.retcode}, Comment: {result.comment}",
                    }
                )
            else:
                results.append({"ticket": position.ticket, "status": "success"})

        return jsonify({"results": results})

    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/logout", methods=["POST"])
def logout():
    global is_logged_in
    if is_logged_in:
        mt5.shutdown()
        is_logged_in = False
        return jsonify({"message": "Logged out successfully"})
    else:
        return jsonify({"error": "No active session"}), 400


if __name__ == "__main__":
    app.run(debug=True)
