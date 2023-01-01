from database import Database
from typing import Dict
from json import load
import logging
from dotenv import load_dotenv
from os import getenv,listdir
from os.path import isfile,join
from sys import argv
import schedule
from time import sleep
from telebot import TeleBot
from threading import Thread
from queue import Queue


##?## ------------------------------ VARIABLES ------------------------------ ##?##

load_dotenv()
DATABASE_PATH = "./resources/database.json"
UPDATES_PATH = "./resources/updates.txt"
#SCHEDULED_TIME_MAIN = "13:50"
SCHEDULED_TIME_THREAD = "14:00"
UPDATING = False
USER_ID = getenv("MY_ID")
bot = TeleBot(__name__)
db = Database()


##?## ------------------------------ LOGGING ------------------------------ ##?##


def logger_init() -> logging.Logger:
    logging.basicConfig(filename="bot.log",filemode="w",format="%(asctime)s %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

def log(message:dict,logger:logging.Logger) -> None:
    log_msg = (
        "{" + str(message['from']['first_name']) +
        ((" "+str(message['from']['last_name'])) if 'last_name' in message['from'].keys() else "") +
        ", id="+str(message['from']['id'])+"} > "+
        str(message['text'])
    )
    print("~> "+log_msg)
    logger.info(log_msg)

logger = logger_init()


##?## ------------------------------ FUNCTIONS ------------------------------ ##?##

def cleanTxtFile(path:str) -> None:
    with open(path,"w",encoding='utf-8') as txt:
        txt.write("")

def dailyUpdate(user_id:str, threadQueue:Queue) -> None:
    db.read(DATABASE_PATH)
    cleanTxtFile(UPDATES_PATH)
    for id,wl in db.database.items():
        wl.updatePrices()
    msg = "Some of your watchlists have been updated!\n"
    updated_ids = []
    with open(UPDATES_PATH,"r",encoding='utf-8') as updates_txt:
        updated_ids = updates_txt.readlines()
    for id in updated_ids:
        id = id.strip()
        msg += (id+":\n") + str(db.database[id])
    if (msg == "Some of your watchlists have been updated!\n"): return
    sent = bot.send_message(chat_id=user_id,text=msg)
    log(sent,logger)


#! DO NOT USE, MAIN THREAD HAS TO POLL BOT REQUESTS
def dailyUpdateMainThread(allWatchlists:Dict[str,Watchlist],threadQueue:Queue) -> None:
    for id in allWatchlists.keys():
        allWatchlists[id].updatePrices()
    threadQueue.put(allWatchlists)


#! DO NOT USE UNTIL AUX FUNCTIONS GET WRITTEN
def rescheduleUpdate(scheduled_time:str,user_id:str) -> None:
    schedule.clear()
    SCHEDULED_TIME_THREAD = scheduled_time
    schedule.every().day.at(SCHEDULED_TIME_THREAD).do(dailyUpdate,user_id,allWatchlists)
    print("~> Daily update rescheduled at "+scheduled_time)
    logger.info("Daily update rescheduled at "+scheduled_time)


def updateRoutine() -> None:
    while True:
        schedule.run_pending()
        sleep(60)



##?## ------------------------------ BOT ROUTES ------------------------------ ##?##

@bot.message_handler(commands=['start'])
def start(message:dict) -> None:
    if (str(message['from']['id']) != USER_ID):
        bot.send_message(chat_id=USER_ID,text=f"User {message['from']['id']} ({message['from']['first_name']}) tried to connect to this bot")
        log(message,logger)
        #print(f"User_id = {str(message['from']['id'])}\nChat_id = {str(message['chat']['id'])}")
        return
    else:
        bot.send_message(chat_id=USER_ID,text=f"Hi {message['from']['first_name']}")


@bot.message_handler(commands=['addProduct'])
def addProduct(message:dict) -> None:
    pass


@bot.message_handler(commands=['removeProduct'])
def removeProduct(message:dict) -> None:
    pass


@bot.message_handler(commands=['addWatchlist'])
def addWatchlist(message:dict) -> None:
    pass


@bot.message_handler(commands=['removeWatchlist'])
def removeWatchlist(message:dict) -> None:
    pass










##?## ------------------------------ MAIN ------------------------------ ##?##

if (__name__ == "__main__"):
    
    bot.config['api_key'] = getenv("TOKEN")    

    print("Jaf's AWS (Amazon Web Scraper) Telegram bot started\n")
    logger.info("Jaf's AWS (Amazon Web Scraper) server started")

    if (isfile(DATABASE_PATH)): db.read(DATABASE_PATH)

    schedule.every().day.at(SCHEDULED_TIME_THREAD).do(dailyUpdate,USER_ID,threadQueue)
    dailyUpdateThread = Thread(target=updateRoutine,args=())

    dailyUpdateThread.start()
    bot.infinity_polling()



 

    
    
    

    




    