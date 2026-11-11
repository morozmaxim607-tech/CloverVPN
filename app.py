import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{API}/sendMessage", json=data, timeout=15)

@app.route("/", methods=["GET"])
def home():
    return "CLOVER VPN is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json

    if not update:
        return "OK"

    message = update.get("message")
    if not message:
        return "OK"

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
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
            "☘️ Добро пожаловать в CLOVER VPN!\n"
            "Свобода без границ.",
            keyboard
        )

    elif text == "🛒 Купить VPN":
        send_message(chat_id, "Раздел покупки скоро появится.")

    elif text == "🌍 Выбор страны":
        send_message(
            chat_id,
            "🇲🇩 Молдова\n🇷🇴 Румыния\n🇩🇪 Германия\n"
            "🇳🇱 Нидерланды\n🇫🇷 Франция\n🇺🇸 США\n\n"
            "Серверы пока настраиваются."
        )

    elif text == "👤 Мой профиль":
        send_message(chat_id, "Твоя подписка пока не оформлена.")

    elif text == "💬 Поддержка":
        send_message(chat_id, "Напиши администратору CLOVER VPN.")

    else:
        send_message(chat_id, "Выбери действие в меню ☘️")

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
