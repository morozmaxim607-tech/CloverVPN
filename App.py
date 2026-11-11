import os
import sqlite3
import logging
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request

# SETTINGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 8129893559

API = f"https://api.telegram.org/bot{TOKEN}"

DB = "clover.db"


# DATABASE
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        registered TEXT,
        subscription TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS promos (
        code TEXT PRIMARY KEY,
        days INTEGER,
        max_uses INTEGER,
        uses INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS redemptions (
        user_id INTEGER,
        code TEXT,
        PRIMARY KEY(user_id, code)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# TELEGRAM
def send_message(chat_id, text, keyboard=None):

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
        logger.info("Telegram: %s", response.status_code)

    except requests.RequestException as e:
        logger.error("Telegram error: %s", e)


# MAIN MENU
def main_menu():

    return {
        "keyboard": [
            [{"text": "🛒 Купить VPN"}],
            [{"text": "👤 Мой профиль"}],
            [{"text": "🎁 Промокод"}],
            [{"text": "🌍 Выбор страны"}],
            [{"text": "💬 Поддержка"}]
        ],
        "resize_keyboard": True
    }


# REGISTER USER
def register_user(user_id, username):

    conn = db()

    conn.execute("""
    INSERT OR IGNORE INTO users
    (user_id, username, registered)
    VALUES (?, ?, ?)
    """, (
        user_id,
        username,
        datetime.now(timezone.utc).isoformat()
    ))

    conn.execute("""
    UPDATE users SET username = ? WHERE user_id = ?
    """, (username, user_id))

    conn.commit()
    conn.close()


# PROFILE
def profile(user_id):

    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    if not user:
        return "Профиль не найден."

    subscription = user["subscription"]

    if subscription:
        expiry = datetime.fromisoformat(subscription)

        if expiry > datetime.now(timezone.utc):
            status = f"Активна до: {expiry.strftime('%d.%m.%Y %H:%M')} UTC"
        else:
            status = "Подписка закончилась."
    else:
        status = "Подписка отсутствует."

    return (
        "👤 CLOVER VPN — ТВОЙ ПРОФИЛЬ\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{user['username'] or 'нет'}\n"
        f"📅 Регистрация: {user['registered'][:10]}\n\n"
        f"💎 Подписка: {status}"
    )


# ACTIVATE PROMO
def activate_promo(user_id, code):

    code = code.upper().strip()

    conn = db()

    promo = conn.execute(
        "SELECT * FROM promos WHERE code = ?",
        (code,)
    ).fetchone()

    if not promo:
        conn.close()
        return "❌ Промокод не найден."

    if promo["uses"] >= promo["max_uses"]:
        conn.close()
        return "❌ Лимит активаций исчерпан."

    redeemed = conn.execute("""
        SELECT * FROM redemptions
        WHERE user_id = ? AND code = ?
    """, (user_id, code)).fetchone()

    if redeemed:
        conn.close()
        return "❌ Ты уже использовал этот промокод."

    user = conn.execute(
        "SELECT subscription FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    now = datetime.now(timezone.utc)

    current = None

    if user and user["subscription"]:
        current = datetime.fromisoformat(user["subscription"])

    start = current if current and current > now else now

    expiry = start + timedelta(days=promo["days"])

    conn.execute("""
        UPDATE users SET subscription = ?
        WHERE user_id = ?
    """, (expiry.isoformat(), user_id))

    conn.execute("""
        INSERT INTO redemptions (user_id, code)
        VALUES (?, ?)
    """, (user_id, code))

    conn.execute("""
        UPDATE promos SET uses = uses + 1
        WHERE code = ?
    """, (code,))

    conn.commit()
    conn.close()

    return (
        f"🎉 Промокод {code} активирован!\n\n"
        f"💎 Получено дней: {promo['days']}\n"
        f"📅 Подписка до: {expiry.strftime('%d.%m.%Y')} UTC"
    )


# ADMIN
def admin_panel():

    return (
        "👑 CLOVER VPN — ADMIN PANEL\n\n"
        "/users — пользователи\n"
        "/addpromo CODE DAYS USES — создать промокод\n"
        "/delpromo CODE — удалить промокод\n"
        "/promos — список промокодов"
    )


def handle_admin(user_id, text):

    if user_id != ADMIN_ID:
        return "⛔ Нет доступа."

    parts = text.split()

    if parts[0] == "/admin":
        return admin_panel()

    if parts[0] == "/users":

        conn = db()

        count = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        conn.close()

        return f"👥 Всего пользователей: {count}"

    if parts[0] == "/addpromo":

        if len(parts) != 4:
            return "Использование:\n/addpromo CODE DAYS USES"

        try:
            code = parts[1].upper()
            days = int(parts[2])
            uses = int(parts[3])

            if not code.isalnum() or not (1 <= days <= 3650) or not (1 <= uses <= 100000):
                return "❌ Проверь код, дни и количество активаций."

            conn = db()

            conn.execute("""
                INSERT INTO promos (code, days, max_uses)
                VALUES (?, ?, ?)
            """, (code, days, uses))

            conn.commit()
            conn.close()

            return f"✅ Промокод {code} создан!\nДней: {days}\nАктиваций: {uses}"

        except ValueError:
            return "❌ Дни и количество активаций должны быть числами."

        except sqlite3.IntegrityError:
            return "❌ Такой промокод уже существует."

    if parts[0] == "/delpromo":

        if len(parts) != 2:
            return "Использование: /delpromo CODE"

        conn = db()

        conn.execute(
            "DELETE FROM promos WHERE code = ?",
            (parts[1].upper(),)
        )

        conn.commit()
        conn.close()

        return "✅ Команда удаления выполнена."

    if parts[0] == "/promos":

        conn = db()

        promos = conn.execute(
            "SELECT * FROM promos"
        ).fetchall()

        conn.close()

        if not promos:
            return "Промокодов пока нет."

        result = "🎁 ПРОМОКОДЫ:\n\n"

        for p in promos:
            result += (
                f"Код: {p['code']}\n"
                f"Дней: {p['days']}\n"
                f"Использовано: {p['uses']}/{p['max_uses']}\n\n"
            )

        return result

    return "Неизвестная команда администратора."


# COMMAND HANDLER
def handle_message(message):

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    username = message["from"].get("username")

    text = message.get("text", "").strip()

    if not text:
        return

    register_user(user_id, username)

    command = text.split()[0].split("@")[0]

    # START
    if command == "/start":

        send_message(
            chat_id,
            "☘️ ДОБРО ПОЖАЛОВАТЬ В CLOVER VPN!\n\n"
            "Твой интернет. Твои правила.\n\n"
            "Выбери нужный раздел:",
            main_menu()
        )

    # HELP
    elif command == "/help":

        send_message(
            chat_id,
            "📚 ДОСТУПНЫЕ КОМАНДЫ\n\n"
            "/start — главное меню\n"
            "/profile — профиль\n"
            "/buy — купить VPN\n"
            "/status — статус подписки\n"
            "/promo CODE — активировать промокод\n"
            "/support — поддержка"
        )

    # PROFILE
    elif command in ["/profile"] or text == "👤 Мой профиль":

        send_message(chat_id, profile(user_id))

    # BUY
    elif command == "/buy" or text == "🛒 Купить VPN":

        send_message(
            chat_id,
            "🛒 ПОКУПКА CLOVER VPN\n\n"
            "Тарифы и оплата Telegram Stars будут подключены следующим этапом."
        )

    # STATUS
    elif command == "/status":

        send_message(chat_id, profile(user_id))

    # PROMO
    elif command == "/promo":

        parts = text.split()

        if len(parts) < 2:
            send_message(
                chat_id,
                "🎁 Чтобы активировать промокод, напиши:\n/promo CODE"
            )
        else:
            send_message(
                chat_id,
                activate_promo(user_id, parts[1])
            )

    elif text == "🎁 Промокод":

        send_message(
            chat_id,
            "🎁 Введи промокод командой:\n/promo CODE"
        )

    # SUPPORT
    elif command == "/support" or text == "💬 Поддержка":

        send_message(
            chat_id,
            "💬 CLOVER VPN SUPPORT\n\n"
            "По вопросам работы сервиса обратись к администратору."
        )

    # COUNTRY
    elif text == "🌍 Выбор страны":

        send_message(
            chat_id,
            "🌍 Доступные страны:\n\n"
            "🇲🇩 Молдова\n"
            "🇷🇴 Румыния\n"
            "🇩🇪 Германия\n"
            "🇳🇱 Нидерланды\n"
            "🇫🇷 Франция\n"
            "🇺🇸 США\n\n"
            "Серверы пока настраиваются."
        )

    # ADMIN
    elif command in ["/admin", "/users", "/addpromo", "/delpromo", "/promos"]:

        send_message(
            chat_id,
            handle_admin(user_id, text)
        )

    else:

        send_message(
            chat_id,
            "☘️ Используй кнопки меню или команду /help."
        )


# WEBHOOK
@app.route("/", methods=["GET"])
def home():
    return "CLOVER VPN is running!"


@app.route("/webhook", methods=["POST"])
def webhook():

    update = request.get_json(silent=True)

    if not update:
        return "OK"

    message = update.get("message")

    if message:
        handle_message(message)

    return "OK"


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
