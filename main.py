import telebot
import os
import csv
from telebot import types

# Подключаем токен из настроек Render
bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

# Имя твоего CSV-файла с товарами (оно точно такое же, как у файла, который ты загрузил)
CSV_FILE = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"

def get_products():
    """Бронебойная функция чтения CSV с защитой от падений и поддержкой разных кодировок"""
    products = []
    if not os.path.exists(CSV_FILE):
        return products
        
    # Пробуем сначала utf-8, если не выйдет - windows-1251
    encodings = ["utf-8", "windows-1251", "utf-8-sig"]
    
    for enc in encodings:
        try:
            with open(CSV_FILE, mode="r", encoding=enc) as file:
                sample = file.readline()
                if not sample:
                    continue
                file.seek(0)
                
                delimiter = ";" if ";" in sample else ","
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row in reader:
                    # Извлекаем данные с защитой от пустых строк
                    name = row.get("Назва") or row.get("Наименование") or "Товар Victoria's Secret"
                    price = row.get("Ціна продажу") or row.get("Рекомендована ціна") or row.get("Цена") or "0"
                    color = row.get("Колір") or row.get("Цвет") or "-"
                    size = row.get("Розмір") or row.get("Размер") or "-"
                    photo = row.get("Фото") or ""
                    
                    products.append({
                        "name": str(name).strip(),
                        "price": str(price).strip(),
                        "color": str(color).strip(),
                        "size": str(size).strip(),
                        "photo": str(photo).strip()
                    })
            # Если успешно прочитали файл — выходим из цикла кодировок
            break
        except Exception:
            # Если упало с одной кодировкой, пробуем следующую
            continue
            
    return products



@bot.message_handler(commands=['start'])
def start(message):
    # Создаем главную клавиатуру с кнопками
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
    if message.text == "🛍️ Каталог":
        products = get_products()
        
        if not products:
            bot.send_message(message.chat.id, "Каталог товаров временно пуст.")
            return
            
        bot.send_message(message.chat.id, f"Найдено доступных товаров: {len(products)}. Загружаю первые позиции...")
        
        # Выводим первые 10 товаров, чтобы не перегружать чат за раз
        for prod in products[:10]:
            caption = (
                f"🌸 *{prod['name']}*\n\n"
                f"🎨 *Цвет:* {prod['color']}\n"
                f"📏 *Размер:* {prod['size']}\n"
                f"💰 *Цена:* {prod['price']} грн"
            )
            
            # Если есть ссылка на фото в колонке "Фото", отправляем карточку с картинкой
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
        bot.send_message(message.chat.id, "По всем вопросам и для оформления заказа пишите менеджеру.")

if __name__ == '__main__':
    bot.polling(none_stop=True)
