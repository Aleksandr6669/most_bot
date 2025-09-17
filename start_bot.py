import telebot
import requests
import os
import time

# Замініть 'YOUR_BOT_TOKEN' на токен, який ви отримали від BotFather
BOT_TOKEN = '8264718582:AAGly9dsfTerEak5GbcfGDA5lRDlOndqSbg'
# URL-адреса вашого API Google Apps Script
GOOGLE_SHEET_API_URL = 'https://script.google.com/macros/s/AKfycbzt1Hf_6copt-mWjGFzKo78lloDEYAsoDvIIN_IgAPKyyRm348g3O7e9eB5Ouh-gIlEpA/exec'

bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary mapping category names to emojis
category_icons = {
    "Навушники": "🎧",
    "Акустика": "🔊",
    "Миша комп.": "🖱️",
    "Набір посуду": "🍽️",
    "Сковорода": "🍳",
    "Клавіатура": "⌨️"
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
    keyboard.add('Аксесуари ТОП СКЮ')
    keyboard.add('Плівка та скло')
    greeting_text = (
        f"👋 Вітаю, {message.from_user.username}, в інформаційному боті магазину «Міст 1»! 👋\n\n"
        "Натисніть кнопку «Аксесуари ТОП СКЮ», щоб переглянути ТОП СКЮ аксесуарів!"
    )
    bot.send_message(message.chat.id, greeting_text, reply_markup=keyboard)

# --- Обробка натискання на кнопку "Аксесуари ТОП СКЮ" ---
@bot.message_handler(func=lambda message: message.text == 'Аксесуари ТОП СКЮ')
def handle_top_sku_button(message):
    status_message = bot.send_message(message.chat.id, "Отримання даних...")
    try:
        response = requests.get(GOOGLE_SHEET_API_URL)
        response.raise_for_status()
        
        data = response.json()
        categories = data.get('categories', [])

        if not categories:
            bot.edit_message_text("На жаль, не вдалося отримати категорії з таблиці. Можливо, список порожній.", 
                                  chat_id=status_message.chat.id, 
                                  message_id=status_message.message_id)
            return

        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2) # Вказуємо, що в одному ряду має бути 2 кнопки
        buttons = []
        for category in categories:
            button_text = f"{category_icons.get(category, '')} {category}".strip()
            buttons.append(telebot.types.InlineKeyboardButton(text=button_text, callback_data=category))
        
        # inline_keyboard.add(*buttons) # Додаємо всі кнопки одразу (не працює для row_width > 1)
        
        # Додаємо кнопки по дві в ряд
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                inline_keyboard.add(buttons[i], buttons[i+1])
            else:
                inline_keyboard.add(buttons[i]) # Додаємо останню кнопку, якщо вона одна

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
        category_name = call.data
        
        response = requests.get(f"{GOOGLE_SHEET_API_URL}?category={category_name}")
        response.raise_for_status()
        
        data = response.json()
        items_data = data.get('data', [])

        if not items_data:
            bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
            bot.send_message(call.message.chat.id, f"На жаль, у категорії '{category_name}' нічого не знайдено.")
            return

        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)

        message_text = f"*Категорія: {category_name}*\n\n"
        bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        for item in items_data:
            link = item.get('link')
            sku = item.get('item_name')
            description = item.get('item_content')
            brand = item.get('item_brand')
            rma = item.get('rma')
            rma_text = pma_icons.get(rma, "")

            cleaned_description = description.replace(f"{sku}", "").replace(" :", "").replace(";", "").strip()

            if link:
                message_text = f"SKU: {sku}\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **[{cleaned_description}]({link})**\n\n"
            else:
                message_text = f"SKU: {sku}\n*РМА: {rma_text}*\nBRAND: {brand}\nNAME: **{cleaned_description}**\n\n"

            message_text = bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')



        # message_text = f"**Категорія: {category_name}**\n\n"
        
        # for item in items_data:
        #     link = item.get('link')
        #     sku = item.get('item_name')
        #     description = item.get('item_content')
        #     brand = item.get('item_brand')

        #     cleaned_description = description.replace(f"{sku}", "").replace(" :", "").replace(";", "").strip()

        #     if link:
        #         message_text += f"SKU: {sku}\n"
        #         message_text += f"BRAND: {brand}\n"
        #         message_text += f"NAME: **[{cleaned_description}]({link})**\n\n"
        #     else:
        #         message_text += f"SKU: {sku}\n"
        #         message_text += f"BRAND: {brand}\n"
        #         message_text += f"NAME: **{cleaned_description}**\n\n"

        # bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
        # bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        bot.delete_message(chat_id=status_message.chat.id, message_id=message_text.message_id)
    
    except requests.exceptions.RequestException as e:
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
        bot.send_message(call.message.chat.id, f"Виникла помилка при отриманні даних: {e}")
    except Exception as e:
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
        bot.send_message(call.message.chat.id, f"Виникла невідома помилка: {e}")

# --- Запуск бота ---
if __name__ == "__main__":
    while True:
        try:
            print("Бот запущено...")
            bot.polling(none_stop=True)
        except:
            print("Бот не запущено...")

        time.sleep(5)