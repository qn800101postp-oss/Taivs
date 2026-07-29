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

# Точное имя файла, как оно отображается у тебя на гитхабе
file_path = "hub_new_price_2026-07-26T19_01_28_TAIVS.xlsx - Sheet 1.csv"

# Временная корзина пользователя {chat_id: { "Название (Цвет, Размер)": {price: int, count: int} }}
user_carts = {}

def get_products_data():
    categories = {"Бюстгальтеры": {}, "Трусики": {}}
    
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден!")
        return categories
        
    with open(file_path, mode="r", encoding="utf-8-sig", errors="ignore") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames if reader.fieldnames else []
        
        # Умный поиск колонок по ключевым словам (чтобы регистр и пробелы не мешали)
        col_name = next((h for h in headers if "назв" in h.lower()), None)
        col_qty = next((h for h in headers if "доступно" in h.lower() or "залиш" in h.lower() or "кол" in h.lower()), None)
        col_price = next((h for h in headers if "ціна" in h.lower() and "продаж" in h.lower()), None) or next((h for h in headers if "ціна" in h.lower()), None)
        col_color = next((h for h in headers if "колір" in h.lower() or "цвет" in h.lower()), None)
        col_size = next((h for h in headers if "розм" in h.lower() or "размер" in h.lower()), None)
        col_photo = next((h for h in headers if "фото" in h.lower() or "картинка" in h.lower() or "лінк" in h.lower()), None)

        if not col_name:
            print("Ошибка: Колонка с названием товара не найдена.")
            return categories

        for row in reader:
            name = row.get(col_name, "")
            if not name:
                continue
            name = name.strip()
            
            # Проверяем количество (В НАЛИЧИИ)
            qty_val = row.get(col_qty, "0") if col_qty else "0"
            try:
                qty = int(float(qty_val))
            except:
                qty = 0
            if qty <= 0:
                continue # Если нет на складе, не показываем покупателю
                
            # Проверяем цену
            price_val = row.get(col_price, "0") if col_price else "0"
            price_digits = "".join(filter(str.isdigit, str(price_val)))
            price = int(price_digits) if price_digits else 0
            
            color = (row.get(col_color, "") if col_color else "-").strip()
            size = (row.get(col_size, "") if col_size else "-").strip()
            photo = (row.get(col_photo, "") if col_photo else "").strip()
            
            # Разделение по категориям
            name_lower = name.lower()
            if "бюстгальтер" in name_lower or "bra" in name_lower:
                cat = "Бюстгальтеры"
            else:
                cat = "Трусики"
                
            # Убираем код в скобках из названия, чтобы сгруппировать дубли в одну карточку
            model_base = name.split(" (")[0].strip()
            
            if model_base not in categories[cat]:
                categories[cat][model_base] = {
                    "name": model_base,
                    "price": price,
                    "photo": photo,
                    "colors": {}
                }
                
            if color not in categories[cat][model_base]["colors"]:
                categories[cat][model_base]["colors"][color] = {
                    "sizes": set(),
                    "photo": photo # Привязываем конкретное фото к цвету
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
    
    # Показываем первые 15 уникальных моделей
    for idx, (m_id, prod) in enumerate(list(products.items())[:15]):
        desc = f"🌸 *{prod['name']}*\n💰 *Цена:* {prod['price']} грн\n\nВ наличии:\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for color, c_data in prod["colors"].items():
            available_sizes = ", ".join(sorted(list(c_data["sizes"])))
            desc += f"▪️ {color} (Размеры: {available_sizes})\n"
            
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
    _, price, m_idx, color = call.data.split("_")
    
    cat_name = "Бюстгальтеры" if "Бюстгальтер" in call.message.caption else "Трусики"
    data = get_products_data()
    products = list(data.get(cat_name, {}).values())
    
    try:
        prod = products[int(m_idx)]
    except:
        bot.send_message(call.message.chat.id, "Ошибка. Откройте каталог заново.")
        return
        
    exact_color = None
    for c in prod["colors"].keys():
        if c.startswith(color):
            exact_color = c
            break
            
    if not exact_color:
        bot.send_message(call.message.chat.id, "Цвет не найден.")
        return
        
    c_data = prod["colors"][exact_color]
    
    # Меняем фото на соответствующее выбранному цвету, если они отличаются
    if c_data["photo"] and c_data["photo"].startswith("http") and c_data["photo"] != prod["photo"]:
        try:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=types.InputMediaPhoto(c_data["photo"], caption=call.message.caption, parse_mode="Markdown")
            )
        except:
            pass

    # Кнопки размеров strictly те, которые есть в наличии
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for size in sorted(list(c_data["sizes"])):
        cb_cart = f"cart_{price}_{exact_color[:10]}_{size}_{prod['name'][:15]}"
        buttons.append(types.InlineKeyboardButton(f"📏 {size}", callback_data=cb_cart))
        
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 Назад к цветам", callback_data=f"showcat_{cat_name}"))
    
    bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали цвет: *{exact_color}*.\nКакой размер добавить в корзину?", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cart_"))
def add_to_cart(call):
    _, price, color, size, name_part = call.data.split("_")
    
    chat_id = call.message.chat.id
    full_item_name = f"{name_part}... ({color}, разм. {size})"
    
    if chat_id not in user_carts:
        user_carts[chat_id] = {}
        
    if full_item_name not in user_carts[chat_id]:
        user_carts[chat_id][full_item_name] = {"price": int(price), "count": 1}
    else:
        user_carts[chat_id][full_item_name]["count"] += 1
        
    bot.answer_callback_query(call.id, f"Добавлено в корзину!")
    bot.send_message(chat_id, f"🛍️ Товар *{full_item_name}* добавлен в корзину!", parse_mode="Markdown")

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
    bot.send_message(chat_id, "✨ Спасибо за заказ! Менеджер свяжется с вами в ближайшее время.")
    user_carts[chat_id] = {}

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_btn(message):
    bot.send_message(message.chat.id, "По всем вопросам пишите менеджеру.")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    bot.polling(none_stop=True)
