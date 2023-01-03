import telebot


################################
# PUT YOUR TELEGRAM TOKEN HERE #
################################
TOKEN = ""


bot = telebot.TeleBot(TOKEN)
@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    my_id = message.from_user.id
    bot.send_message(chat_id=my_id,text=f"Request received from user: {message.from_user.first_name}\nTelegram ID: {my_id}")
    print(f"User_id = {str(message.from_user.id)}\nChat_id = {str(message.chat.id)}")


if __name__ == "__main__":
    print("Go on Telegram and send a \"/start\" command to your bot")
    bot.infinity_polling()
