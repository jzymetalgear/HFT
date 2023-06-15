import websocket
import json
import config
import requests
import time
import alpaca_trade_api as tradeapi
import numpy as np

# Define the WebSocket URL
url = 'wss://stream.data.alpaca.markets/v2/iex'

# Define the authentication payload
auth_payload = {
    'action': 'auth',
    'key': config.APCA_API_KEY_ID,
    'secret': config.APCA_API_SECRET_KEY
}

# Define the subscription payload for multiple stocks
subscription_payload = {
    'action': 'subscribe',
    'trades': ['AAPL', 'MSFT', 'GOOG']
}

# Define EMA parameters
ema_period = 9
prev_close_prices = {}

# Alpaca API configuration
api = tradeapi.REST(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, base_url=config.APCA_API_BASE_URL)

def calculate_ema(symbol, close_price):
    if symbol not in prev_close_prices:
        prev_close_prices[symbol] = [close_price]
    else:
        if len(prev_close_prices[symbol]) < ema_period:
            prev_close_prices[symbol].append(close_price)
        else:
            prev_close_prices[symbol] = prev_close_prices[symbol][1:]
            prev_close_prices[symbol].append(close_price)
    prices = np.array(prev_close_prices[symbol])
    weights = np.exp(np.linspace(-1., 0., ema_period))
    weights /= weights.sum()
    ema = np.dot(weights, prices)
    return ema

def send_telegram_message(message):
    # ...
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send Telegram message: {response.text}")
    time.sleep(1)  # Add a 1-second delay before sending the next message
    
# Define the WebSocket connection callback functions
def on_open(ws):
    # Send the authentication payload
    ws.send(json.dumps(auth_payload))
    # Send the subscription payload
    ws.send(json.dumps(subscription_payload))
    # Send a Telegram bot message for successful connection
    send_telegram_message("Connecting successfully. Streaming real-time data live.")

def on_message(ws, message):
    # Parse and process the received message
    data = json.loads(message)
    # Extract the trade data for the subscribed stocks
    if data[0]['T'] == 't' and data[0]['S'] in subscription_payload['trades']:
        trade = data[0]
        symbol = trade['S']
        close_price = float(trade['p'])
        ema = calculate_ema(symbol, close_price)
        if ema is not None:
            price = f"${close_price:.2f}"
            size = trade['s']
            timestamp = trade['t']
            # Print the trade information
            print(f"Symbol: {symbol}, Price: {price}, Size: {size}, Timestamp: {timestamp}, EMA: {ema:.2f}")
            if close_price > ema:
                # Place a buy order
                place_buy_order(symbol)
            elif close_price < ema:
                # Place a sell order
                place_sell_order(symbol)

def on_error(ws, error):
    print(f"WebSocket Error: {error}")
    # Send a Telegram bot message for connection failure
    send_telegram_message("Failed to connect to the WebSocket.")

def on_close(ws):
    print("WebSocket connection closed")
    # Send a Telegram bot message for connection closure
    send_telegram_message("WebSocket connection closed.")

# Function to place a buy order
def place_buy_order(symbol):
    try:
        api.submit_order(
            symbol=symbol,
            qty=1,  # Modify the quantity as per your requirement
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        print(f"Placed a buy order for {symbol}")
    except tradeapi.rest.APIError as e:
        print(f"Failed to place buy order for {symbol}: {e}")

# Function to place a sell order
def place_sell_order(symbol):
    try:
        api.submit_order(
            symbol=symbol,
            qty=1,  # Modify the quantity as per your requirement
            side='sell',
            type='market',
            time_in_force='gtc'
        )
        print(f"Placed a sell order for {symbol}")
    except tradeapi.rest.APIError as e:
        print(f"Failed to place sell order for {symbol}: {e}")

# Function to send a message via Telegram bot
def send_telegram_message(message):
    bot_token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send Telegram message: {response.text}")

# Start the WebSocket connection
ws = websocket.WebSocketApp(url,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

# Run the WebSocket connection
ws.run_forever()
