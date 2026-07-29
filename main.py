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

# Временная корзина в памяти бота (в реальном проекте лучше БД, но для старта отлично)
# Структура: {chat_id: {product_name: {price: int, count: int}}}
user_carts = {}

def get_grouped_products():
    """Считывает CSV и группирует товары по категориям и уникальным моделям"""
    categories = {
        "Бюстгальтеры": {},
        "Трусики": {}
    }
    
    if not os.path.exists(file_path):
        return categories
        
    with open(file_path, mode="r", encoding="utf-8-sig", errors="ignore") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
                
            price = row.get("price", "0").strip()
            color = row.get("color", "-").strip()
            size = row.get("size", "-").strip()
            photo = row.get("photo", "").strip()
            
            # Определяем категорию по ключевым словам в названии
            name_lower = name.lower()
            if "бюстгальтер" in name_lower:
                cat = "Бюстгальтеры"
            elif "трусики" in name_lower or "стрінги" in name_lower or "шортики" in name_lower:
                cat = "Трусики"
            else:
                continue # Если не подошло, пропускаем
                
            # Базовая очистка имени от размеров для группировки в одну модель
            # Убираем размер в скобках в конце, если он есть
            model_name = name.split(" (")[0]
            
            if model_name not in categories[cat]:
                categories[cat][model_name] = {
                    "name": model_name,
                    "price": price,
                    "photos": [photo] if photo else [],
                    "variants": {} # {Цвет: [Размеры]}
                }
            
            # Добавляем фото, если такого еще нет (на случай если захочешь указать несколько через запятую)
            if photo and photo not in categories[cat][model_name]["photos"]:
                # Если в будущем в ячейку запишешь ссылки через запятую, этот код их разделит:
                for p in photo.split(","):
                    p_clean = p.strip()
                    if p_clean and p_clean not in categories[cat][model_name]["photos"]:
                        categories[cat][model_name]["photos"].append(p_clean)
            
            if color not in categories[cat][model_name]["variants"]:
                categories[cat][model_name]["variants"][color] = set()
                
            categories[cat][model_name]["variants"][color].add(size)
            
    return categories

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛍️ Каталог"), types.KeyboardButton("🛒 Корзина"))
    markup.add(types.KeyboardButton("ℹ️ Помощь"))
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в магазин белья Victoria's Secret! 🌸\nВыберите интересующий раздел ниже 👇", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🛍️ Каталог")
def catalog_btn(message):
    # Создаем инлайн-кнопки для выбора категорий
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👙 Бюстгальтеры", callback_data="cat_Бюстгальтеры"),
        types.InlineKeyboardButton("🩲 Трусики", callback_data="cat_Трусики")
    )
    bot.send_message(message.chat.id, "Выберите категорию товара:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def show_category_products(call):
    category_name = call.data.split("_")[1]
    data = get_grouped_products()
    products = data.get(category_name, {})
    
    if not products:
        bot.send_message(call.message.chat.id, f"В категории {category_name} пока нет товаров.")
        return
        
    bot.send_message(call.message.chat.id, f"Загружаю товары из категории: {category_name}...")
    
    # Показываем первые 10 уникальных моделей, чтобы не спамить лимиты Telegram
    count = 0
    for model_id, prod in products.items():
        if count >= 10:
            break
            
        # Формируем текст с доступными цветами и размерами
        variants_text = ""
        for color, sizes in prod["variants"].items():
            variants_text += f"🎨 *Цвет:* {color} — 📏 *Размеры:* {', '.join(sorted(list(sizes)))}\n"
            
        caption = f"🌸 *{prod['name']}*\n\n{variants_text}\n💰 *Цена:* {prod['price']} грн"
        
        # Инлайн-кнопка для покупки этой модели
        # Передаем усеченное имя в callback (лимит 64 символа)
        callback_buy = f"buy_{count}" 
        # Сохраним полное имя в сессию, чтобы кнопка знала, что покупают
        # Для упрощения передаем индекс модели
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"buy_{prod['price']}_{prod['name'][:30]}"))
        
        photos = prod["photos"]
        
        # Если фото несколько, отправляем первую, остальные можно будет листать 
        # (Либо отправляем одну главную карточку, чтобы не перегружать чат)
        if photos and photos[0].startswith("http"):
            try:
                bot.send_photo(call.message.chat.id, photos[0], caption=caption, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
            
        count += 1

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def add_to_cart(call):
    # Разбираем данные клика: buy_цена_название
    parts = call.data.split("_")
    price = parts[1]
    prod_name = parts[2]
    
    chat_id = call.message.chat.id
    if chat_id not in user_carts:
        user_carts[chat_id] = {}
        
    if prod_name not in user_carts[chat_id]:
        user_carts[chat_id][prod_name] = {"price": int(price), "count": 1}
    else:
        user_carts[chat_id][prod_name]["count"] += 1
        
    bot.answer_callback_query(call.id, f"Добавлено: {prod_name}")
    bot.send_message(chat_id, f"🛍️ Товар *{prod_name}...* добавлен в корзину!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🛒 Корзина")
def cart_btn(message):
    chat_id = message.chat.id
    cart = user_carts.get(chat_id, {})
    
    if not cart:
        bot.send_message(chat_id, "Ваша корзина пуста. Загляните в 🛍️ Каталог!")
        return
        
    cart_text = "🛒 *Ваша корзина:*\n\n"
    total_sum = 0
    
    for item_name, info in cart.items():
        item_sum = info["price"] * info["count"]
        total_sum += item_sum
        cart_text += f"▪️ *{item_name}...*\n  {info['count']} шт. х {info['price']} грн = {item_sum} грн\n"
        
    cart_text += f"\n💰 *Итого к оплате:* {total_sum} грн"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"))
    markup.add(types.InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_cart"))
    
    bot.send_message(chat_id, cart_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def clear_cart_callback(call):
    chat_id = call.message.chat.id
    if chat_id in user_carts:
        user_carts[chat_id] = {}
    bot.answer_callback_query(call.id, "Корзина очищена")
    bot.send_message(chat_id, "🗑️ Ваша корзина успешно очищена.")

@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def checkout_callback(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "✨ Спасибо за заказ! Менеджер свяжется с вами в ближайшее время для подтверждения.")
    # Очищаем корзину после заказа
    user_carts[chat_id] = {}

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_btn(message):
    bot.send_message(message.chat.id, "По всем вопросам заказа, доставки и подбора размеров пишите менеджеру.")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
