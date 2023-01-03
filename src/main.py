from database import Database
import logging
from dotenv import load_dotenv
from sys import argv
from os import getenv,makedirs
from os.path import isfile,isdir,dirname
import schedule
from time import sleep
import telebot
import threading



##?## ------------------------------ VARIABLES ------------------------------ ##?##



load_dotenv()
RESOURCES_PATH = "./resources/"
DATABASE_PATH = "./resources/database.json"
UPDATES_PATH = "./resources/updates.txt"
SCHEDULED_TIME = "14:00"
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


def cleanUpdatesFile(path:str) -> None:
    with open(path,"w",encoding='utf-8') as txt:
        txt.write("")


def dailyUpdate(user_id:str=USER_ID) -> None:
    db.read(DATABASE_PATH)
    cleanUpdatesFile(UPDATES_PATH)
    for id in db.database.keys():
        db.database[id].updatePrices()
    msg = "Some of your watchlists have been updated!\n"
    updated_ids = []
    with open(UPDATES_PATH,"r",encoding='utf-8') as updates_txt:
        updated_ids = updates_txt.readlines()
    for id in updated_ids:
        id = id.strip()
        msg += str(db.database[id])
    if (msg == "Some of your watchlists have been updated!\n"):
        msg = "Your watchlists have no relevant updates"
    sent = bot.send_message(chat_id=user_id,text=msg)
    log(sent,logger)


def updateRoutine() -> None:
    while True:
        schedule.run_pending()
        sleep(60)


def isValidTime(t:str) -> bool:
    return (
        (len(t) == 5) and
        (t.count(':') == 1) and
        (t.replace(':','',1).isdecimal()) and
        (int(t[:2]) <= 23) and
        (int(t[3:]) <= 59)
    )


"""
#! DO NOT USE UNTIL AUX FUNCTIONS GET WRITTEN
def rescheduleUpdate(scheduled_time:str,user_id:str) -> bool:
    if (not isValidTime(scheduled_time)): return False
    schedule.clear()
    schedule.every().day.at(scheduled_time).do(dailyUpdate,user_id)
    print("~> Daily update rescheduled at "+scheduled_time)
    logger.info("Daily update rescheduled at "+scheduled_time)
"""


def checkUser(chat_id:str) -> bool:
    return chat_id == USER_ID


def command_switch(message:telebot.types.Message) -> bool:
    switcher = {
        "/start":start,
        "/addwatchlist":addwatchlist,
        "/removewatchlist":removewatchlist,
        "/addproduct":addproduct,
        "/removeproduct":removeproduct,
        "/listall":listall,
        "/update":update,
        "/cmd":cmd
    }
    if (message.text in switcher.keys()):
        switcher.get(message.text)(message)
        return True
    return False



##?## ------------------------------ BOT ROUTES ------------------------------ ##?##



#? START

@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))):
        bot.send_message(chat_id=USER_ID,text=f"User {message.from_user.id} ({message.from_user.first_name}) tried to connect to this bot")
        log(message,logger)
        return
    else:
        bot.send_message(chat_id=USER_ID,text=f"Hi {message.from_user.first_name}")
        log(message,logger)



#? ADDWATCHLIST

@bot.message_handler(commands=['addwatchlist'])
def addwatchlist(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    new_msg = bot.send_message(chat_id=USER_ID,text="Name of the watchlist to be created? (64 characters max, unique)")
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_1)

def addwatchlist_step_1(message:telebot.types.Message) -> None:
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
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_2,args=(wl_id))

def addwatchlist_step_2(message:telebot.types.Message,args:str) -> None:
    if command_switch(message): return
    targetPrice = str(message.text)
    if (targetPrice in ["No","no"]):
        db.write(DATABASE_PATH)
    elif (targetPrice.replace('.','',1).isdigit()):
        db.database[args].editTargetPrice(float(targetPrice))
        db.write(DATABASE_PATH)
    else:
        db.removeWatchlist(args[0])
        bot.send_message(chat_id=USER_ID,text=f"{targetPrice} is not a valid answer")
        return
    final_msg = bot.send_message(chat_id=USER_ID,text=f"Watchlist \"{args}\" created!")
    log(final_msg,logger)



#? REMOVEWATCHLIST

@bot.message_handler(commands=['removewatchlist'])
def removewatchlist(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(
        row_width=1,
        one_time_keyboard=True,
        selective=True,
        resize_keyboard=True
    )
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(
        chat_id=USER_ID,
        text="Which watchlist do you want to remove?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=removewatchlist_step_1)

def removewatchlist_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    del_id = message.text
    db.removeWatchlist(del_id)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(
        chat_id=USER_ID,
        text=f"Watchlist \"{del_id}\" removed!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(final_msg,logger)



#? ADDPRODUCT

@bot.message_handler(commands=['addproduct'])
def addproduct(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(
        row_width=1,
        one_time_keyboard=True,
        selective=True,
        resize_keyboard=True
    )
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(
        chat_id=USER_ID,
        text="Add product to which watchlist?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_1)

def addproduct_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    add_id = message.text
    new_msg = bot.send_message(
        chat_id=USER_ID,
        text="Product URL:",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_2,args=(add_id))

def addproduct_step_2(message:telebot.types.Message,args:str) -> None:
    if command_switch(message): return
    url = str(message.text)
    if (not url.startswith("https://")):
        bot.send_message(chat_id=USER_ID,text=f"Invalid URL: {url}")
        return
    new_msg = bot.send_message(chat_id=USER_ID,text="Product name (optional, 64 characters max):")
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_3,args=(args,url))

def addproduct_step_3(message:telebot.types.Message,args:tuple) -> None:
    if command_switch(message): return
    name = message.text
    if (len(name) > 64):
        bot.send_message(chat_id=USER_ID,text="Invalid name: name longer than 64 characters")
        return
    if (name in ["No","no"]): name = None
    db.database[args[0]].addProduct(args[1],name)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(chat_id=USER_ID, text=f"\"{name if name is not None else 'Product'}\" added to watchlist \"{args[0]}\"!")
    log(final_msg,logger)



#? REMOVEPRODUCT

@bot.message_handler(commands=['removeproduct'])
def removeproduct(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(
        row_width=1,
        one_time_keyboard=True,
        selective=True,
        resize_keyboard=True
    )
    for id in db.database.keys(): keyboard.add(id)
    new_msg = bot.send_message(
        chat_id=USER_ID,
        text="Remove product from which watchlist?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=removeproduct_step_1)

def removeproduct_step_1(message:telebot.types.Message) -> None:
    if command_switch(message): return
    del_id = message.text
    keyboard = telebot.types.ReplyKeyboardMarkup(
        row_width=1,
        one_time_keyboard=True,
        selective=True,
        resize_keyboard=True
    )
    for prod in db.database[del_id].products:
        keyboard.add(prod.name if prod.name is not None else prod.fullName)
    new_msg = bot.send_message(
        chat_id=USER_ID,
        text="Remove which product?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=removeproduct_step_2,args=(del_id))

def removeproduct_step_2(message:telebot.types.Message,args:str) -> None:
    if command_switch(message): return
    name = message.text
    db.database[args].removeProduct(name)
    db.write(DATABASE_PATH)
    final_msg = bot.send_message(
        chat_id=USER_ID,
        text=f"{name} removed from watchlist \"{args}\"!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(final_msg,logger)



#? LISTALL

@bot.message_handler(commands=['listall'])
def listall(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addWatchlist")
        return
    bot.send_message(chat_id=USER_ID,text=str(db))



#? UPDATE

@bot.message_handler(commands=['update'])
def update(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    dailyUpdate(USER_ID)



#? CMD

@bot.message_handler(commands=['cmd'])
def cmd(message:telebot.types.Message) -> None:
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    msg = (
        "Command list of this bot:\n\n"
        "/addWatchlist\n"
        "/removeWatchlist\n"
        "/addProduct\n"
        "/removeProduct\n"
        "/listAll\n"
        "/update"
    )
    bot.send_message(chat_id=USER_ID,text=msg)










##?## ------------------------------ MAIN ------------------------------ ##?##

if (__name__ == "__main__"):

    if firstRun():
        print("All needed files created, make sure to fill the .env file and run again to start\n")
        exit(0)

    if (len(argv) > 1):
        if (argv[1] in ["--help","-h"]):
            print(
                "Optional arguments of main.py:\n"
                "<scheduledTime>: the time of day at which the bot sends its daily update, formatted as HH:MM\n"
            )
            exit(0)
        if (isValidTime(argv[1])):
            SCHEDULED_TIME = argv[1]

    if (isfile(DATABASE_PATH)): db.read(DATABASE_PATH)

    schedule.every().day.at(SCHEDULED_TIME).do(dailyUpdate,USER_ID)
    dailyUpdateThread = threading.Thread(target=updateRoutine)

    print("Jaf's AWS (Amazon Web Scraper) Telegram bot started\n")
    logger.info("Jaf's AWS (Amazon Web Scraper) server started")

    dailyUpdateThread.start()
    bot.infinity_polling()



 

    
    
    

    




    