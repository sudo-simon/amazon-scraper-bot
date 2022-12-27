from web_scraper.productSearch import Product, getProducts, loadJson, updatePrices
from time import sleep
from os import system
from json import dump
import schedule
from typing import List
import threading

JSON_PATH = "resources/products.json"
UPDATES_PATH = "resources/updates.json"
BOT_PATH = "/home/jaf/Repos/amazon-scraper-bot/src/telegram_bot/bot.py"
SCHEDULED_TIME = "13:50"


def computeTotal(products:List[Product]) -> float:
    tot = 0.0
    for prod in products:
        tot += prod.price
    return tot


def scheduledUpdate(products:List[Product],modifiedList:List[Product],diff:List[float]) -> None:
    modifiedIndexes = updatePrices(products)
    modifiedList.extend([products[i] for i in modifiedIndexes])
    for prod in [products[i] for i in modifiedIndexes]:
        diff[0] += (prod.oldPrice - prod.price)
    return

def launchBot() -> None:
    system("x-terminal-emulator -e 'python3 "+BOT_PATH+"'")



PRODUCTS, TARGET = loadJson(JSON_PATH)
TOTAL = computeTotal(PRODUCTS)
MODIFIED = []
DIFFERENCE = [0.0]

print("Amazon Web Scraper started...\n")
for prod in PRODUCTS:
    print(prod)
print(f"\nTarget total = {TARGET} €\nTotal = {TOTAL} €")


bot_thread = threading.Thread(target=launchBot,args=())
bot_thread.start()


schedule.every().day.at(SCHEDULED_TIME).do(scheduledUpdate,PRODUCTS,MODIFIED,DIFFERENCE)
while True:
    MODIFIED = []
    DIFFERENCE[0] = 0.0
    schedule.run_pending()
    sleep(30)

    d = dict()
    d["updates"] = []
    d["difference"] = DIFFERENCE[0]
    for prod in MODIFIED:
        p_d = {
            "url":prod.url,
            "name":prod.name,
            "price":prod.price
        }
        d["updates"].append(p_d)

    with open(UPDATES_PATH,"w",encoding='utf-8') as updates_json:
        dump(d,updates_json,indent=4)


