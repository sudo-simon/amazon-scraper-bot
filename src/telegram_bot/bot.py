import logging
from dotenv import load_dotenv
from os import getenv
from json import load
from telebot import TeleBot
import schedule
from time import sleep
load_dotenv()


JSON_PATH = "/home/jaf/Repos/amazon-scraper-bot/src/resources/updates.json"
SCHEDULED_TIME = "14:00"
bot = TeleBot(__name__)
USER_ID = getenv("MY_ID")


logging.basicConfig(filename="bot.log",filemode="w",format="%(asctime)s %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log(message,logger:logging.Logger) -> None:
    log_msg = (
        "{" + str(message['from']['first_name']) +
        ((" "+str(message['from']['last_name'])) if 'last_name' in message['from'].keys() else "") +
        ", id="+str(message['from']['id'])+"} > "+
        str(message['text'])
    )
    print("~> "+log_msg)
    logger.info(log_msg)



@bot.route("/start")
def start(message) -> None:
    if (message['from']['is_bot']):
        log(message,logger)
        return
    log(message,logger)
    if (str(message['from']['id']) != USER_ID):
        print(f"User_id = {str(message['from']['id'])}\nChat_id = {str(message['chat']['id'])}")
    else:
        print("Hi creator ("+USER_ID+")")



def getUpdatesMessage() -> str:
    jsonObj = None
    with open(JSON_PATH,"r",encoding='utf-8') as update_file:
        jsonObj = load(update_file)
    updated = jsonObj.get("updates")
    diff = float(jsonObj.get("difference"))

    out = ""
    for prod in updated:
        out += (
            f"{prod.get('name')}: {prod.get('price')} €\n({prod.get('url')})\n"
        )
    out += f"\nDifference: {diff} €" if len(updated) > 0 else ""
    return out

def scheduledMessage() -> None:
    updatesText = getUpdatesMessage()
    if (len(updatesText) == 0): return
    text = "Some products have price updates!\n"+updatesText
    bot.send_message(chat_id=USER_ID,text=text)
    log("Update message sent!",logger)




if __name__ == "__main__":

    print("Jaf's AWS (Amazon Web Scraper) Telegram bot started\n")
    logger.info("Jaf's AWS (Amazon Web Scraper) server started")
    bot.config['api_key'] = getenv("TOKEN")

    #bot.poll()

    schedule.every().day.at(SCHEDULED_TIME).do(scheduledMessage)
    while True:
        schedule.run_pending()
        sleep(30)

    
