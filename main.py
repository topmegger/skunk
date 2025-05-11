from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
import logging
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Шаги разговора
MODEL, PHOTOS, SCREEN, BODY, REPAIR, BATTERY, MALFUNCTION, COMPLETENESS, COMMENTS, METRO, CONFIRM = range(11)

# Ваши данные
TOKEN = "7944685358:AAEL_XQIC5CYz9hsiJCurLQmYqVyoGQddGo"
ADMIN_CHAT_ID = 758347965

# Хранилища
requests_db = {}     # req_id → данные заявки
chat_sessions = {}   # user_id → req_id
next_req_id = 1

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([["Оценить устройство"]], resize_keyboard=True)
    await update.message.reply_text("Привет! Чтобы начать продажу iPhone, нажмите кнопку ниже:", reply_markup=kb)
    return MODEL

async def model_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "Оценить устройство":
        return MODEL
    await update.message.reply_text(
        "1️⃣ Укажите модель и объём памяти (например: iPhone 12 Pro 256 GB):",
        reply_markup=ReplyKeyboardRemove()
    )
    return PHOTOS

async def photo_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # сохранение модели
    if text and 'model' not in ctx.user_data and text != "Готово":
        ctx.user_data['model'] = text
        ctx.user_data['photos'] = []
        kb = ReplyKeyboardMarkup([[KeyboardButton("Готово")]], resize_keyboard=True)
        await update.message.reply_text(
            "✅ Модель сохранена.\n📸 Пришлите фото со всех сторон. Когда закончите — нажмите «Готово».",
            reply_markup=kb
        )
        return PHOTOS
    # кнопка Готово
    if text == "Готово":
        photos = ctx.user_data.get('photos', [])
        if not photos:
            await update.message.reply_text("⚠️ Нужно хотя бы одно фото.")
            return PHOTOS
        await update.message.reply_text("👍 Фото получены.", reply_markup=ReplyKeyboardRemove())
        # экран
        buttons = [
            InlineKeyboardButton("Без дефектов", callback_data="screen_0"),
            InlineKeyboardButton("1–2 мелкие царапины", callback_data="screen_1"),
            InlineKeyboardButton("Много мелких царапин", callback_data="screen_2"),
            InlineKeyboardButton("Глубокие царапины", callback_data="screen_3"),
            InlineKeyboardButton("Пятна/блики/выгорание", callback_data="screen_4"),
            InlineKeyboardButton("Полосы и битые пиксели", callback_data="screen_5"),
        ]
        kb = InlineKeyboardMarkup([buttons[0:2], buttons[2:4], buttons[4:6]])
        await update.message.reply_text("2️⃣ Состояние экрана:", reply_markup=kb)
        return SCREEN
    # фото
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        ctx.user_data.setdefault('photos', []).append(fid)
        await update.message.reply_text(f"Фото принято (всего {len(ctx.user_data['photos'])}).")
        return PHOTOS
    # всё остальное
    kb = ReplyKeyboardMarkup([[KeyboardButton("Готово")]], resize_keyboard=True)
    await update.message.reply_text("Пришлите фото или нажмите «Готово»", reply_markup=kb)
    return PHOTOS

async def screen_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: await update.callback_query.answer()
    except BadRequest: pass
    idx = int(update.callback_query.data.split("_")[1])
    opts = ["Без дефектов","1–2 мелкие царапины","Много мелких царапин",
            "Глубокие царапины","Пятна/блики/выгорание","Полосы и битые пиксели"]
    ctx.user_data['screen'] = opts[idx]
    buttons = [
        InlineKeyboardButton("Без дефектов", callback_data="body_0"),
        InlineKeyboardButton("Мелкие царапины", callback_data="body_1"),
        InlineKeyboardButton("Глубокие царапины", callback_data="body_2"),
        InlineKeyboardButton("Сколы/трещины", callback_data="body_3"),
        InlineKeyboardButton("Щели/зазоры", callback_data="body_4"),
        InlineKeyboardButton("Изгиб/вмятины", callback_data="body_5"),
    ]
    kb = InlineKeyboardMarkup([buttons[0:2], buttons[2:4], buttons[4:6]])
    await update.callback_query.message.reply_text("3️⃣ Состояние корпуса:", reply_markup=kb)
    return BODY

async def body_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: await update.callback_query.answer()
    except BadRequest: pass
    idx = int(update.callback_query.data.split("_")[1])
    opts = ["Без дефектов","Мелкие царапины","Глубокие царапины",
            "Сколы/трещины","Щели/зазоры","Изгиб/вмятины"]
    ctx.user_data['body'] = opts[idx]
    await update.callback_query.message.reply_text(
        "4️⃣ Были ли ремонты? Если были — опишите какие, иначе — «нет»."
    )
    return REPAIR

async def repair_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['repair'] = update.message.text
    await update.message.reply_text("5️⃣ Состояние аккумулятора (процент/описание):")
    return BATTERY

async def battery_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['battery'] = update.message.text
    await update.message.reply_text("6️⃣ Неисправности (если есть — перечислите; если нет — «нет»):")
    return MALFUNCTION

async def malfunction_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['malfunction'] = update.message.text
    await update.message.reply_text("7️⃣ Что в комплекте? (коробка, провод, чек…):")
    return COMPLETENESS

async def completeness_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['completeness'] = update.message.text
    await update.message.reply_text("8️⃣ Дополнительные комментарии (необязательно):")
    return COMMENTS

async def comments_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['comments'] = update.message.text
    await update.message.reply_text("9️⃣ Укажите ближайшую станцию метро в Москве:")
    return METRO

async def metro_step(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['metro'] = update.message.text
    data = ctx.user_data
    summary = (
        f"Модель/память: {data['model']}\n"
        f"Фото: {len(data['photos'])} шт.\n"
        f"Экран: {data['screen']}\n"
        f"Корпус: {data['body']}\n"
        f"Ремонты: {data['repair']}\n"
        f"Аккум.: {data['battery']}\n"
        f"Неисправности: {data['malfunction']}\n"
        f"Комплект: {data['completeness']}\n"
        f"Комментарии: {data['comments'] or '—'}\n"
        f"Метро: {data['metro']}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Подтвердить", callback_data="confirm_yes"),
        InlineKeyboardButton("Отменить", callback_data="confirm_no"),
    ]])
    await update.message.reply_text("🔟 Проверьте заявку и подтвердите:\n\n" + summary, reply_markup=kb)
    return CONFIRM

async def confirm_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: await update.callback_query.answer()
    except BadRequest: pass
    if update.callback_query.data == "confirm_no":
        await update.callback_query.message.reply_text("Отменено. Для новой заявки — /start")
        return ConversationHandler.END

    global next_req_id
    rid = next_req_id; next_req_id += 1
    requests_db[rid] = {"user_id": update.callback_query.from_user.id, **ctx.user_data}
    chat_sessions[update.callback_query.from_user.id] = rid

    data = requests_db[rid]
    txt = (
        f"Заявка #{rid}\nПользователь: @{update.callback_query.from_user.username}\n\n"
        f"Модель/память: {data['model']}\nЭкран: {data['screen']}\n"
        f"Корпус: {data['body']}\nРемонты: {data['repair']}\n"
        f"Аккум.: {data['battery']}\nНеисправности: {data['malfunction']}\n"
        f"Комплект: {data['completeness']}\nКомментарии: {data['comments'] or '—'}\n"
        f"Метро: {data['metro']}"
    )
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("Ответить", callback_data=f"answer_{rid}")]])
    await ctx.bot.send_message(ADMIN_CHAT_ID, txt, reply_markup=btn)
    media = [InputMediaPhoto(fid) for fid in data['photos']]
    await ctx.bot.send_media_group(ADMIN_CHAT_ID, media)

    await update.callback_query.message.reply_text(
        "Ваша заявка принята! Менеджер свяжется с вами."
    )
    return ConversationHandler.END

async def forward_to_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in chat_sessions:
        return
    rid = chat_sessions[uid]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Ответить", callback_data=f"answer_{rid}")]])
    if update.message.text:
        await ctx.bot.send_message(ADMIN_CHAT_ID, f"[#{rid}] {update.message.text}", reply_markup=kb)
    elif update.message.photo:
        await ctx.bot.send_photo(ADMIN_CHAT_ID, update.message.photo[-1].file_id,
                                 caption=f"[#{rid}] Фото", reply_markup=kb)

async def answer_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try: await update.callback_query.answer()
    except BadRequest: pass
    rid = int(update.callback_query.data.split("_")[1])
    ctx.user_data['rid'] = rid
    await update.callback_query.message.reply_text(f"Введите ответ для заявки #{rid}:")
    return 100

async def admin_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rid = ctx.user_data.get('rid')
    if rid not in requests_db:
        await update.message.reply_text("Заявка не найдена.")
        return ConversationHandler.END
    await ctx.bot.send_message(requests_db[rid]['user_id'], f"Ответ по заявке #{rid}:\n\n{update.message.text}")
    await update.message.reply_text("Ответ отправлен.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Произошла ошибка:", exc_info=context.error)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    user_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODEL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, model_step)],
            PHOTOS:     [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), photo_handler)],
            SCREEN:     [CallbackQueryHandler(screen_handler, pattern="^screen_")],
            BODY:       [CallbackQueryHandler(body_handler, pattern="^body_")],
            REPAIR:     [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_step)],
            BATTERY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, battery_step)],
            MALFUNCTION:[MessageHandler(filters.TEXT & ~filters.COMMAND, malfunction_step)],
            COMPLETENESS:[MessageHandler(filters.TEXT & ~filters.COMMAND, completeness_step)],
            COMMENTS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, comments_step)],
            METRO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, metro_step)],
            CONFIRM:    [CallbackQueryHandler(confirm_handler, pattern="^confirm_")],
        },
        fallbacks=[]
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(answer_callback, pattern="^answer_")],
        states={100: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply)]},
        fallbacks=[]
    )

    app.add_handler(user_conv)
    app.add_handler(admin_conv)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_admin), group=1)
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
