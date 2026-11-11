import os
import logging
import requests

from flask import Flask, request

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text, keyboard=None):

    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    try:
        response = requests.post(
            f"{API}/sendMessage",
            json=data,
            timeout=15
        )

        logger.info("Telegram response: %s", response.status_code)

        if not response.ok:
            logger.error("Telegram error: %s", response.text)

    except requests.RequestException as e:
        logger.error("Telegram connection error: %s", e)


@app.route("/", methods=["GET"])
def home():
    return "CLOVER VPN is running!"


@app.route("/webhook", methods=["POST"])
def webhook():

    update = request.get_json(silent=True)

    if not update:
        return "OK"

    message = update.get("message")

    if not message:
        return "OK"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start"):

        keyboard = {
            "keyboard": [
                [{"text": "🛒 Купить VPN"}],
                [{"text": "🌍 Выбор страны"}],
                [{"text": "👤 Мой профиль"}],
                [{"text": "💬 Поддержка"}]
            ],
            "resize_keyboard": True
        }

        send_message(
            chat_id,
            "☘️ Добро пожаловать в CLOVER VPN!\n\n"
            "Свобода без границ.",
            keyboard
        )

    elif text == "🛒 Купить VPN":

        send_message(
            chat_id,
            "🛒 Раздел покупки скоро появится."
        )

    elif text == "🌍 Выбор страны":

        send_message(
            chat_id,
            "🌍 Выбери страну:\n\n"
            "🇲🇩 Молдова\n"
            "🇷🇴 Румыния\n"
            "🇩🇪 Германия\n"
            "🇳🇱 Нидерланды\n"
            "🇫🇷 Франция\n"
            "🇺🇸 США\n\n"
            "Серверы пока настраиваются."
        )

    elif text == "👤 Мой профиль":

        send_message(
            chat_id,
            "👤 Твой профиль CLOVER VPN\n\n"
            "Подписка пока не оформлена."
        )

    elif text == "💬 Поддержка":

        send_message(
            chat_id,
            "💬 Поддержка CLOVER VPN\n\n"
            "Напиши администратору."
        )

    else:

        send_message(
            chat_id,
            "Выбери действие в меню ☘️"
        )

    return "OK"


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
