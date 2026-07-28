import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot

# 1. Берем токен из настроек Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# 2. Простейший веб-сервер, чтобы Render не ругался на порты
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    # Render автоматически передает номер порта в переменную PORT
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

# 3. Логика вашего бота
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Магазин Victoria's Secret готов к работе!")

# 4. Запуск всего приложения
if __name__ == '__main__':
    # Запускаем веб-сервер в отдельном потоке, чтобы он не мешал боту
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    # Запускаем самого бота
    print("Bot is polling...")
    bot.infinity_polling()
