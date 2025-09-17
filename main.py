import os
import threading
import time

from flask import Flask, send_file
import telebot
import requests

# Замініть 'YOUR_BOT_TOKEN' на токен, який ви отримали від BotFather
BOT_TOKEN = '8264718582:AAGly9dsfTerEak5GbcfGDA5lRDlOndqSbg'

# URL-адреси вашого API Google Apps Script
GOOGLE_SHEET_API_ACCESSORIES = 'https://script.google.com/macros/s/AKfycbzt1Hf_6copt-mWjGFzKo78lloDEYAsoDvIIN_IgAPKyyRm348g3O7e9eB5Ouh-gIlEpA/exec'
GOOGLE_SHEET_API_FILMS = 'https://script.google.com/macros/s/AKfycbwxXf15evwxyGu_0eC2kFHdWnHw3jLS8jEkKgJZjO3mPl7COmGUUGlrKq2uDRqsIy5bAw/exec'

bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary mapping category names to emojis
category_icons = {
    "Навушники": "🎧",
    "Акустика": "🔊",
    "Миша комп.": "🖱️",
    "Набір посуду": "🍽️",
    "Сковорода": "🍳",
    "Клавіатура": "⌨️",
    "Вирізна 6.5'": "🛡️",
    "Вирізна 11'": "🧱",
    "Вирізна 13'": "💎"
}

pma_icons = {
    "SPUSH": "🔥 Пріоритет",
    "Spush": "🔥 Пріоритет",
    "spush": "🔥 Пріоритет",
    "SHELF": "✅ На складі",
    "Shelf": "✅ На складі",
    "shelf": "✅ На складі"
}


# --- Обробка команд /start і /привіт ---
@bot.message_handler(commands=['start', 'привіт'])
def send_greeting_and_button(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add('✨ Аксесуари ТОП СКЮ')
    keyboard.add('📱 Плівка та скло')
    greeting_text = (
        f"👋 Вітаю, {message.from_user.username}, в інформаційному боті магазину «МОСТ 1»! 👋\n\n"
        "Натисніть кнопку, щоб переглянути ТОП СКЮ або інформацію по плівкам!"
    )
    bot.send_message(message.chat.id, greeting_text, reply_markup=keyboard)


# --- Обробка натискання на кнопку "Аксесуари ТОП СКЮ" ---
@bot.message_handler(func=lambda message: message.text == '✨ Аксесуари ТОП СКЮ')
def handle_top_sku_button(message):
    status_message = bot.send_message(message.chat.id, "Отримання даних...")
    try:
        response = requests.get(GOOGLE_SHEET_API_ACCESSORIES)
        response.raise_for_status()
        
        data = response.json()
        categories = data.get('categories', [])

        if not categories:
            bot.edit_message_text("На жаль, не вдалося отримати категорії з таблиці. Можливо, список порожній.", 
                                  chat_id=status_message.chat.id, 
                                  message_id=status_message.message_id)
            return

        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for category in categories:
            button_text = f"{category_icons.get(category, '')} {category}".strip()
            buttons.append(telebot.types.InlineKeyboardButton(text=button_text, callback_data=f"accessories_{category}"))
        
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                inline_keyboard.add(buttons[i], buttons[i+1])
            else:
                inline_keyboard.add(buttons[i])

        bot.edit_message_text("Оберіть категорію аксесуарів:", chat_id=status_message.chat.id, 
                              message_id=status_message.message_id, reply_markup=inline_keyboard)

    except requests.exceptions.RequestException as e:
        bot.edit_message_text(f"Виникла помилка при отриманні даних з API: {e}", 
                              chat_id=status_message.chat.id, 
                              message_id=status_message.message_id)
    except Exception as e:
        bot.edit_message_text(f"Виникла невідома помилка: {e}", 
                              chat_id=status_message.chat.id, 
                              message_id=status_message.message_id)

# --- Обробка натискання на кнопку "Плівка та скло" ---
@bot.message_handler(func=lambda message: message.text == '📱 Плівка та скло')
def handle_film_button(message):
    status_message = bot.send_message(message.chat.id, "Отримання даних...")
    try:
        response = requests.get(GOOGLE_SHEET_API_FILMS)
        response.raise_for_status()
        
        data = response.json()
        categories = data.get('categories', [])
        
        if not categories:
            bot.edit_message_text("На жаль, не вдалося отримати категорії з таблиці. Можливо, список порожній.", 
                                  chat_id=status_message.chat.id, 
                                  message_id=status_message.message_id)
            return

        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for category in categories:
            button_text = f"{category_icons.get(category, '')} {category}".strip()
            buttons.append(telebot.types.InlineKeyboardButton(text=button_text, callback_data=f"films_{category}"))
        
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                inline_keyboard.add(buttons[i], buttons[i+1])
            else:
                inline_keyboard.add(buttons[i])

        bot.edit_message_text("Оберіть категорію плівок та стекол:", chat_id=status_message.chat.id, 
                              message_id=status_message.message_id, reply_markup=inline_keyboard)
    
    except requests.exceptions.RequestException as e:
        bot.edit_message_text(f"Виникла помилка при отриманні даних з API: {e}", 
                              chat_id=status_message.chat.id, 
                              message_id=status_message.message_id)
    except Exception as e:
        bot.edit_message_text(f"Виникла невідома помилка: {e}", 
                              chat_id=status_message.chat.id, 
                              message_id=status_message.message_id)


# --- Обробка натискання на inline-кнопки ---
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_button_click(call):
    
    bot.answer_callback_query(call.id)
    status_message = bot.send_message(call.message.chat.id, "Отримання даних...")

    try:
        data_parts = call.data.split('_', 1)
        source_type = data_parts[0]
        category_name = data_parts[1]
        
        api_url = GOOGLE_SHEET_API_ACCESSORIES if source_type == 'accessories' else GOOGLE_SHEET_API_FILMS
        
        response = requests.get(f"{api_url}?category={category_name}")
        response.raise_for_status()
        
        data = response.json()
        items_data = data.get('data', [])

        if not items_data:
            bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
            bot.send_message(call.message.chat.id, f"На жаль, у категорії '{category_name}' нічого не знайдено.")
            return

        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)

        message_text_header = f"*Категорія: {category_name}*\n\n"
        bot.send_message(call.message.chat.id, message_text_header, parse_mode='Markdown')
        for item in items_data:
            link = item.get('link')
            sku = item.get('item_name')
            description = item.get('item_content')
            brand = item.get('item_brand')
            rma = item.get('rma')
            rma_text = pma_icons.get(rma, "")
            price = item.get('price')

            cleaned_description = description.replace(f"{sku}", "").replace(" :", "").replace(";", "").strip()
            if price:
                if link:
                    message_text = f"SKU: {sku}\nPRICE: {price} грн.\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **[{cleaned_description}]({link})**\n\n"
                else:
                    message_text = f"SKU: {sku}\nPRICE: {price} грн.\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **{cleaned_description}**\n\n"
            else:
                if link:
                    message_text = f"SKU: {sku}\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **[{cleaned_description}]({link})**\n\n"
                else:
                    message_text = f"SKU: {sku}\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **{cleaned_description}**\n\n"
            

            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')

    except requests.exceptions.RequestException as e:
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
        bot.send_message(call.message.chat.id, f"Виникла помилка при отриманні даних: {e}")
    except Exception as e:
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
        bot.send_message(call.message.chat.id, f"Виникла невідома помилка: {e}")

# --- Функція для запуска бота ---
def run_bot():
    while True:
        try:
            print("Бот запущено...")
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Бот не запущено... Помилка: {e}")
            time.sleep(5)

# --- Функція для запуска Flask-сервера ---
def run_flask():
    app.run(port=int(os.environ.get('PORT', 80)), host='0.0.0.0')

app = Flask(__name__)

@app.route("/")
def index():
    return send_file('src/index.html')


if __name__ == "__main__":
    # Создаем и запускаем потоки
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_bot)
    
    # Запуск потоков
    flask_thread.start()
    bot_thread.start()

    # Ожидание завершения потоков (необязательно)
    # flask_thread.join()
    # bot_thread.join()