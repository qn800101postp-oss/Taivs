import os
import telebot
from telebot import types
import json

# Для теста вставьте ваш токен в кавычках вместо всей строки os.environ.get
TOKEN = os.environ.get('BOT_TOKEN', 'СЮДА_МОЖНО_ВСТАВИТЬ_ТОКЕН_ДЛЯ_ТЕСТА') 
bot = telebot.TeleBot(TOKEN)

# Ваша рабочая ссылка на магазин
WEB_APP_URL = "https://qn800101postp-oss.github.io/Taivs/" 

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app = types.WebAppInfo(WEB_APP_URL)
    btn = types.KeyboardButton(text="🛍️ Открыть магазин", web_app=web_app)
    markup.add(btn)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Добро пожаловать в Victoria's Secret.\n\nНажми на кнопку ниже, чтобы открыть каталог товаров:", 
        reply_markup=markup
    )

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    try:
        data = json.loads(message.web_app_data.data)
        order_text = "🛍️ Новый заказ в магазине!\n\n"
        for item in data['items']:
            order_text += f"• {item['name']} — {item['price']} ₴\n"
        order_text += f"\n💰 Итого к оплате: {data['total']} ₴"
        bot.send_message(message.chat.id, order_text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при обработке заказа.")

if name == 'main':
    print("Бот успешно запущен!")
    bot.polling(none_stop=True)
