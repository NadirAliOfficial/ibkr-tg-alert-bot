# ibkr-tg-alert-bot

A Flask webhook bridge connecting TradingView alert signals to Interactive Brokers (IBKR) for automated trade execution, with real-time management and notifications via a Telegram bot.

## Features

- **TradingView Webhook Integration**: Authenticates incoming signals at `/webhook` using HMAC-SHA256 signatures (`X-Signature` header).
- **Automated IBKR Execution**: Places limit BUY orders based on preset dollar allocation and SELL orders upon meeting a configurable profit percentage threshold.
- **Telegram Bot Control**: Manage trading presets on the fly directly from Telegram (`/set`, `/show`, `/setsecret`, `/getsecret`).
- **Real-Time Alerts**: Receive instant Telegram messages on order placement, trade executions, profit/loss status, and insufficient funds.
- **Dynamic Secret Rotation**: Update your TradingView webhook HMAC secret via Telegram without restarting the server.

## Requirements

- Python 3.9+
- Interactive Brokers TWS or IB Gateway running with API connections enabled
- Telegram Bot token (from [@BotFather](https://t.me/BotFather)) and your Telegram Chat ID

## Installation

```bash
# Clone the repository
git clone https://github.com/NadirAliOfficial/ibkr-tg-alert-bot.git
cd ibkr-tg-alert-bot

# Install required dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# Interactive Brokers TWS / Gateway settings
IB_HOST=127.0.0.1
IB_PORT=7497            # 7497 for TWS paper, 7496 for live, 4002/4001 for IB Gateway
IB_CLIENT_ID=2

# Telegram Bot settings
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Security & Webhook
WEBHOOK_SECRET=your_hmac_webhook_secret
PORT=8000
```

## Usage

### 1. Start the Server

```bash
python bot.py
```

### 2. Telegram Commands

Send commands to your Telegram bot to configure trade presets:

| Command | Description |
| :--- | :--- |
| `/set TICKER SIZE PROFIT` | Save order size ($) and minimum profit % (e.g. `/set AAPL 500 2.5`) |
| `/set` | Step-by-step interactive setup prompt |
| `/show` | List all currently active ticker presets |
| `/setsecret <SECRET>` | Update the TradingView HMAC webhook secret dynamically |
| `/getsecret` | Display the active HMAC webhook secret |

### 3. TradingView Alert Webhook

Configure your TradingView alert to send a `POST` request to `https://your-domain.com/webhook` with the following JSON body:

```json
{
  "ticker": "AAPL",
  "signal": "BUY"
}
```

Include the HMAC-SHA256 signature in the request headers:
- `X-Signature`: `<hex_digest>`

## Project Structure

```
.
├── .gitignore         # Git ignore rules
├── bot.py             # Flask app, IBKR connection, and Telegram handlers
├── LICENSE            # MIT license
├── README.md          # Project documentation
└── requirements.txt   # Python package dependencies
```

## License

MIT License © 2026 Nadir Ali
