import telebot
import os
import csv
from telebot import types
from threading import Thread
from http.server import Flask, RequestHandlerServer

# 1. Создаем микро-веб-сервер для обмана Render
from flask import Flask
app = Flask('')

@app.route('/')
def home():
    return "Бот Victoria's Secret работает!"

def run_web():
    # Render автоматически передает порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. Настройка самого Telegram-бота
bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

def get_products():
    products = []
    file_path = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"
    
    if not os.path.exists(file_path):
        return products
        
    try:
        with open(file_path, mode="r", encoding="utf-8-sig", errors="ignore") as file:
            reader = csv.DictReader(file, delimiter=",")
            for row in reader:
                name = row.get("Назва")
                price = row.get("Ціна продажу") or row.get("Рекомендована ціна") or "0"
                color = row.get("Колір") or "-"
                size = row.get("Розмір") or "-"
                photo = row.get("Фото") or ""
                
                try:
                    available = int(row.get("Доступно до продажу всього", 0))
                except:
                    available = 0
                
                if not name or available <= 0:
                    continue

                products.append({
                    "name": str(name).strip(),
                    "price": str(price).strip(),
                    "color": str(color).strip(),
                    "size": str(size).strip(),
                    "photo": str(photo).strip()
                })
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        
    return products

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_catalog = types.KeyboardButton("🛍️ Каталог")
    btn_cart = types.KeyboardButton("🛒 Корзина")
    btn_help = types.KeyboardButton("ℹ️ Помощь")
    
    markup.add(btn_catalog, btn_cart)
    markup.add(btn_help)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Магазин Victoria's Secret готов к работе! Выберите нужное действие в меню ниже 👇", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    try:
        if message.text == "🛍️ Каталог":
            products = get_products()
            
            if not products:
                bot.send_message(message.chat.id, "Каталог товаров временно пуст.")
                return
                
            bot.send_message(message.chat.id, f"Найдено товаров: {len(products)}. Загружаю первые позиции...")
            
            for prod in products[:10]:
                caption = (
                    f"🌸 *{prod['name']}*\n\n"
                    f"🎨 *Цвет:* {prod['color']}\n"
                    f"📏 *Размер:* {prod['size']}\n"
                    f"💰 *Цена:* {prod['price']} грн"
                )
                
                if prod['photo'] and prod['photo'].startswith("http"):
                    try:
                        bot.send_photo(message.chat.id, prod['photo'], caption=caption, parse_mode="Markdown")
                    except:
                        bot.send_message(message.chat.id, caption, parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, caption, parse_mode="Markdown")
                    
        elif message.text == "🛒 Корзина":
            bot.send_message(message.chat.id, "Ваша корзина пока пуста.")
        elif message.text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")
    except Exception as e:
        print(f"Ошибка кнопок: {e}")

# 3. Запуск всего вместе
if __name__ == '__main__':
    # Сначала запускаем веб-сервер в отдельном потоке для Render
    t = Thread(target=run_web)
    t.start()
    
    # Затем запускаем опрос Telegram-бота
    bot.polling(none_stop=True)
            
        elif message.text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")
            
    except Exception as e:
        print(f"Ошибка при клике на кнопку: {e}")

if __name__ == '__main__':
    bot.polling(none_stop=True)
        elif message.text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    bot.polling(none_stop=True)
