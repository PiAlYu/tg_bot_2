import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

DATA_FILE = "shopping_lists.json"


def load_shopping_lists():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_shopping_lists(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


shopping_lists = load_shopping_lists()


# ——— КЛАВИАТУРЫ —————————————————————————————————————————————

def main_menu():
    return ReplyKeyboardMarkup(
        [["Админ", "Пользователь"]],
        resize_keyboard=True
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        [["Создать список", "Изменить список"],
         ["Удалить список"],
         ["⏪ Назад"]],
        resize_keyboard=True
    )


def admin_edit_menu():
    return ReplyKeyboardMarkup(
        [["Отправить заново", "Добавить товар"], ["⏪ Назад"]],
        resize_keyboard=True
    )


def user_menu():
    return ReplyKeyboardMarkup(
        [["⏪ Назад"]],
        resize_keyboard=True
    )


# ——— СТАРТ ——————————————————————————————————————————————————

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Выберите режим работы:", reply_markup=main_menu()
    )


# ——— ОБРАБОТКА ТЕКСТА ——————————————————————————————————————

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    ud = context.user_data

    # — ГЛАВНОЕ МЕНЮ ——
    if text == "Админ" and "state" not in ud:
        ud["state"] = "admin"
        await update.message.reply_text("Меню админа:", reply_markup=admin_menu())
        return

    if text == "Пользователь" and "state" not in ud:
        if not shopping_lists:
            await update.message.reply_text("Нет доступных списков.")
            return
        ud["state"] = "user"
        await update.message.reply_text(
            "Выберите список:", reply_markup=user_list_keyboard()
        )
        return

    # —⏪ Назад из любого подменю ——
    if text == "⏪ Назад":
        # если мы в админских или пользовательских подменю
        if ud.get("state") in ("admin", "creating", "modifying", "editing"):
            ud.clear()
            await update.message.reply_text("Возврат в главное меню:", reply_markup=main_menu())
            return
        if ud.get("state") == "user_select":
            ud["state"] = "user"
            await update.message.reply_text("Выберите список:", reply_markup=user_list_keyboard())
            return

    # ——— АДМИН ————————————————————————————————————————————
    if ud.get("state") == "admin":
        if text == "Создать список":
            ud["state"] = "creating_name"
            await update.message.reply_text("Введите имя нового списка:")
            return
        if text == "Изменить список":
            if not shopping_lists:
                await update.message.reply_text("Список пуст, нечего менять.")
                return
            ud["state"] = "modifying"
            await update.message.reply_text("Выберите, какой список редактировать:", reply_markup=admin_list_keyboard())
            return
        if text == "Удалить список":
            if not shopping_lists:
                await update.message.reply_text("Нет списков для удаления.")
                return
            ud["state"] = "deleting"
            await update.message.reply_text(
                "Выберите список для удаления:", reply_markup=admin_list_keyboard()
            )
            return

    # ——— СОЗДАНИЕ НОВОГО СПИСКА ————————————————————————————
    if ud.get("state") == "creating_name":
        ud["new_name"] = text
        ud["state"] = "creating_items"
        await update.message.reply_text(
            f"Введите данные для списка «{text}».\n"
            "Первая строка — дата, далее товары по одной на строке."
        )
        return

    if ud.get("state") == "creating_items":
        name = ud["new_name"]
        shopping_lists[name] = text
        save_shopping_lists(shopping_lists)
        ud.clear()
        await update.message.reply_text(f"Список «{name}» создан!", reply_markup=main_menu())
        return

    # ——— РЕДАКТИРОВАНИЕ СУЩЕСТВУЮЩЕГО СПИСКА ————————————————————
    if ud.get("state") == "modifying":
        if text in shopping_lists:
            ud["edit_name"] = text
            ud["state"] = "editing"
            await update.message.reply_text(
                f"Список «{text}» выбран.\n"
                "Выберите действие:", reply_markup=admin_edit_menu()
            )
        return

    if ud.get("state") == "editing":
        name = ud["edit_name"]
        if text == "Отправить заново":
            ud["state"] = "rewrite"
            await update.message.reply_text("Отправьте новый список целиком:")
            return
        if text == "Добавить товар":
            ud["state"] = "add_items"
            await update.message.reply_text("Отправьте новые товары по одной строке:")
            return

    if ud.get("state") == "rewrite":
        shopping_lists[ud["edit_name"]] = text
        save_shopping_lists(shopping_lists)
        ud.clear()
        await update.message.reply_text("Список перезаписан!", reply_markup=main_menu())
        return

    if ud.get("state") == "add_items":
        old = shopping_lists[ud["edit_name"]]
        shopping_lists[ud["edit_name"]] = old + "\n" + text
        save_shopping_lists(shopping_lists)
        ud.clear()
        await update.message.reply_text("Товары добавлены!", reply_markup=main_menu())
        return

    if ud.get("state") == "deleting":
        if text in shopping_lists:
            del shopping_lists[text]
            save_shopping_lists(shopping_lists)
            ud.clear()
            await update.message.reply_text(f"Список «{text}» удалён.", reply_markup=main_menu())
        else:
            await update.message.reply_text("Такой список не найден.")
        return

    # ——— ПОЛЬЗОВАТЕЛЬ ————————————————————————————————————————
    if ud.get("state") == "user":
        if text == "⏪ Назад":
            ud.clear()
            await update.message.reply_text("Возврат в главное меню:", reply_markup=main_menu())
            return
        elif text in shopping_lists:
            ud["active_list"] = text
            ud["state"] = "user_select"
            await update.message.reply_text(
                f"Список «{text}»:\nВыберите режим просмотра:",
                reply_markup=ReplyKeyboardMarkup(
                    [["Показать по‑товарно", "Показать списком"], ["⏪ Назад"]],
                    resize_keyboard=True
                )
            )
            return
        else:
            await update.message.reply_text("Неправильное имя списка.")
            return

    if ud.get("state") == "user_select":
        name = ud["active_list"]
        if text == "Показать списком":
            await update.message.reply_text(shopping_lists[name])
        elif text == "Показать по‑товарно":
            lines = shopping_lists[name].splitlines()
            ud["current_items"] = lines[1:].copy()
            await send_item_buttons(update, ud["current_items"])
        return

    # ——— ВСЕ ПРОЧИЕ ——
    await update.message.reply_text("Не распознал. Вернитесь в главное меню:", reply_markup=main_menu())


# ——— КНОПКИ ДЛЯ ВЫБОРА СПИСКОВ ———————————————————————————

def admin_list_keyboard():
    return ReplyKeyboardMarkup(
        [list(shopping_lists.keys()), ["⏪ Назад"]],
        resize_keyboard=True
    )


def user_list_keyboard():
    if shopping_lists:
        rows = []
        names = list(shopping_lists.keys())
        # разбиваем на строки по 2 кнопки
        for i in range(0, len(names), 2):
            rows.append(names[i : i + 2])
        rows.append(["⏪ Назад"])
        return ReplyKeyboardMarkup(rows, resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["⏪ Назад"]], resize_keyboard=True)


# ——— ПО‑ТОВАРНО (INLINE) ——————————————————————————————————

async def send_item_buttons(update: Update, items):
    if not items:
        await update.message.reply_text("Все товары куплены! 🎉")
        return
    kb = [[InlineKeyboardButton(i, callback_data=i)] for i in items]
    await update.message.reply_text("Нажмите купленный товар:", reply_markup=InlineKeyboardMarkup(kb))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    item = query.data

    items = ud.get("current_items", [])
    if item in items:
        items.remove(item)
        ud["current_items"] = items
    if items:
        kb = [[InlineKeyboardButton(i, callback_data=i)] for i in items]
        await query.edit_message_text("Нажмите купленный товар:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await query.edit_message_text("Все товары куплены!")
        # Отправка эффекта 🎉
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🎉"
        )


# ——— ЗАПУСК ——————————————————————————————————————————————

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
