from json import load,dump
from typing import Union, List, Dict
import requests
from bs4 import BeautifulSoup
from pysondb import db


class JsonDatabase:

    class Watchlist:

        class Product:

            url = None
            name = None
            fullName = None
            lastPrice = None
            price = None

            def __init__(self, url:str, name:str=None, d:dict=None) -> None:
                if (d is not None):
                    self.fromDict(d)
                    return
                if (len(url) > 0): self.url = url
                else: return
                if (url.startswith("https://")): self.webScrape()
                if ((name is not None) and (len(name) > 0)): self.name = name

            def __str__(self) -> str:
                return f"{self.name if (self.name is not None) else self.fullName}: {self.price:.2f} €"
            def __repr__(self) -> str:
                return f"{self.name if (self.name is not None) else self.fullName}: {self.price:.2f} €"

            def __eq__(self, __o: object) -> bool:
                if (isinstance(__o, self.__class__)):
                    return (self.name if self.name is not None else self.fullName) == (__o.name if __o.name is not None else __o.fullName)
                return False
            def __lt__(self, __o: object) -> bool:
                if (isinstance(__o, self.__class__)):
                    return (self.name if self.name is not None else self.fullName) < (__o.name if __o.name is not None else __o.fullName)
                return False
            def __gt__(self, __o: object) -> bool:
                if (isinstance(__o, self.__class__)):
                    return (self.name if self.name is not None else self.fullName) > (__o.name if __o.name is not None else __o.fullName)
                return False


            def webScrape(self, max_retries:int=20) -> None:

                fullName = None
                price = None
                
                for _ in range(max_retries):
                    if ((price is not None) and (fullName is not None)): break

                    r = requests.get(self.url)
                    if (r.status_code != 200): continue
                    
                    pageContent = BeautifulSoup(r.content, 'html.parser')

                    whole_price = pageContent.find("span",class_="a-price-whole")
                    cent_price = pageContent.find("span",class_="a-price-fraction")
                    price_str = f"{whole_price.text.replace(',','.')}{cent_price.text}"
                    price = float(price_str)

                    if (fullName is None): fullName = pageContent.find("span",id="productTitle").text

                if (self.fullName is None): self.fullName = fullName
                self.lastPrice = self.price
                self.price = price
                return


            def updatePrice(self) -> float:
                self.webScrape()
                return self.lastPrice - self.price

            
            def toDict(self) -> dict:
                out_d = {
                    "name":self.name,
                    "fullName":self.fullName,
                    "url":self.url,
                    "lastPrice":self.lastPrice,
                    "price":self.price
                }
                return out_d

            def fromDict(self, d:dict) -> None:
                self.url = d['url']
                self.name = d['name']
                self.fullName = d['fullName']
                self.lastPrice = d['lastPrice']
                self.price = d['price']

        ##?## ----------------------------------- Watchlist --------------------------------------- ##?##



        name = None
        products:List[Product] = None
        targetPrice = None
        lastTotal = None
        total = None

        def __init__(self, name:str, targetPrice:float=None, d:dict=None) -> None:
            if (not (len(name) > 0)): return
            self.name = name
            if (d is not None):
                self.fromDict(d)
                return
            self.products = []
            if (targetPrice is not None): self.targetPrice = targetPrice
            self.total = 0.0

        def __str__(self) -> str:
            ret = self.name+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice}\n" if self.targetPrice is not None else "")
            return ret
        def __repr__(self) -> str:
            ret = self.name+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice}\n" if self.targetPrice is not None else "")
            return ret

        def toDict(self) -> dict:
            out_d = {
                "name":self.name,
                "products":[],
                "targetPrice":self.targetPrice,
                "lastTotal":self.lastTotal,
                "total":self.total
            }
            for prod in self.products:
                out_d["products"].append(prod.toDict())
            return out_d

        def fromDict(self, d:dict) -> None:
            self.targetPrice = d['targetPrice']
            self.lastTotal = d['lastTotal']
            self.total = d['total']
            for prod_d in d['products']:
                new_prod = self.Product("fakeurl",d=prod_d)
                self.products.append(new_prod)
            self.products.sort(key=lambda p: p.name if p.name is not None else p.fullName)

        
        def editTargetPrice(self, targetPrice:Union[float,None]) -> None:
            self.targetPrice = targetPrice


        def addProduct(self, url:str, name:str=None) -> int:
            #if (self.findProduct(name) is not None): return -1
            new_prod = self.Product(url,name)
            self.total += new_prod.price
            self.products.append(new_prod)
            self.products.sort(key=lambda p: p.name if p.name is not None else p.fullName)
            return 0
        
        def removeProduct(self, name:str) -> int:
            index = self.findProduct(name)
            if (index is not None):
                popped = self.products.pop(index)
                self.total -= popped.price
                self.products.sort(key=lambda p: p.name if p.name is not None else p.fullName)
                return 0
            return -1
        

        def findProduct(self, name:str) -> Union[int,None]:
            top = len(self.products)-1
            bot = 0     
            while (top >= bot):
                mid = (top+bot)//2
                elem = self.products[mid]
                elem_name = elem.name if elem.name is not None else elem.fullName
                if (name == elem_name):
                    return mid
                if (name < elem_name):
                    top = (mid-1)
                    continue
                if (name > elem_name):
                    bot = (mid+1)
                    continue
            return None

        #! DEPRECATED, LINEAR TIME :(
        def findProductLinear(self, name:str) -> int:
            for index,prod in enumerate(self.products):
                if (name == (prod.name if prod.name is not None else prod.fullName)):
                    return index
            return None


        def updatePrices(self) -> bool:
            if (len(self.products == 0)): return False
            diff = 0.0
            for i in range(len(self.products)):
                diff += self.products[i].updatePrice()
            self.lastTotal = self.total
            self.total -= diff
            if (self.targetPrice is not None):
                if (self.total <= self.targetPrice):
                    return True
            if (diff >= 5.0):
                return True
            return False



        def loadFromJson(self, json_path:str) -> int:
            with open(json_path, "r", encoding='utf-8') as in_json:
                jsonObj = load(in_json)
                self.name = jsonObj.get('name')
                prods = []
                for prod_entry in jsonObj.get('products'):
                    prod = self.Product(prod_entry[1],prod_entry[0])
                    prods.append(prod)
                self.products = prods
                if (jsonObj.get('targetPrice')):
                    self.targetPrice = jsonObj.get('targetPrice')
            return len(self.products)

        def saveToJson(self, json_path:str=None) -> int:
            out_d = dict()
            out_d['name'] = self.name
            out_d['products'] = []
            out_d['targetPrice'] = 0.0
            for prod in self.products:
                out_d["products"].append([(prod.name if prod.name is not None else prod.fullName),prod.url])
            if (self.targetPrice is not None):
                out_d["targetPrice"] = self.targetPrice

            out_path = json_path if json_path is not None else ("./resources/"+self.name+"_watchlist.json")
            with open(out_path, "w", encoding='utf-8') as out_json:
                dump(out_d,out_json,indent=4)
            return len(out_d["products"])

        def writeUpdatesToJson(self, json_path:str="./resources/updates.json") -> int:
            out_d = dict()
            with open(json_path,"r",encoding='utf-8') as updates_json:
                out_d = load(updates_json)
            out_d[self.name] = self.toDict()
            if (self.lastTotal is not None):
                out_d[self.name]["difference"] = self.lastTotal - self.total
            with open(json_path,"w",encoding='utf-8') as updates_json:
                dump(out_d,updates_json,indent=4)
            return len(out_d[self.name]['products'])

        def writeUpdatedWatchlists(self, name:str, txt_path:str="./resources/updates.txt") -> None:
            with open(txt_path,"a",encoding='utf-8') as txt:
                txt.write(name+'\n')



    ##?## ----------------------------------- Database --------------------------------------- ##?##



    database:db.JsonDatabase = None

    def __init__(self, jsonPath:str) -> None:
        self.database = db.getDb(jsonPath)



    def addUser(self, user_id:int) -> int:
        return self.database.add({
            "user_id": user_id,
            "watchlists": []
        })
    


    def getUser(self, user_id:int) -> dict:
        user_list = self.database.getByQuery({'user_id':user_id})
        if (len(user_list) == 0): return None
        return user_list[0]



    def findWatchlist(self, wl_list:List[dict], wl_name:str) -> Union[int,None]:
        top = len(wl_list)-1
        bot = 0
        while (top >= bot):
            mid = (top+bot)//2
            elem_name = wl_list[mid].get('name')
            if (wl_name == elem_name):
                return mid
            if (wl_name < elem_name):
                top = (mid-1)
                continue
            if (wl_name > elem_name):
                bot = (mid+1)
                continue
        return None



    def addWatchlist(self, user_id:int, wl_name:str, targetPrice:float=None) -> int:
        user_dict = self.getUser(user_id)
        if (user_dict is None):
            self.addUser(user_id)
            user_dict = self.getUser(user_id)
        user_wl:List[dict] = user_dict.get('watchlists')
        for wl_dict in user_wl:
            if (wl_dict.get('name') == wl_name): return -1
        user_wl.append(self.Watchlist(wl_name,targetPrice).toDict())
        user_wl.sort(key=lambda wl_dict: wl_dict['name'])
        self.database.updateByQuery({'user_id':user_id},{'watchlists':user_wl})
        return 0



    def removeWatchlist(self, user_id:int, wl_name:str) -> int:
        user_dict = self.getUser(user_id)
        if (user_dict is None): return -1
        user_wl:List[dict] = user_dict.get('watchlists')
        index = self.findWatchlist(user_wl,wl_name)
        if (index is None): return -1
        user_wl.pop(index)
        user_wl.sort(key=lambda wl_dict: wl_dict['name'])
        self.database.updateByQuery({'user_id':user_id},{'watchlists':user_wl})
        return 0

    

    def addProduct(self, user_id:int, wl_name:str, url:str, prod_name:str=None) -> int:
        user_dict = self.getUser(user_id)
        if (user_dict is None): return -1
        user_wl:List[dict] = user_dict.get('watchlists')
        index = self.findWatchlist(user_wl,wl_name)
        if (index is None): return -1
        wl = self.Watchlist("fakename",d=user_wl[index])
        wl.addProduct(url,prod_name)
        user_wl[index] = wl.toDict()
        self.database.updateByQuery({'user_id':user_id},{'watchlists':user_wl})
        return 0



    def removeProduct(self, user_id:int, wl_name:str, prod_name:str) -> int:
        user_dict = self.getUser(user_id)
        if (user_dict is None): return -1
        user_wl:List[dict] = user_dict.get('watchlists')
        index = self.findWatchlist(user_wl,wl_name)
        if (index is None): return -1
        wl = self.Watchlist("fakename",d=user_wl[index])
        if (wl.removeProduct(prod_name) == -1): return -1
        user_wl[index] = wl.toDict()
        self.database.updateByQuery({'user_id':user_id},{'watchlists':user_wl})
        return 0



    def updateWatchlists(self, user_id:int) -> str:
        """Updates all the user watchlists and returns an update message

        Parameters
        -----
        user_id : int
            The unique Telegram user ID
        
        Returns
        -----
        str
            The update message to be sent to the user
        """

        user_dict = self.getUser(user_id)
        if (user_dict is None): return None
        ret = ""
        user_wl:List[dict] = user_dict.get('watchlists')
        for i,wl_dict in enumerate(user_wl):
            wl = self.Watchlist(wl_dict['name'],d=wl_dict)
            if (wl.updatePrices()):
                ret += str(wl) + "\n ~~~~~ \n"
            user_wl[i] = wl.toDict()
        self.database.updateByQuery({'user_id':user_id},{'watchlists':user_wl})
        return ret



    def read(self, filepath:str="./resources/database.json") -> None:
        self.database = db.getDb(filepath)

    def write(self, filepath:str="./resources/database.json") -> None:
        pass #? USELESS
