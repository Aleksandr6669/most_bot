import os
import threading
import time
import json
import base64
import datetime

from flask import Flask, send_file
import telebot
import requests
from groq import Groq

from dotenv import load_dotenv
load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# URL-адреси вашого API Google Apps Script
GOOGLE_SHEET_API_ACCESSORIES = 'https://script.google.com/macros/s/AKfycbzt1Hf_6copt-mWjGFzKo78lloDEYAsoDvIIN_IgAPKyyRm348g3O7e9eB5Ouh-gIlEpA/exec'
GOOGLE_SHEET_API_FILMS = 'https://script.google.com/macros/s/AKfycbwxXf15evwxyGu_0eC2kFHdWnHw3jLS8jEkKgJZjO3mPl7COmGUUGlrKq2uDRqsIy5bAw/exec'
GOOGLE_SHEET_API_WRITE_CHECK_DATA = 'https://script.google.com/macros/s/AKfycbwfyAkC52RoI-CbHiGDi2-ncQEv-RxcCQYfygbDuF8gYTXYxinA3P4IgSWMCzVFqmAJaw/exec'
GOOGLE_SHEET_API_GET_INSTRUCTIONS = 'https://script.google.com/macros/s/AKfycbzFbS6Jwpbuy3VEEaKhuzGHLT9ZC5f4MpOaqw5h9LjAHSAh3K1Ms9vVw6GXARkRz7Gm/exec'

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

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
def get_system_prompt():
    default_prompt = "Тебе нужно в json\nsky - это код товара \nname - название товара \nint - количество товара \nprice - общая цена \nrole - main_product или accessories или services"
    try:
        response = requests.get(GOOGLE_SHEET_API_GET_INSTRUCTIONS, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success' and data.get('instruction'):
            print("Успішно завантажено інструкцію з Google Sheets.")
            print(data['instruction'])
            return data['instruction']
        else:
            print("Не вдалося отримати інструкцію з Google Sheets, використовуючи резервну.")
            return default_prompt
    except requests.exceptions.RequestException as e:
        print(f"Помилка при завантаженні інструкції: {e}. Використовую резервну.")
        return default_prompt

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

@bot.message_handler(content_types=['photo'])
def handle_photo_echo(message):
    status_message = bot.reply_to(message, "Отримав фото. Оброблюю...")

    try:
        # Отримання системної інструкції
        system_prompt = get_system_prompt()

        photo_id = message.photo[-1].file_id
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_string = base64.b64encode(downloaded_file).decode('utf-8')

        IMAGE_DATA_URL = f"data:image/jpeg;base64,{base64_string}"

        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Розпізнай цей чек."},
                        {
                            "type": "image_url",
                            "image_url": { "url": IMAGE_DATA_URL }
                        }
                    ]
                }
            ],
            temperature=0.5,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
            stop=None
        )

        raw_response_text = completion.choices[0].message.content
        
        try:
            json_str = raw_response_text.split("```json")[1].split("```")[0].strip()
            parsed_json = json.loads(json_str)
            
            # --- ПЕРЕКЛАД РОЛЕЙ ---
            role_translations = {
                "main_product": "Основний товар",
                "accessories": "Аксесуар",
                "services": "Послуга"
            }
            translated_check_data = []
            for item in parsed_json:
                translated_item = item.copy()
                original_role = translated_item.get('role', '')
                translated_item['role'] = role_translations.get(original_role, original_role)
                translated_check_data.append(translated_item)
            # -----------------------

            # --- ВІДПРАВКА ДАНИХ В GOOGLE SHEETS ---
            try:
                bot.send_message(message.chat.id, "Розпізнано. Відправляю дані в таблицю...")
                
                now = datetime.datetime.now()
                payload = {
                    "telegram_id": message.from_user.id,
                    "telegram_username": message.from_user.username,
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "check_data": translated_check_data
                }

                headers = {'Content-Type': 'application/json'}
                response = requests.post(GOOGLE_SHEET_API_WRITE_CHECK_DATA, headers=headers, data=json.dumps(payload))
                response.raise_for_status()
                bot.send_message(message.chat.id, "✅ Дані успішно записано в таблицю.")
            except requests.exceptions.RequestException as e:
                bot.send_message(message.chat.id, f"🔴 Помилка при записі даних в таблицю: {e}")
            # ----------------------------------------

            # # Формуємо текстове повідомлення з даних
            # final_text = "**Розпізнані дані:**\n\n"
            # for i, item in enumerate(translated_check_data, 1):
            #     final_text += f"**Товар {i}:**\n"
            #     name = str(item.get('name', '-')).replace('*', '').replace('_', '')
            #     sky = str(item.get('sky', '-')).replace('*', '').replace('_', '')
            #     item_type = str(item.get('type', '-')).replace('*', '').replace('_', '')
            #     quantity = str(item.get('int', '-')).replace('*', '').replace('_', '')
            #     price = str(item.get('price', '-')).replace('*', '').replace('_', '')
            #     role = str(item.get('role', '-')).replace('*', '').replace('_', '')
            #     final_text += f"Назва: {name}\n"
            #     final_text += f"Код: {sky}\n"
            #     final_text += f"Тип: {item_type}\n"
            #     final_text += f"К-сть: {quantity}\n"
            #     final_text += f"Ціна: {price}\n"
            #     final_text += f"Роль: {role}\n\n"

            # bot.edit_message_text(
            #     chat_id=status_message.chat.id,
            #     message_id=status_message.message_id,
            #     text=final_text,
            #     parse_mode='Markdown'
            # )

        except (IndexError, json.JSONDecodeError) as e:
            bot.edit_message_text(
                chat_id=status_message.chat.id,
                message_id=status_message.message_id,
                text=f"Не вдалося витягти JSON з відповіді моделі. Помилка: {e}\n\n**Оригінальна відповідь:**\n{raw_response_text}"
            )

    except Exception as e:
        bot.edit_message_text(
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
            text=f"Виникла помилка під час обробки фото: {e}"
        )


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
