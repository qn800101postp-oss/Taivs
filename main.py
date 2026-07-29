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

# Указываем твой оригинальный файл, который ты загружал
file_path = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"

# Корзина: {chat_id: { "Название (Цвет, Размер)": {price: int, count: int} }}
user_carts = {}

def get_products_data():
    """
    Считывает оригинальный CSV файл. 
    Группирует строго по моделям, учитывая только товары в наличии (>0).
    """
    categories = {"Бюстгальтеры": {}, "Трусики": {}}
    
    if not os.path.exists(file_path):
        return categories
        
    with open(file_path, mode="r", encoding="utf-8-sig", errors="ignore") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Проверяем наличие колонки имени
            name = row.get("Назва", "") or row.get("Назва (укр)", "")
            if not name:
                continue
            name = name.strip()
            
            # Проверяем реальный остаток товара
            try:
                qty = int(row.get("Доступно до продажу всього", 0))
            except:
                qty = 0
                
            if qty <= 0:
                continue # Пропускаем, если нет в наличии
                
            # Определяем цену
            price = row.get("Ціна продажу", "") or row.get("Рекомендована ціна", "0")
            price = "".join(filter(str.isdigit, str(price)))
            price = int(price) if price else 0
            
            color = (row.get("Колір", "") or "-").strip()
            size = (row.get("Розмір", "") or "-").strip()
            photo = (row.get("Фото", "") or "").strip()
            
            # Фильтр по категориям
            name_lower = name.lower()
            if "бюстгальтер" in name_lower or "bra" in name_lower:
                cat = "Бюстгальтеры"
            elif any(k in name_lower for k in ["трусики", "стрінги", "шортики", "thong", "panty", "танга", "чікі"]):
                cat = "Трусики"
            else:
                cat = "Трусики" # Дефолтная категория для белья, если не определилось явно
                
            # Группируем базовое имя модели (до скобок с артикулом)
            model_base = name.split(" (")[0].strip()
            
            if model_base not in categories[cat]:
                categories[cat][model_base] = {
                    "name": model_base,
                    "price": price,
                    "photo": photo,
                    "colors": {} # { Цвет: { "sizes": set(), "photo": str } }
                }
                
            if color not in categories[cat][model_base]["colors"]:
                categories[cat][model_base]["colors"][color] = {
                    "sizes": set(),
                    "photo": photo # Привязываем фото к конкретному цвету
                }
                
            categories[cat][model_base]["colors"][color]["sizes"].add(size)
            
    return categories

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛍️ Каталог"), types.KeyboardButton("🛒 Корзина"))
    markup.add(types.KeyboardButton("ℹ️ Помощь"))
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в магазин Victoria's Secret! 🌸\nВыберите интересующий раздел ниже 👇", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🛍️ Каталог")
def catalog_btn(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👙 Бюстгальтеры", callback_data="showcat_Бюстгальтеры"),
        types.InlineKeyboardButton("🩲 Трусики", callback_data="showcat_Трусики")
    )
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("showcat_"))
def show_category(call):
    cat_name = call.data.split("_")[1]
    data = get_products_data()
    products = data.get(cat_name, {})
    
    if not products:
        bot.send_message(call.message.chat.id, f"В категории {cat_name} сейчас нет товаров в наличии.")
        return
        
    bot.send_message(call.message.chat.id, f"✨ Доступные модели в категории {cat_name}:")
    
    # Выводим уникальные модели
    for idx, (m_id, prod) in enumerate(list(products.items())[:15]):
        # Собираем общее описание того, что вообще есть для ознакомления
        desc = f"🌸 *{prod['name']}*\n💰 *Цена:* {prod['price']} грн\n\nВ наличии:\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for color, c_data in prod["colors"].items():
            available_sizes = ", ".join(sorted(list(c_data["sizes"])))
            desc += f"▪️ {color} (Размеры: {available_sizes})\n"
            
            # Кнопка выбора конкретного цвета
            # Кодируем в callback: csel_[индекс_категории_или_усеченное_имя]
            # Чтобы не выйти за лимиты 64 байт, передаем усеченные параметры
            cb_data = f"csel_{prod['price']}_{idx}_{color[:15]}"
            markup.add(types.InlineKeyboardButton(f"🎨 Выбрать цвет: {color}", callback_data=cb_data))
            
        if prod["photo"] and prod["photo"].startswith("http"):
            try:
                bot.send_photo(call.message.chat.id, prod["photo"], caption=desc, reply_markup=markup, parse_mode="Markdown")
            except:
                bot.send_message(call.message.chat.id, desc, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, desc, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("csel_"))
def color_selected(call):
    # Разбираем: csel_цена_индексМодели_цвет
    _, price, m_idx, color = call.data.split("_")
    
    # Нам нужно найти эту модель повторно в базе
    # Для этого определим, в какой категории мы находимся (по тексту сообщения)
    cat_name = "Бюстгальтеры" if "Бюстгальтер" in call.message.caption else "Трусики"
    data = get_products_data()
    products = list(data.get(cat_name, {}).values())
    
    try:
        prod = products[int(m_idx)]
    except:
        bot.send_message(call.message.chat.id, "Ошибка выбора товара. Попробуйте открыть каталог заново.")
        return
        
    # Ищем точное совпадение цвета (так как мы его обрезали для callback)
    exact_color = None
    for c in prod["colors"].keys():
        if c.startswith(color):
            exact_color = c
            break
            
    if not exact_color:
        bot.send_message(call.message.chat.id, "Цвет не найден.")
        return
        
    c_data = prod["colors"][exact_color]
    
    # Меняем фото на то, которое соответствует выбранному цвету (если оно отличается)
    if c_data["photo"] and c_data["photo"].startswith("http") and c_data["photo"] != prod["photo"]:
        try:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=types.InputMediaPhoto(c_data["photo"], caption=call.message.caption, parse_mode="Markdown")
            )
        except:
            pass

    # Создаем кнопки с размерами, которые ЕСТЬ В НАЛИЧИИ для этого цвета
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for size in sorted(list(c_data["sizes"])):
        # callback: cart_цена_цвет_размер_кусокНазвания
        cb_cart = f"cart_{price}_{exact_color[:10]}_{size}_{prod['name'][:15]}"
        buttons.append(types.InlineKeyboardButton(f"📏 {size}", callback_data=cb_cart))
        
    markup.add(*buttons)
    # Добавляем кнопку возврата
    markup.add(types.InlineKeyboardButton("🔙 Назад к цветам", callback_data=f"showcat_{cat_name}"))
    
    bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали цвет: *{exact_color}*.\nКакой размер добавить в корзину?", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cart_"))
def add_to_cart(call):
    # Разбираем: cart_цена_цвет_размер_название
    _, price, color, size, name_part = call.data.split("_")
    
    chat_id = call.message.chat.id
    full_item_name = f"{name_part}... ({color}, размер {size})"
    
    if chat_id not in user_carts:
        user_carts[chat_id] = {}
        
    if full_item_name not in user_carts[chat_id]:
        user_carts[chat_id][full_item_name] = {"price": int(price), "count": 1}
    else:
        user_carts[chat_id][full_item_name]["count"] += 1
        
    bot.answer_callback_query(call.id, f"Добавлено в корзину!")
    bot.send_message(chat_id, f"🛍️ Товар *{full_item_name}* успешно добавлен в корзину!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🛒 Корзина")
def cart_btn(message):
    chat_id = message.chat.id
    cart = user_carts.get(chat_id, {})
    
    if not cart:
        bot.send_message(chat_id, "Ваша корзина пуста. Выберите что-нибудь в 🛍️ Каталоге!")
        return
        
    cart_text = "🛒 *Ваша корзина:*\n\n"
    total_sum = 0
    
    for item_name, info in cart.items():
        item_sum = info["price"] * info["count"]
        total_sum += item_sum
        cart_text += f"▪️ *{item_name}*\n  {info['count']} шт. х {info['price']} грн = {item_sum} грн\n"
        
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
    bot.send_message(chat_id, "✨ Спасибо за заказ! Менеджер свяжется с вами в ближайшее время для подтверждения заказа и уточнения деталей доставки.")
    user_carts[chat_id] = {}

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_btn(message):
    bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
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
