import telebot
import os
import csv
from telebot import types

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

CSV_FILE = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"

def get_products():
    products = []
    if not os.path.exists(CSV_FILE):
        return products
        
    # Пробуем открыть файл с безопасной кодировкой 'utf-8-sig' (она убирает скрытые мусорные символы Excel)
    try:
        with open(CSV_FILE, mode="r", encoding="utf-8-sig", errors="ignore") as file:
            reader = csv.DictReader(file, delimiter=",")
            for row in reader:
                # Берем названия колонок, как они написаны в твоем файле
                name = row.get("Назва") or row.get("Назва (укр)") or "Товар Victoria's Secret"
                price = row.get("Ціна продажу") or row.get("Рекомендована ціна") or "0"
                color = row.get("Колір") or "-"
                size = row.get("Розмір") or "-"
                photo = row.get("Фото") or ""
                
                # Если название пустое (пустая строка в конце файла), пропускаем
                if not name or name.isspace():
                    continue

                products.append({
                    "name": str(name).strip(),
                    "price": str(price).strip(),
                    "color": str(color).strip(),
                    "size": str(size).strip(),
                    "photo": str(photo).strip()
                })
    except Exception as e:
        print(f"Ошибка при чтении CSV: {e}")
        
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
                bot.send_message(message.chat.id, "Каталог товаров временно пуст или файл не найден ботом.")
                return
                
            bot.send_message(message.chat.id, f"Найдено товаров: {len(products)}. Загружаю первые позиции...")
            
            # Выводим первые 10 товаров
            for prod in products[:10]:
                caption = (
                    f"🌸 *{prod['name']}*\n\n"
                    f"🎨 *Цвет:* {prod['color']}\n"
                    f"📏 *Размер:* {prod['size']}\n"
                    f"💰 *Цена:* {prod['price']} грн"
                )
                
                # Проверяем ссылку на фото
                if prod['photo'] and prod['photo'].startswith("http"):
                    try:
                        bot.send_photo(message.chat.id, prod['photo'], caption=caption, parse_mode="Markdown")
                    except Exception:
                        bot.send_message(message.chat.id, caption, parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, caption, parse_mode="Markdown")
                    
        elif message.text == "🛒 Корзина":
            bot.send_message(message.chat.id, "Ваша корзина пока пуста.")
            
        elif message.text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    bot.polling(none_stop=True)
