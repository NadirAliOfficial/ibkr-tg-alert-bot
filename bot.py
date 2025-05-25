#!/usr/bin/env python3
import os
import hmac
import hashlib
import json
from flask import Flask, request, abort
from ib_insync import IB, Stock, LimitOrder
from telegram import Bot
from pydantic import BaseSettings

# ---------- Configuration ----------
class Settings(BaseSettings):
    IB_HOST: str = "127.0.0.1"
    IB_PORT: int = 7497
    IB_CLIENT_ID: int = 2

    TELEGRAM_TOKEN: str        # from BotFather
    TELEGRAM_CHAT_ID: str      # your chat ID
    WEBHOOK_SECRET: str        # initial TradingView HMAC secret

    class Config:
        env_file = ".env"

settings = Settings()
# allow dynamic secret
webhook_secret = settings.WEBHOOK_SECRET

# ---------- App Setup ----------
app = Flask(__name__)
ib = IB()
ib.connect(settings.IB_HOST, settings.IB_PORT, clientId=settings.IB_CLIENT_ID)
tg = Bot(token=settings.TELEGRAM_TOKEN)

# In-memory state
presets = {}      # ticker -> {order_size, min_profit_pct}
user_states = {}  # chat_id -> {step, ticker, order_size}

# ---------- Helper ----------
def notify(chat_id: int, text: str):
    tg.send_message(chat_id=chat_id, text=text)

# ---------- Telegram Handler ----------
@app.route("/telegram", methods=["POST"])
def telegram_config():
    global webhook_secret
    data = request.get_json(force=True)
    msg = data.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = msg["chat"]["id"]
    if str(chat_id) != settings.TELEGRAM_CHAT_ID:
        return "", 403

    # direct set secret
    if text.lower().startswith("/setsecret "):
        secret = text.split(maxsplit=1)[1]
        webhook_secret = secret
        notify(chat_id, f"✅ Webhook secret updated.")
        return "", 200

    if text.lower() == "/getsecret":
        notify(chat_id, f"Current webhook secret: {webhook_secret}")
        return "", 200

    # /set TICKER SIZE PROFIT
    if text.lower().startswith("/set "):
        parts = text.split()
        if len(parts) == 4:
            _, ticker, size, profit = parts
            try:
                size = float(size)
                profit = float(profit)
            except ValueError:
                notify(chat_id, "Usage: /set TICKER SIZE PROFIT")
                return "", 200
            presets[ticker.upper()] = {"order_size": size, "min_profit_pct": profit/100.0}
            notify(chat_id, f"✅ Preset saved: {ticker.upper()} @ {size}$ @{profit}%")
            return "", 200

    # interactive /set
    state = user_states.get(chat_id)
    if text.lower() == "/set" and not state:
        user_states[chat_id] = {"step": "ticker"}
        notify(chat_id, "Enter ticker:")
        return "", 200
    if state:
        step = state["step"]
        if step == "ticker":
            state["ticker"] = text.upper(); state["step"] = "size"
            notify(chat_id, "Enter size:")
        elif step == "size":
            try:
                state["order_size"] = float(text)
            except:
                notify(chat_id, "Number only."); return "", 200
            state["step"] = "profit"
            notify(chat_id, "Enter profit %:")
        else:
            try:
                profit = float(text)
            except:
                notify(chat_id, "Number only."); return "", 200
            presets[state["ticker"]] = {"order_size": state["order_size"], "min_profit_pct": profit/100.0}
            notify(chat_id, f"✅ Saved {state['ticker']} @${state['order_size']} @{profit}%")
            user_states.pop(chat_id)
        return "", 200

    # show
    if text.lower() == "/show":
        if not presets:
            notify(chat_id, "No presets.")
        else:
            lines = [f"{t}: ${v['order_size']} @{v['min_profit_pct']*100}%" for t,v in presets.items()]
            notify(chat_id, "\n".join(lines))
        return "", 200

    # help
    notify(chat_id,
           "/set TICKER SIZE PROFIT\n/set → interactive\n/show\n"
           "/setsecret SECRET\n/getsecret")
    return "", 200

# ---------- TradingView Webhook Handler ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig = request.headers.get("X-Signature", "")
    expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected): abort(403)

    data = json.loads(payload)
    ticker = data.get("ticker",""").upper()
    signal = data.get("signal",""").upper()
    cfg = presets.get(ticker)
    if not cfg:
        notify(int(settings.TELEGRAM_CHAT_ID), f"No preset for {ticker}.")
        return "", 200

    contract = Stock(ticker, "SMART","USD")
    ib.qualifyContracts(contract)
    price = float(ib.reqMktData(contract, "", False, False).last)

    if signal == "BUY":
        cash = float(next(a.value for a in ib.accountValues() if a.tag=="AvailableFunds"))
        qty = cfg["order_size"]/price
        if cash>=cfg["order_size"]:
            ib.placeOrder(contract, LimitOrder("BUY",qty,price))
            notify(int(settings.TELEGRAM_CHAT_ID), f"BUY {ticker}:{qty:.2f}@{price}")
        else: notify(int(settings.TELEGRAM_CHAT_ID), "Insufficient funds.")
    else:
        pos = ib.position(contract)
        pnl = float(ib.pnl(contract).unrealizedPNL)
        if pos and pos.position>0 and pnl/(pos.avgCost*pos.position)>=cfg["min_profit_pct"]:
            ib.placeOrder(contract, LimitOrder("SELL",pos.position,price))
            notify(int(settings.TELEGRAM_CHAT_ID), f"SELL {ticker}:P/L{pnl:.2f}")
        else: notify(int(settings.TELEGRAM_CHAT_ID), f"Skip SELL {ticker}. P/L{pnl:.2f}")

    return "", 200

# ---------- Main ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",8000)))
