import telebot

# Fill this field with the token you get from Telegram's BotFather
MY_TOKEN = ""

bot = telebot.TeleBot(MY_TOKEN)
@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    my_id = message.from_user.id
    bot.send_message(chat_id=my_id,text=f"User {my_id} ({message.from_user.first_name}) tried to connect to this bot")
    print(f"User_id = {str(message.from_user.id)}\nChat_id = {str(message.chat.id)}")


if __name__ == "__main__":
    bot.infinity_polling()
