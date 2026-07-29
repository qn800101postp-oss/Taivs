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
file_path = "products.csv"

def get_products():
    products = []
    if not os.path.exists(file_path):
        return products
    
    with open(file_path, mode="r", encoding="utf-8-sig", errors="ignore") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not row.get("name"):
                continue
            products.append({
                "name": row["name"].strip(),
                "price": row["price"].strip(),
                "color": row["color"].strip(),
                "size": row["size"].strip(),
                "photo": row["photo"].strip()
            })
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
        bot.send_message(message.chat.id, "Каталог пуст.")
        return
        
    bot.send_message(message.chat.id, f"Найдено товаров в базе: {len(products)}. Загружаю каталог...")
    
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
