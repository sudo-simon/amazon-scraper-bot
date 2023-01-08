from AWSDatabase import AWSDatabase, UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException, WatchlistDuplicateException, ProductNotFoundException, EmptyProfileException, EmptyWatchlistException, BadAmazonProductException
import logging
from dotenv import load_dotenv
from sys import argv
from os import getenv,makedirs
from os.path import isfile,isdir,dirname
import schedule
from time import sleep
import telebot
import threading
from typing import Tuple,List



##?## ------------------------------ VARIABLES ------------------------------ ##?##



load_dotenv()
RESOURCES_PATH = "./resources/"
SCHEDULED_TIME = "13:00"
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

def addPendingRequest(user_id:int) -> int:
    userExists = False
    with open(db.txtPath,"r+",encoding='utf-8') as pending_txt:
        pending = [int(line.strip()) for line in pending_txt.readlines()]
        if (user_id in pending): userExists = True
        else: pending_txt.writelines([str(user_id)])
    if (userExists): return -1
    return 0

def removePendingRequest(user_id:int) -> int:
    userExists = True
    pending = []
    with open(db.txtPath,"r",encoding='utf-8') as pending_txt:
        pending = [int(line.strip()) for line in pending_txt.readlines()]
        if (user_id not in pending): userExists = False
        else: pending.remove(user_id)
    if(not userExists): return -1
    with open(db.txtPath,"w",encoding='utf-8') as pending_txt:
        pending_txt.writelines([str(pending_id) for pending_id in pending])
    return 0




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
    

@bot.callback_query_handler(func=(lambda query: query.data[:4] == "yes:"))
def adminAuthResponse_yes(query:telebot.types.CallbackQuery) -> None:
    if (query.from_user.id != db.adminId): return
    res,user_id = query.data.split(':')
    user_id = int(user_id)
    if (res == "yes"):
        if (db.addUser(user_id) == -1):
            sent = bot.send_message(chat_id=db.adminId,text="User already in the database! Unexpected anomaly :(")
            log(sent,logger)
            return
        sent = bot.send_message(chat_id=user_id,text="You have been authorized to use this bot! :)")
        log(sent,logger)
        removePendingRequest(user_id)
        bot.delete_message(chat_id=db.adminId,message_id=query.message.id)
        bot.send_message(chat_id=db.adminId,text="User authorized!",reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        sent = bot.send_message(chat_id=db.adminId,text="Unexpected callback query behaviour!")
        log(sent,logger)

@bot.callback_query_handler(func=(lambda query: query.data[:3] == "no:"))
def adminAuthResponse_no(query:telebot.types.CallbackQuery) -> None:
    if (query.from_user.id != db.adminId): return
    res,user_id = query.data.split(':')
    user_id = int(user_id)
    if (res == "no"):
        sent = bot.send_message(chat_id=user_id,text="You have not been authorized to use this bot :(")
        log(sent,logger)
        removePendingRequest(user_id)
        bot.delete_message(chat_id=db.adminId,message_id=query.message.id)
        bot.send_message(chat_id=db.adminId,text="User not authorized!",reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        sent = bot.send_message(chat_id=db.adminId,text="Unexpected callback query behaviour!")
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



def dailyUpdate() -> None:
    db.loadDb()

    for user_id in db.authorizedUsers:
        tmp_msg = bot.send_message(chat_id=user_id,text=f"Automatic daily update running...")
        try:
            msg = db.updateWatchlists(user_id)
        except UserNotAuthorizedException:
            userNotAuthorizedException_message(user_id)
            return
        except UserNotFoundError:
            userNotFoundError_message(user_id)
            return
        except:
            unknownError_message(user_id)
            return
        bot.delete_message(chat_id=user_id,message_id=tmp_msg.id)
        sent = bot.send_message(chat_id=user_id,text=(msg if msg != "" else "You have no updates"),reply_markup=telebot.types.ReplyKeyboardRemove())
        log(sent,logger)

    tmp_msg = bot.send_message(chat_id=db.adminId,text=f"Automatic daily update running...")
    try:
        msg = db.updateWatchlists(db.adminId)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(db.adminId)
        return
    except UserNotFoundError:
        userNotFoundError_message(db.adminId)
        return
    except:
        unknownError_message(db.adminId)
        return
    bot.delete_message(chat_id=db.adminId,message_id=tmp_msg.id)
    sent = bot.send_message(chat_id=db.adminId,text=(msg if msg != "" else "You have no updates"),reply_markup=telebot.types.ReplyKeyboardRemove())
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
        text="Error: it seems like you are not an authorized user :(",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    print(f"DEBUGGONE: userNotAuthorizedException\nauthUsers = {str(db.authorizedUsers)}")
    bot.send_message(
        chat_id=user_id,
        text=f"Ciao bb, se ti arriva questo messaggio me lo dici please?\nQuesta è la lista degli utenti autorizzati che ho in memoria: {str(db.authorizedUsers)}"
    )
    log(sent,logger)

def userNotFoundError_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: user \"{user_id}\" not found!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def watchlistNotFoundException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: watchlist \"{wl_name}\" not found!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def watchlistDuplicateException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: watchlist \"{wl_name}\" already exists!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def productNotFoundException_message(user_id:int, prod_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Error: product \"{prod_name}\" not found!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def emptyProfileException_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text="You have no watchlists yet!\nTry creating one with /addwatchlist",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def emptyWatchlistException_message(user_id:int, wl_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"Watchlist {wl_name} has no products!\nAdd one with /addproduct",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def unknownError_message(user_id:int) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text="Unknown error: something went wrong!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)

def badAmazonProductException_message(user_id:int, prod_name:str) -> None:
    sent = bot.send_message(
        chat_id=user_id,
        text=f"\"{prod_name}\" Amazon product is not fit for web scraping, sorry :(",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(sent,logger)



##?## ------------------------------ BOT ROUTES ------------------------------ ##?##



#? START

@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
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



#? ADDWATCHLIST

@bot.message_handler(commands=['addwatchlist'])
def addwatchlist(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
    sender_id = message.from_user.id
    new_msg = bot.send_message(
        chat_id=sender_id,
        text="Name of the watchlist to be created? (64 characters max, unique)",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_1,args=(sender_id))

def addwatchlist_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args
    wl_name = message.text
    if (len(wl_name) > 64):
        bot.send_message(chat_id=sender_id,text="Invalid name: it is longer than 64 characters")
        return
    new_msg = bot.send_message(chat_id=sender_id,text="Do you want to set a target price for this watchlist? (Number if yes, \"no\" otherwise)")
    bot.register_next_step_handler(message=new_msg,callback=addwatchlist_step_2,args=(sender_id,wl_name))

def addwatchlist_step_2(message:telebot.types.Message,args:Tuple[int,str]) -> None:
    if command_switch(message): return
    log(message,logger)
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
    log(message,logger)
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
    bot.register_next_step_handler(message=new_msg,callback=removewatchlist_step_1,args=(sender_id))

def removewatchlist_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    log(message,logger)
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



#? ADDPRODUCT

@bot.message_handler(commands=['addproduct'])
def addproduct(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
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
        text="To which watchlist do you want to add a product?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_1,args=(sender_id))

def addproduct_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args
    wl_name = message.text
    new_msg = bot.send_message(
        chat_id=sender_id,
        text="Product URL:",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_2,args=(sender_id,wl_name))

def addproduct_step_2(message:telebot.types.Message,args:Tuple[int,str]) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args[0]
    wl_name = args[1]
    url = message.text
    if (not url.startswith("https://") or (not ("amazon" in url) and (not ("amzn" in url)))):
        bot.send_message(chat_id=sender_id,text=f"Invalid URL: {url}\nMake sure to paste an Amazon URL")
        return
    new_msg = bot.send_message(chat_id=sender_id,text="Do you want to give the product a custom name? (64 characters max, \"no\" to use Amazon's name):")
    bot.register_next_step_handler(message=new_msg,callback=addproduct_step_3,args=(sender_id,wl_name,url))

def addproduct_step_3(message:telebot.types.Message,args:Tuple[int,str,str]) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args[0]
    wl_name = args[1]
    url = args[2]
    prod_name = message.text
    if (len(prod_name) > 64):
        bot.send_message(chat_id=sender_id,text="Invalid name: name longer than 64 characters!")
        return
    if (prod_name in ["No","no"]): prod_name = None
    tmp_msg = bot.send_message(
        chat_id=sender_id,
        text="Scraping Amazon's website..."
    )
    try:
        added_name = db.addProduct(sender_id,wl_name,url,prod_name)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except WatchlistNotFoundException:
        watchlistNotFoundException_message(sender_id,wl_name)
        return
    except BadAmazonProductException:
        badAmazonProductException_message(sender_id,(prod_name if prod_name not in ["No","no"] else ""))
        return
    except:
        unknownError_message(sender_id)
        return
    bot.delete_message(chat_id=sender_id,message_id=tmp_msg.id)
    final_msg = bot.send_message(
        chat_id=sender_id,
        text=f"\"{added_name}\" added to watchlist \"{wl_name}\"!"
    )
    log(final_msg,logger)



#? REMOVEPRODUCT

@bot.message_handler(commands=['removeproduct'])
def removeproduct(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
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
        text="From which watchlist do you want to remove a product?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=removeproduct_step_1,args=(sender_id))

def removeproduct_step_1(message:telebot.types.Message,args:int) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args
    wl_name = message.text
    try:
        prod_names = db.getProducts(sender_id,wl_name)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except WatchlistNotFoundException:
        watchlistNotFoundException_message(sender_id)
        return
    except EmptyWatchlistException:
        emptyWatchlistException_message(sender_id,wl_name)
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
    for prod_name in prod_names: keyboard.add(prod_name)
    new_msg = bot.send_message(
        chat_id=sender_id,
        text="Which product do you want to remove?",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message=new_msg,callback=removeproduct_step_2,args=(sender_id,wl_name))

def removeproduct_step_2(message:telebot.types.Message,args:Tuple[int,str]) -> None:
    if command_switch(message): return
    log(message,logger)
    sender_id = args[0]
    wl_name = args[1]
    prod_name = message.text
    try:
        db.removeProduct(sender_id,wl_name,prod_name)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except WatchlistNotFoundException:
        watchlistNotFoundException_message(sender_id,wl_name)
        return
    except ProductNotFoundException:
        productNotFoundException_message(sender_id,prod_name)
        return
    except:
        unknownError_message(sender_id)
        return
    final_msg = bot.send_message(
        chat_id=sender_id,
        text=f"{prod_name} removed from watchlist \"{wl_name}\"!",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    log(final_msg,logger)



#? LISTALL

@bot.message_handler(commands=['listall'])
def listall(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
    sender_id = message.from_user.id
    try:
        msg = db.toString(sender_id)
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
    bot.send_message(chat_id=sender_id,text=msg,reply_markup=telebot.types.ReplyKeyboardRemove())



#? UPDATE

@bot.message_handler(commands=['update'])
def update(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
    sender_id = message.from_user.id
    tmp_msg = bot.send_message(
        chat_id=sender_id,
        text="Scraping Amazon's website..."
    )
    try:
        msg = db.updateWatchlists(sender_id)
    except UserNotAuthorizedException:
        userNotAuthorizedException_message(sender_id)
        return
    except UserNotFoundError:
        userNotFoundError_message(sender_id)
        return
    except:
        unknownError_message(sender_id)
        return
    bot.delete_message(chat_id=sender_id,message_id=tmp_msg.id)
    sent = bot.send_message(chat_id=sender_id,text=(msg if msg != "" else "You have no updates"),reply_markup=telebot.types.ReplyKeyboardRemove())
    log(sent,logger)



#? AUTH

@bot.message_handler(commands=['auth'])
def auth(message:telebot.types.Message) -> None:
    if (message.from_user.is_bot): return
    log(message,logger)
    sender_id = message.from_user.id
    if (sender_id == db.adminId):
        bot.send_message(
            chat_id=db.adminId,
            text="Why are you asking for authorization, jaf?"
        )
        return
    if (sender_id in db.authorizedUsers):
        bot.send_message(
            chat_id=sender_id,
            text="You already are an authorized user, no need to ask again :)"
        )
        return
    if (addPendingRequest(sender_id) == -1):
        bot.send_message(
            chat_id=sender_id,
            text="You already have a pending authorization request that will get reviewed soon."
        )
        return
    askAdminAuthUser(sender_id,message.from_user.first_name)
    bot.send_message(
        chat_id=sender_id,
        text="An authorization request has been sent! You will be notified when the request gets reviewed.",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    



#? USERS (ADMIN COMMAND ONLY)
@bot.message_handler(commands=['users'])
def users(message:telebot.types.Message) -> None:
    log(message,logger)
    if (message.from_user.id != db.adminId): return
    msg = "User list:\n"
    for user_id in db.authorizedUsers:
        msg += str(user_id)+'\n'
    sent = bot.send_message(
        chat_id=db.adminId,
        text=msg
    )
    log(sent,logger)








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

    schedule.every().day.at(SCHEDULED_TIME).do(dailyUpdate)
    dailyUpdateThread = threading.Thread(target=updateRoutine)

    print("Jaf's AWS (Amazon Web Scraper) Telegram bot started\n")
    logger.info("Jaf's AWS (Amazon Web Scraper) server started")

    dailyUpdateThread.start()
    bot.infinity_polling()



 

    
    
    

    




    