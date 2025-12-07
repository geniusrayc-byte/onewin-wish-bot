import logging
import re
import os
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------- НАСТРОЙКИ ЧЕРЕЗ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ----------

# токен бота
TOKEN = os.getenv("BOT_TOKEN")

# твой личный chat_id, куда отправлять заявки
_admin_id = os.getenv("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(_admin_id) if _admin_id else None

# id канала, на который нужно быть подписанным
_channel_id = os.getenv("CHANNEL_ID", "0")
CHANNEL_ID = int(_channel_id) if _channel_id else 0

# ---------- ЛОГИ ----------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- СОСТОЯНИЯ ДИАЛОГА ----------

EMAIL, ABOUT, WISH, CHECK_ACTIVITY = range(4)


# ---------- ВАЛИДАЦИЯ EMAIL ----------

def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


# ---------- ХЭНДЛЕРЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение с кнопкой."""
    keyboard = [
        [InlineKeyboardButton("Принять участие 🎁", callback_data="join")]
    ]

    text = (
        "🎄 Стартуем 1wish!\n\n"
        "В преддверии праздников мы запускаем магическую акцию, где каждый может загадать своё желание, "
        "а 26 декабря мы выберем 26 счастливчиков и исполним их мечты!\n\n"
        "Хочешь поучаствовать?\n"
        "Нажимай ниже и начнём регистрацию в 1wish! ✨"
    )

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Нажатие на кнопку 'Принять участие'."""
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Отлично! \n"
        "Чтобы подтвердить участие, укажи, пожалуйста, свой email 👇"
    )
    return EMAIL


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем и валидируем email."""
    email = update.message.text.strip()

    if not is_valid_email(email):
        await update.message.reply_text(
            "❌ Вы ввели неправильную почту, попробуйте ещё раз!"
        )
        return EMAIL

    context.user_data["email"] = email

    await update.message.reply_text(
        "Спасибо! ✔️\n\n"
        "Теперь расскажи немного о себе: чем ты занимаешься?\n"
        "Работа, хобби, увлечения — всё, что хочешь"
    )
    return ABOUT


async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инфа о себе."""
    context.user_data["about"] = update.message.text.strip()

    await update.message.reply_text(
        "Супер! ✨\n\n"
        "А теперь самое важное — какое желание ты хочешь, чтобы Санта 1win исполнил?\n\n"
        "Напиши, что именно ты хочешь получить 🎁"
    )
    return WISH


async def wish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Желание + показ кнопок активности."""
    context.user_data["wish"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton("1WIN", url="https://lkhq.cc/350c71")],
        [InlineKeyboardButton("Телеграм", url="https://t.me/+itqbiJNevPBmMTYy")],
        [InlineKeyboardButton("Я проявил активность", callback_data="check_active")],
    ]

    await update.message.reply_text(
        "Отлично, твоё желание записано!\n\n"
        "🚀 Чтобы точно выиграть, стань новым пользователем нашей платформы и внеси минимальный депозит, "
        "а также будь подписчиком нашего телеграм-канала — всё это учитывается и помогает победить именно тебе 🎄\n\n"
        "Перейди на сайт и подпишись на канал, а потом нажми «Я проявил активность».",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CHECK_ACTIVITY


async def check_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка подписки на канал и финальное сообщение."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Проверяем подписку на канал
    tg_ok = False
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user.id)
        if member.status in ("member", "creator", "administrator"):
            tg_ok = True
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")

    # Сайт технически проверить нельзя, считаем ок
    site_ok = True

    if not tg_ok:
        await query.message.reply_text(
            "❌ Похоже, ты ещё не подписан на наш Telegram-канал.\n\n"
            "Подпишись по кнопке «Телеграм» выше, а затем снова нажми «Я проявил активность». 💙"
        )
        return CHECK_ACTIVITY

    if not site_ok:
        await query.message.reply_text(
            "❌ Похоже, ты ещё не проявил активность на сайте. Перейди по кнопке 1WIN и попробуй ещё раз."
        )
        return CHECK_ACTIVITY

    # Всё ок — финальное сообщение
    await query.message.reply_text(
        "Вот и всё! 🫶\n"
        "Желаем тебе удачи и новогоднего настроения 💙"
    )

    # Отправляем заявку админу, если указан
    if ADMIN_CHAT_ID:
        email = context.user_data.get("email", "—")
        about = context.user_data.get("about", "—")
        wish = context.user_data.get("wish", "—")
        result_text = (
            f"Новая заявка из бота 🎁\n\n"
            f"👤 Пользователь: {user.full_name} (@{user.username or 'нет username'})\n"
            f"🆔 user_id: {user.id}\n\n"
            f"📧 Email: {email}\n"
            f"ℹ️ О себе: {about}\n"
            f"🎁 Желание: {wish}\n"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=result_text)
        except Exception as e:
            logger.error(f"Не удалось отправить заявку админу: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# ---------- MAIN ----------

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(join_callback, pattern="^join$")],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handler)],
            ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_handler)],
            WISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, wish_handler)],
            CHECK_ACTIVITY: [CallbackQueryHandler(check_activity, pattern="^check_active$")],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
