import telebot
from telebot import types
import requests, os
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()

# Змінна для збереження стану користувача
user_data = {}

# Ваш токен бота
TOKEN = os.getenv('telegram_key')  # Замініть на ваш токен

# Ваш API ключ для конвертації
API_KEY = os.getenv('api')  # Замініть на ваш API ключ

# Створення об'єкта бота
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://tele-check.onrender.com/' + TOKEN)  # Replace with your Render app name!
    return "Webhook set!", 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привіт! Я допоможу конвертувати валюту. Спочатку виберіть валюту, яку хочете конвертувати:",
        reply_markup=currency_keyboard()
    )

def currency_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("USD", callback_data="from_USD"),
        types.InlineKeyboardButton("EUR", callback_data="from_EUR")
    )
    markup.add(
        types.InlineKeyboardButton("UAH", callback_data="from_UAH"),
        types.InlineKeyboardButton("GBP", callback_data="from_GBP")
    )
    markup.add(
        types.InlineKeyboardButton("Інша валюта", callback_data="from_another")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "from_another")
def currency_another(call):
    bot.edit_message_text(
        "Напишіть свою валюту (наприклад, USD, EUR, UAH).",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.register_next_step_handler(call.message, handle_custom_currency)

def currency_keyboard_for_to():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("USD", callback_data="to_USD"),
        types.InlineKeyboardButton("EUR", callback_data="to_EUR")
    )
    markup.add(
        types.InlineKeyboardButton("UAH", callback_data="to_UAH"),
        types.InlineKeyboardButton("GBP", callback_data="to_GBP")
    )
    markup.add(
        types.InlineKeyboardButton("Інша валюта", callback_data="to_another")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith('from_'))
def currency_from(call):
    currency = call.data.split("_")[1]
    user_data[call.from_user.id] = {"from_currency": currency}
    bot.edit_message_text(
        f"Ви вибрали {currency}. Тепер введіть суму для конвертації:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.message_handler(func=lambda message: message.text.replace('.', '', 1).isdigit())
def handle_amount(message):
    user_id = message.from_user.id
    if user_id in user_data and "from_currency" in user_data[user_id]:
        amount = float(message.text)
        user_data[user_id]["amount"] = amount
        bot.send_message(
            message.chat.id,
            "Тепер виберіть валюту, в яку хочете конвертувати:",
            reply_markup=currency_keyboard_for_to()
        )
    else:
        bot.send_message(message.chat.id, "Спочатку виберіть валюту командою /start.")

@bot.callback_query_handler(func=lambda call: call.data == "to_another")
def currency_to_another(call):
    bot.edit_message_text(
        "Напишіть код валюти, в яку хочете конвертувати (наприклад, USD, EUR, JPY).",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.register_next_step_handler(call.message, handle_custom_currency_to)

@bot.callback_query_handler(func=lambda call: call.data.startswith('to_'))
def currency_to(call):
    currency = call.data.split("_")[1]
    user_id = call.from_user.id
    
    if user_id in user_data and "amount" in user_data[user_id]:
        from_currency = user_data[user_id]["from_currency"]
        amount = user_data[user_id]["amount"]
        converted_amount = convert_currency(from_currency, currency, amount)
        
        bot.edit_message_text(
            f"{amount} {from_currency} = {converted_amount} {currency}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.edit_message_text(
            "Спочатку виберіть валюту командою /start.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )


def convert_currency(from_currency, to_currency, amount):
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200 and "conversion_result" in data:
        return round(data['conversion_result'], 2)
    else:
        return "Помилка отримання курсу"


def handle_custom_currency(message):
    user_id = message.from_user.id
    custom_currency = message.text.strip().upper()
    
    if len(custom_currency) == 3 and custom_currency.isalpha():
        user_data[user_id] = {"from_currency": custom_currency}
        bot.send_message(
            message.chat.id,
            f"Ви вибрали {custom_currency}. Тепер введіть суму для конвертації."
        )
    else:
        bot.send_message(
            message.chat.id,
            "Невідомий код валюти. Введіть міжнародний 3-літерний код (наприклад, USD, EUR, JPY)."
        )

def handle_custom_currency_to(message):
    user_id = message.from_user.id
    custom_currency = message.text.strip().upper()
    
    if len(custom_currency) == 3 and custom_currency.isalpha():
        from_currency = user_data[user_id]["from_currency"]
        amount = user_data[user_id]["amount"]
        converted_amount = convert_currency(from_currency, custom_currency, amount)
        bot.send_message(
            message.chat.id,
            f"{amount} {from_currency} = {converted_amount} {custom_currency}"
        )
    else:
        bot.send_message(
            message.chat.id,
            "Невідомий код валюти. Введіть міжнародний 3-літерний код (наприклад, USD, EUR, JPY)."
        )

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)