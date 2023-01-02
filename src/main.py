from database import Database
import logging
from dotenv import load_dotenv
from os import getenv,makedirs
from os.path import isfile,isdir,dirname
import schedule
from time import sleep
import telebot
from threading import Thread


##?## ------------------------------ VARIABLES ------------------------------ ##?##

load_dotenv()
RESOURCES_PATH = "./resources/"
DATABASE_PATH = "./resources/database.json"
UPDATES_PATH = "./resources/updates.txt"
SCHEDULED_TIME_THREAD = "14:00"
#UPDATING = False
USER_ID = ""
bot:telebot.TeleBot
db = Database()
if (isfile(".env")):
    USER_ID = getenv("MY_ID")
    bot = telebot.TeleBot(getenv("TOKEN"))


##?## ------------------------------ LOGGING ------------------------------ ##?##


def logger_init() -> logging.Logger:
    logging.basicConfig(filename="bot.log",filemode="w",format="%(asctime)s %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

def log(message:telebot.types.Message,logger:logging.Logger) -> None:
    log_msg = (
        "{" + str(message.from_user.first_name) +
        ((" "+str(message.from_user.last_name)) if message.from_user.last_name is not None else "") +
        ", id="+str(message.from_user.id)+"} > "+
        str(message.text)
    )
    print("~> "+log_msg)
    logger.info(log_msg)

logger = logger_init()


##?## ------------------------------ FUNCTIONS ------------------------------ ##?##

def firstRun() -> bool:
    flag = False
    if (not isdir(RESOURCES_PATH)):
        makedirs(dirname(RESOURCES_PATH),exist_ok=True)
        flag = True
    if (not isfile(DATABASE_PATH)):
        with open(DATABASE_PATH,"x",encoding='utf-8') as new_db:
            new_db.write(str(dict()))
        flag = True
    if (not isfile(UPDATES_PATH)):
        with open(UPDATES_PATH,"x",encoding='utf-8') as new_txt:
            new_txt.write("")
        flag = True
    if (not isfile(".env")):
        with open(".env","x",encoding='utf-8') as new_env:
            new_env.write(f"TOKEN = \"\"\nMY_ID = \"\"")
        flag = True
    return flag

def cleanTxtFile(path:str) -> None:
    with open(path,"w",encoding='utf-8') as txt:
        txt.write("")

def dailyUpdate(user_id:str=USER_ID) -> None:
    db.read(DATABASE_PATH)
    cleanTxtFile(UPDATES_PATH)
    for id in db.database.keys():
        db.database[id].updatePrices()
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

def updateRoutine() -> None:
    while True:
        schedule.run_pending()
        sleep(60)


"""
#! DO NOT USE UNTIL AUX FUNCTIONS GET WRITTEN
def rescheduleUpdate(scheduled_time:str,user_id:str) -> None:
    schedule.clear()
    SCHEDULED_TIME_THREAD = scheduled_time
    schedule.every().day.at(SCHEDULED_TIME_THREAD).do(dailyUpdate,user_id,allWatchlists)
    print("~> Daily update rescheduled at "+scheduled_time)
    logger.info("Daily update rescheduled at "+scheduled_time)
"""





##?## ------------------------------ BOT ROUTES ------------------------------ ##?##

def checkUser(chat_id:str) -> bool:
    return chat_id == USER_ID

def command_switch(message:telebot.types.Message) -> bool:
    switcher = {
        "/start":start,
        "/addWatchlist":addWatchlist,
        "/removeWatchlist":removeWatchlist,
        "/addProduct":addProduct,
        "/removeProduct":removeProduct
    }
    if (message.text in switcher.keys()):
        switcher.get(message.text)(message)
        return True
    return False



@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    if (str(message.from_user.id) != USER_ID):
        bot.send_message(chat_id=USER_ID,text=f"User {message.from_user.id} ({message.from_user.first_name}) tried to connect to this bot")
        log(message,logger)
        #print(f"User_id = {str(message['from']['id'])}\nChat_id = {str(message['chat']['id'])}")
        return
    else:
        bot.send_message(chat_id=USER_ID,text=f"Hi {message.from_user.first_name}")



@bot.message_handler(commands=['addWatchlist'])
def addWatchlist(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    new_msg = bot.send_message(chat_id=USER_ID,text="Name of the watchlist to be created? (64 characters max, unique)")
    bot.register_next_step_handler(message=new_msg,callback=addWatchlist_step_1)

def addWatchlist_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    wl_id = message.text
    if (len(wl_id) > 64):
        bot.send_message(chat_id=USER_ID,text="Invalid name: it is longer than 64 characters")
        return
    if (wl_id in db.database.keys()):
        bot.send_message(chat_id=USER_ID,text=f"Watchlist \"{wl_id}\" already exists!")
        return
    db.addWatchlist(wl_id)
    new_msg = bot.send_message(chat_id=USER_ID,text="Do you want to set a target price for this watchlist? (Number if affirmative, \"No\") otherwise")
    bot.register_next_step_handler(message=new_msg,callback=addWatchlist_step_2,args=(wl_id))

def addWatchlist_step_2(message:telebot.types.Message,id:str) -> None:
    if command_switch(message): return
    targetPrice = str(message.text)
    if (targetPrice in ["No","no"]):
        db.write(DATABASE_PATH)
    elif (targetPrice.replace('.','',1).isdigit()):
        db.database[id].editTargetPrice(float(targetPrice))
        db.write(DATABASE_PATH)
    else:
        bot.send_message(chat_id=USER_ID,text=f"{targetPrice} is not a valid answer")
        return
    final_msg = bot.send_message(chat_id=USER_ID,text=f"Watchlist \"{id}\" created!")
    log(final_msg,logger)



@bot.message_handler(commands=['removeWatchlist'])
def removeWatchlist(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1,one_time_keyboard=True,selective=False)
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(chat_id=USER_ID,text="Which watchlist do you want to remove?",reply_markup=keyboard)
    bot.register_next_step_handler(message=new_msg,callback=removeWatchlist_step_1)

def removeWatchlist_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    del_id = message.text
    db.removeWatchlist(del_id)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(chat_id=USER_ID,text=f"Watchlist \"{del_id}\" removed!")
    log(final_msg,logger)



@bot.message_handler(commands=['addProduct'])
def addProduct(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1,one_time_keyboard=True,selective=False)
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(chat_id=USER_ID,text="Add product to which watchlist?",reply_markup=keyboard)
    bot.register_next_step_handler(message=new_msg,callback=addProduct_step_1)

def addProduct_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    add_id = message.text
    new_msg = bot.send_message(chat_id=USER_ID,text="Product URL:")
    bot.register_next_step_handler(message=new_msg,callback=addProduct_step_2,args=(add_id))

def addProduct_step_2(message:telebot.types.Message,id:str) -> None:
    if command_switch(message): return
    url = str(message.text)
    if (not url.startswith("https://")):
        bot.send_message(chat_id=USER_ID,text=f"Invalid URL: {url}")
        return
    new_msg = bot.send_message(chat_id=USER_ID,text="Product name (optional, 64 characters max):")
    bot.register_next_step_handler(message=new_msg,callback=addProduct_step_3,args=(id,url))

def addProduct_step_3(message:telebot.types.Message,id:str,url:str) -> None:
    if command_switch(message): return
    name = message.text
    if (len(name) > 64):
        bot.send_message(chat_id=USER_ID,text="Invalid name: name longer than 64 characters")
        return
    if (len(name) == 0): name = None
    db.database[id].addProduct(url,name)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(chat_id=USER_ID, text=f"\"{name if name is not None else 'Product'}\" added to watchlist \"{id}\"!")
    log(final_msg,logger)



@bot.message_handler(commands=['removeProduct'])
def removeProduct(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1,one_time_keyboard=True,selective=False)
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(chat_id=USER_ID,text="Remove product from which watchlist?",reply_markup=keyboard)
    bot.register_next_step_handler(message=new_msg,callback=removeProduct_step_1)

def removeProduct_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    del_id = message.text
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1,one_time_keyboard=True,selective=False)
    for prod in db.database[del_id].products:
        keyboard.add(prod.name if prod.name is not None else prod.fullName)
    new_msg = bot.send_message(chat_id=USER_ID,text="Remove which product?",reply_markup=keyboard)
    bot.register_next_step_handler(message=new_msg,callback=removeProduct_step_2,args=(del_id))

def removeProduct_step_2(message:telebot.types.Message,id:str) -> None:
    if command_switch(message): return
    name = message.text
    db.database[id].removeProduct(name)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(chat_id=USER_ID,text=f"{name} removed from watchlist \"{id}\"!")
    log(final_msg,logger)



@bot.message_handler(commands=['listAll'])
def listAll(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    bot.send_message(chat_id=USER_ID,text=str(db))



@bot.message_handler(commands=['update'])
def update(message:telebot.types.Message) -> None:
    if not checkUser(str(message.from_user.id)): return
    log(message,logger)
    dailyUpdate(USER_ID)












##?## ------------------------------ MAIN ------------------------------ ##?##

if (__name__ == "__main__"):

    if firstRun():
        print("All needed files created, make sure to fill the .env file and run again to start\n")
        exit(0)
    
    print("Jaf's AWS (Amazon Web Scraper) Telegram bot started\n")
    logger.info("Jaf's AWS (Amazon Web Scraper) server started")

    if (isfile(DATABASE_PATH)): db.read(DATABASE_PATH)

    schedule.every().day.at(SCHEDULED_TIME_THREAD).do(dailyUpdate,USER_ID)
    dailyUpdateThread = Thread(target=updateRoutine,args=())

    dailyUpdateThread.start()
    bot.infinity_polling()



 

    
    
    

    




    