import telebot
import os
import csv
from telebot import types
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))
file_path = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"

def get_products():
    products = []
    if not os.path.exists(file_path):
        return products
    
    file = open(file_path, mode="r", encoding="utf-8-sig", errors="ignore")
    # Читаем как обычный массив строк, а не словарь
    reader = csv.reader(file, delimiter=",")
    
    # Пропускаем первую строчку-заголовок
    next(reader, None)
    
    for row in reader:
        # Если строка пустая или в ней слишком мало колонок — пропускаем
        if not row or len(row) < 10:
            continue
            
        # Загружаем данные строго по индексам (0 — первая колонка, 1 — вторая и т.д.)
        # Если колонка отсутствует в строке, берем заглушку
        color = row[3] if len(row) > 3 else "-"
        size = row[4] if len(row) > 4 else "-"
        name = row[6] if len(row) > 6 else ""
        price = row[12] if len(row) > 12 else "0"
        photo = row[49] if len(row) > 49 else ""
        
        # Если названия нет, то это не товар — пропускаем
        if not name or str(name).isspace():
            continue

        products.append({
            "name": str(name).strip(),
            "price": str(price).strip(),
            "color": str(color).strip(),
            "size": str(size).strip(),
            "photo": str(photo).strip()
        })
        
    file.close()
    return products

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛍️ Каталог"), types.KeyboardButton("🛒 Корзина"))
    markup.add(types.KeyboardButton("ℹ️ Помощь"))
    bot.send_message(message.chat.id, "Привет! Магазин готов к работе! 👇", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🛍️ Каталог")
def catalog_btn(message):
    products = get_products()
    if not products:
        bot.send_message(message.chat.id, "Каталог пуст. Не удалось считать строки по индексам.")
        return
        
    bot.send_message(message.chat.id, f"Найдено товаров в базе: {len(products)}. Загружаю первые позиции...")
    
    for prod in products[:10]:
        caption = f"🌸 *{prod['name']}*\n\n🎨 *Цвет:* {prod['color']}\n📏 *Размер:* {prod['size']}\n💰 *Цена:* {prod['price']} грн"
        if prod['photo'] and prod['photo'].startswith("http"):
            try:
                bot.send_photo(message.chat.id, prod['photo'], caption=caption, parse_mode="Markdown")
            except:
                bot.send_message(message.chat.id, caption, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, caption, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🛒 Корзина")
def cart_btn(message):
    bot.send_message(message.chat.id, "Ваша корзина пуста.")

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_btn(message):
    bot.send_message(message.chat.id, "По вопросам пишите менеджеру.")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
