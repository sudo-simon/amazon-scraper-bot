from watchlist import Watchlist
from typing import Dict
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
RESOURCES_PATH = "./resources/"
#SCHEDULED_TIME_MAIN = "13:50"
SCHEDULED_TIME_THREAD = "14:00"
UPDATING = False
bot = TeleBot(__name__)
USER_ID = getenv("MY_ID")


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

def loadWatchlists(resources_path:str=RESOURCES_PATH) -> Dict[str,Watchlist]:
    allWatchlists = dict()
    watchlists_paths = [path for path in listdir(resources_path) if (isfile(join(resources_path,path)) and path.endswith("_watchlist.json"))]
    for path in watchlists_paths:
        new_watchlist = Watchlist("",json_path=path)
        allWatchlists[new_watchlist.id] = new_watchlist
    return allWatchlists


def updateThreadQueue(allWatchlists:Dict[str,Watchlist],threadQueue:Queue) -> None:
    try:
        threadQueue.get(block=False)
    except:
        pass
    threadQueue.put(allWatchlists,block=True,timeout=None)


def addWatchlistServer(allWatchlists:Dict[str,Watchlist],threadQueue:Queue,id:str,targetPrice:float=None) -> int:
    if (id in allWatchlists.keys()): return -1
    new_watchlist = Watchlist(id,targetPrice)
    allWatchlists[id] = new_watchlist
    updateThreadQueue(allWatchlists,threadQueue)
    return 0


def removeWatchlistServer(allWatchlists:Dict[str,Watchlist],id:str) -> int:
    if (id not in allWatchlists.keys()): return -1
    allWatchlists.pop(id)
    return 0


def dailyUpdate(user_id:str, threadQueue:Queue) -> None:
    allWatchlists:Dict[str,Watchlist] = {}
    try:
        allWatchlists = threadQueue.get()
    except:
        return
    msg = "Some of your watchlists have been updated!\n"
    for id in allWatchlists.keys():
        diff = allWatchlists[id].updatePrices()
        if ((diff >= 5.0) or (allWatchlists[id].total <= allWatchlists[id].targetPrice)):
            msg += (id+":\n") + str(allWatchlists[id])
    if (msg == "Some of your watchlists have been updated!\n"): return
    sent = bot.send_message(chat_id=user_id,text=msg)
    log(sent,logger)
    threadQueue.put(allWatchlists)

    #TODO: remake with json _update.json files being the readable database (listdir function)


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

    allWatchlists = loadWatchlists()

    threadQueue = Queue(maxsize=1)
    dailyUpdateThread = Thread(target=updateRoutine,args=())
    schedule.every().day.at(SCHEDULED_TIME_THREAD).do(dailyUpdate,USER_ID,threadQueue)

    try:
        if (len(argv) > 1):
            json_file = str(argv[1])
            list_id = json_file.split('/')[1].split('_')[0]
            init_watchlist = Watchlist(list_id)
            init_watchlist.loadFromJson(json_file)
            allWatchlists[init_watchlist.id] = init_watchlist
    except:
        print("Make sure your initial json file to load has a name similar to <list_id>_watchlist.json and is placed in resources/")
        exit(1)
    
    threadQueue.put(allWatchlists)

    bot.infinity_polling()
    dailyUpdateThread.start()



 

    
    
    

    




    