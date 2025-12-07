import os
import re
import logging
import telebot
from telebot import types

# ---------- НАСТРОЙКИ ЧЕРЕЗ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ----------

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

_admin_id = os.getenv("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(_admin_id) if _admin_id else None

_channel_id = os.getenv("CHANNEL_ID", "0")
CHANNEL_ID = int(_channel_id) if _channel_id else 0

# ---------- ЛОГИ ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- ИНИЦИАЛИЗАЦИЯ БОТА ----------

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ---------- СОСТОЯНИЯ И ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ ----------

STATE_EMAIL = "EMAIL"
STATE_ABOUT = "ABOUT"
STATE_WISH = "WISH"

user_state = {}   # user_id -> state
user_data = {}    # user_id -> {email, about, wish}


# ---------- ХЕЛПЕРЫ ----------

def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def set_state(user_id: int, state: str | None):
    if state is None:
        user_state.pop(user_id, None)
    else:
        user_state[user_id] = state


def get_state(user_id: int) -> str | None:
    return user_state.get(user_id)


def get_user_data(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {}
    return user_data[user_id]


def clear_user(user_id: int):
    user_state.pop(user_id, None)
    user_data.pop(user_id, None)


# ---------- ОБРАБОТЧИКИ ----------

@bot.message_handler(commands=["start"])
def handle_start(message: types.Message):
    user_id = message.from_user.id
    clear_user(user_id)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Принять участие 🎁", callback_data="join"))

    text = (
        "🎄 Стартуем 1wish!\n\n"
        "В преддверии праздников мы запускаем магическую акцию, где каждый может загадать своё желание, "
        "а 26 декабря мы выберем 26 счастливчиков и исполним их мечты!\n\n"
        "Хочешь поучаствовать?\n"
        "Нажимай ниже и начнём регистрацию в 1wish! ✨"
    )

    bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: c.data == "join")
def handle_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    set_state(user_id, STATE_EMAIL)

    bot.answer_callback_query(callback.id)
    bot.send_message(
        callback.message.chat.id,
        "Отлично!\nЧтобы подтвердить участие, укажи, пожалуйста, свой email 👇",
    )


@bot.message_handler(func=lambda m: get_state(m.from_user.id) == STATE_EMAIL)
def handle_email(message: types.Message):
    user_id = message.from_user.id
    email = message.text.strip()

    if not is_valid_email(email):
        bot.send_message(
            message.chat.id,
            "❌ Вы ввели неправильную почту, попробуйте ещё раз!",
        )
        return

    data = get_user_data(user_id)
    data["email"] = email
    set_state(user_id, STATE_ABOUT)

    bot.send_message(
        message.chat.id,
        "Спасибо! ✔️\n\n"
        "Теперь расскажи немного о себе: чем ты занимаешься?\n"
        "Работа, хобби, увлечения — всё, что хочешь",
    )


@bot.message_handler(func=lambda m: get_state(m.from_user.id) == STATE_ABOUT)
def handle_about(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    data["about"] = message.text.strip()

    set_state(user_id, STATE_WISH)

    bot.send_message(
        message.chat.id,
        "Супер! ✨\n\n"
        "А теперь самое важное — какое желание ты хочешь, чтобы Санта 1win исполнил?\n\n"
        "Напиши, что именно ты хочешь получить 🎁",
    )


@bot.message_handler(func=lambda m: get_state(m.from_user.id) == STATE_WISH)
def handle_wish(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    data["wish"] = message.text.strip()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("1WIN", url="https://lkhq.cc/350c71"))
    keyboard.add(types.InlineKeyboardButton("Телеграм", url="https://t.me/+itqbiJNevPBmMTYy"))
    keyboard.add(types.InlineKeyboardButton("Я проявил активность", callback_data="check_active"))

    bot.send_message(
        message.chat.id,
        "Отлично, твоё желание записано!\n\n"
        "🚀 Чтобы точно выиграть, стань новым пользователем нашей платформы и внеси минимальный депозит, "
        "а также будь подписчиком нашего телеграм-канала — всё это учитывается и помогает победить именно тебе 🎄\n\n"
        "Перейди на сайт и подпишись на канал, а потом нажми «Я проявил активность».",
        reply_markup=keyboard,
    )


@bot.callback_query_handler(func=lambda c: c.data == "check_active")
def handle_check_active(callback: types.CallbackQuery):
    user = callback.from_user
    user_id = user.id
    chat_id = callback.message.chat.id

    bot.answer_callback_query(callback.id)

    # Проверяем подписку на канал
    tg_ok = False
    try:
        if CHANNEL_ID != 0:
            member = bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ("member", "administrator", "creator"):
                tg_ok = True
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")

    site_ok = True  # сайт по факту проверить нельзя, считаем ок

    if not tg_ok:
        bot.send_message(
            chat_id,
            "❌ Похоже, ты ещё не подписан на наш Telegram-канал.\n\n"
            "Подпишись по кнопке «Телеграм» выше, а затем снова нажми «Я проявил активность». 💙",
        )
        return

    if not site_ok:
        bot.send_message(
            chat_id,
            "❌ Похоже, ты ещё не проявил активность на сайте. Перейди по кнопке 1WIN и попробуй ещё раз.",
        )
        return

    # Всё ок: финальное сообщение
    bot.send_message(
        chat_id,
        "Вот и всё! 🫶\n"
        "Желаем тебе удачи и новогоднего настроения 💙",
    )

    # Отправляем данные админу
    if ADMIN_CHAT_ID:
        data = get_user_data(user_id)
        email = data.get("email", "—")
        about = data.get("about", "—")
        wish = data.get("wish", "—")

        result_text = (
            f"Новая заявка из бота 🎁\n\n"
            f"👤 Пользователь: {user.full_name} (@{user.username or 'нет username'})\n"
            f"🆔 user_id: {user.id}\n\n"
            f"📧 Email: {email}\n"
            f"ℹ️ О себе: {about}\n"
            f"🎁 Желание: {wish}\n"
        )
        try:
            bot.send_message(ADMIN_CHAT_ID, result_text)
        except Exception as e:
            logger.error(f"Не удалось отправить заявку админу: {e}")

    clear_user(user_id)


# ---------- ЗАПУСК ----------

if __name__ == "__main__":
    logger.info("Bot started with telebot polling")
    bot.infinity_polling(skip_pending=True)
