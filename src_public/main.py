from AWSDatabase import AWSDatabase, UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException, WatchlistDuplicateException, ProductNotFoundException, EmptyProfileException, EmptyWatchlistException
import logging
from dotenv import load_dotenv
from sys import argv
from os import getenv,makedirs
from os.path import isfile,isdir,dirname
import schedule
from time import sleep
import telebot
import threading
from typing import Tuple



##?## ------------------------------ VARIABLES ------------------------------ ##?##



load_dotenv()
RESOURCES_PATH = "./resources/"
SCHEDULED_TIME = "14:00"
#UPDATING = False

bot = telebot.TeleBot(getenv("TOKEN"))
db = AWSDatabase(int(getenv("ADMIN_ID")),RESOURCES_PATH)



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
        ", id="+str(message.from_user.id)+"} -> "+
        "{" + str(message.chat.first_name) +
        ((" "+str(message.chat.last_name)) if message.chat.last_name is not None else "") +
        ", id="+str(message.chat.id)+"}\n" +
        str(message.text)+"\n"
    )
    print(log_msg)
    logger.info(log_msg)

logger = logger_init()



##?## ------------------------------ FUNCTIONS ------------------------------ ##?##


def askAdminAuthUser(user_id:int, user_firstName:str) -> None:
    keyboard = telebot.util.quick_markup({
        "Yes": {"callback_data":f"yes:{user_id}"},
        "No": {"callback_data":f"no:{user_id}"}
    }, row_width=2
    )
    bot.send_message(
        chat_id=db.adminId,
        text=f"User {user_firstName} ({user_id}) has asked for authorization to use AWS Bot. Authorize?",
        reply_markup=keyboard
    )

@bot.callback_query_handler() #TODO: func filter???
def adminAuthResponse(query:telebot.types.CallbackQuery) -> None:
    if (query.from_user.id != db.adminId): return
    res,user_id = query.data.split(':')
    if (res == "yes"):
        db.addUser(user_id)
        sent = bot.send_message(chat_id=user_id,text="You have been authorized to use this bot! :)")
        log(sent,logger)
    elif (res == "no"):
        sent = bot.send_message(chat_id=user_id,text="You have not been authorized to use this bot :(")
        log(sent,logger)



def firstRun() -> bool:
    flag = False
    if (not isdir(RESOURCES_PATH)):
        makedirs(dirname(RESOURCES_PATH),exist_ok=True)
        flag = True
    if (not isfile(".env")):
        with open(".env","x",encoding='utf-8') as new_env:
            new_env.write(f"TOKEN = \"\"\nADMIN_ID = \"\"")
        flag = True
    return flag



def dailyUpdate(user_id:int) -> None:
    msg = db.updateWatchlists(user_id)
    if (msg == ""): return
    sent = bot.send_message(chat_id=user_id,text=msg,reply_markup=telebot.types.ReplyKeyboardRemove())
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



def command_switch(message:telebot.types.Message) -> bool:
    switcher = {
        "/start":start,
        "/addwatchlist":addwatchlist,
        "/removewatchlist":removewatchlist,
        "/addproduct":addproduct,
        "/removeproduct":removeproduct,
        "/listall":listall,
        "/update":update,
        "/auth":auth
    }
    if (message.text in switcher.keys()):
        switcher.get(message.text)(message)
        return True
    return False



def userNotAuthorizedException_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text="Error: it seems like you are not an authorized user :("
    )
    log(sent,logger)

def userNotFoundError_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: user \"{user_id}\" not found!"
    )
    log(sent,logger)

def watchlistNotFoundException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: watchlist \"{wl_name}\" not found!"
    )
    log(sent,logger)

def watchlistDuplicateException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: watchlist \"{wl_name}\" already exists!"
    )
    log(sent,logger)

def productNotFoundException_message(user_id:int, prod_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: product \"{prod_name}\" not found!"
    )
    log(sent,logger)

def emptyProfileException_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text="Error: you have no watchlists yet!\nTry creating one with /addwatchlist"
    )
    log(sent,logger)

def emptyWatchlistException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: watchlist {wl_name} has no products!\nAdd one with /addproduct"
    )
    log(sent,logger)

def unknownError_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text="Unknown error: something went wrong!"
    )
    log(sent,logger)



##?## ------------------------------ BOT ROUTES ------------------------------ ##?##



#? START

@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    sender_id = message.from_user.id
    if (sender_id == db.adminId):
        bot.send_message(
            chat_id=db.adminId,
            text="Hi Jaf :)",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
    else:
        msg = f"Hi {message.from_user.first_name}"
        if (sender_id not in db.authorizedUsers):
            msg += "\nUse the command /auth to ask for the authorization to use this bot"
        bot.send_message(
            chat_id=sender_id,
            text=msg,
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
    log(message,logger)



#? ADDWATCHLIST

@bot.message_handler(commands=['addwatchlist'])
def addwatchlist(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    sender_id = message.from_user.id
    new_msg = bot.send_message(
        chat_id=sender_id,
        text="Name of the watchlist to be created? (64 characters max, unique)",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(message,logger)
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_1,args=(sender_id))

def addwatchlist_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    sender_id = args
    wl_name = message.text
    if (len(wl_name) > 64):
        bot.send_message(chat_id=sender_id,text="Invalid name: it is longer than 64 characters")
        return
    new_msg = bot.send_message(chat_id=sender_id,text="Do you want to set a target price for this watchlist? (Number if yes, \"No\") otherwise")
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_2,args=(sender_id,wl_name))

def addwatchlist_step_2(message:telebot.types.Message,args:Tuple[int,str]) -> None:
    if command_switch(message): return
    sender_id = args[0]
    wl_name = args[1]
    targetPrice = message.text
    if (targetPrice in ["No","no"]):
        targetPrice = None
    elif (targetPrice.replace('.','',1).isdigit()):
        targetPrice = float(targetPrice)
    else:
        bot.send_message(chat_id=sender_id,text=f"{targetPrice} is not a valid answer")
        return
    try:
        db.addWatchlist(sender_id,wl_name,targetPrice)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except WatchlistDuplicateException:
        watchlistDuplicateException_message(sender_id,wl_name)
        return
    except:
        unknownError_message(sender_id)
        return
    final_msg = bot.send_message(chat_id=sender_id,text=f"Watchlist \"{wl_name}\" created!")
    log(final_msg,logger)



#? REMOVEWATCHLIST

@bot.message_handler(commands=['removewatchlist'])
def removewatchlist(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    sender_id = message.from_user.id
    try:
        wl_names = db.getWatchlists(sender_id)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except EmptyProfileException:
        emptyProfileException_message(sender_id)
        return
    except:
        unknownError_message(sender_id)
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(
        row_width=1,
        one_time_keyboard=True,
        selective=True,
        resize_keyboard=True
    )
    for wl_name in wl_names: keyboard.add(wl_name)
    new_msg = bot.send_message(
        chat_id=sender_id,
        text="Which watchlist do you want to remove?",
        reply_markup=keyboard
    )
    log(message,logger)
    bot.register_next_step_handler(message=new_msg,callback=removewatchlist_step_1,args=(sender_id))

def removewatchlist_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    sender_id = args
    wl_name = message.text
    try:
        db.removeWatchlist(sender_id,wl_name)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except WatchlistNotFoundException:
        watchlistNotFoundException_message(sender_id,wl_name)
        return
    except:
        unknownError_message(sender_id)
        return
    final_msg = bot.send_message(
        chat_id=sender_id,
        text=f"Watchlist \"{wl_name}\" removed!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(final_msg,logger)

#TODO: from here

#? ADDPRODUCT

@bot.message_handler(commands=['addproduct'])
def addproduct(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addwatchlist")
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
    if (not url.startswith("https://") or (not ("amazon" in url) and (not ("amzn" in url)))):
        bot.send_message(chat_id=USER_ID,text=f"Invalid URL: {url}\nMake sure to paste an Amazon URL")
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
    if (message.from_user.is_bot): return
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(chat_id=USER_ID,text="You don't have any watchlists yet! Create one first using /addwatchlist")
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
    if (len(db.database[del_id].products) == 0):
        bot.send_message(chat_id=USER_ID, text=f"Watchlist {del_id} is empty!")
        return
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
    if (message.from_user.is_bot): return
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    if (len(db.database.keys()) == 0):
        bot.send_message(
            chat_id=USER_ID,
            text="You don't have any watchlists yet! Create one first using /addwatchlist",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        return
    bot.send_message(chat_id=USER_ID,text=str(db),reply_markup=telebot.types.ReplyKeyboardRemove())



#? UPDATE

@bot.message_handler(commands=['update'])
def update(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    dailyUpdate(USER_ID)



#? AUTH

@bot.message_handler(commands=['cmd'])
def cmd(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    if (not checkUser(str(message.from_user.id))): return
    log(message,logger)
    msg = (
        "Command list of this bot:\n\n"
        "/addwatchlist\n"
        "/removewatchlist\n"
        "/addproduct\n"
        "/removeproduct\n"
        "/listall\n"
        "/update"
    )
    bot.send_message(chat_id=USER_ID,text=msg,reply_markup=telebot.types.ReplyKeyboardRemove())










##?## ------------------------------ MAIN ------------------------------ ##?##

if (__name__ == "__main__"):

    if firstRun():
        print("All needed files and folders created, make sure to fill the .env file and run again to start\n")
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



 

    
    
    

    




    