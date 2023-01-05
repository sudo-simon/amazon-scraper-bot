from json import load,dump
from typing import Union, List, Dict
import requests
from bs4 import BeautifulSoup

class Database:

    class Watchlist:

        class Product:

            url = None
            name = None
            fullName = None
            lastPrice = None
            price = None

            def __init__(self, url:str, name:str=None) -> None:
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


            def webScrape(self, max_retries:int=20) -> int:

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

                    if (fullName is None): fullName = pageContent.find("span",id="productTitle").text.strip()

                if (price is None): return -1
                if (self.fullName is None): self.fullName = fullName
                self.lastPrice = self.price
                self.price = price
                return 0


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



        id = None
        products:List[Product] = None
        targetPrice = None
        lastTotal = None
        total = None

        def __init__(self, id:str, targetPrice:float=None, json_path:str=None) -> None:
            if (not (len(id) > 0)):
                try:
                    self.loadFromJson(json_path)
                except: return
            else:
                #if (' ' in id): return
                self.id = id
                self.products = []
                if (targetPrice is not None): self.targetPrice = targetPrice
                self.total = 0.0

        def __str__(self) -> str:
            ret = self.id+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice}\n" if self.targetPrice is not None else "")
            return ret
        def __repr__(self) -> str:
            ret = self.id+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice}\n" if self.targetPrice is not None else "")
            return ret

        def toDict(self) -> dict:
            out_d = {
                "products":[],
                "targetPrice":self.targetPrice,
                "lastTotal":self.lastTotal,
                "total":self.total
            }
            for prod in self.products:
                out_d["products"].append(prod.toDict())
            return out_d

        def fromDict(self, id:str, d:dict) -> None:
            self.id = id
            self.targetPrice = d['targetPrice']
            self.lastTotal = d['lastTotal']
            self.total = d['total']
            for prod_d in d['products']:
                new_prod = self.Product("fakeurl")
                new_prod.fromDict(prod_d)
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
                ret = self.products.pop(index)
                self.total -= ret.price
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

        def findProductLinear(self, name:str) -> int:
            for index,prod in enumerate(self.products):
                if (name == (prod.name if prod.name is not None else prod.fullName)):
                    return index
            return None


        def updatePrices(self) -> float:
            diff = 0.0
            if (len(self.products) == 0): return 0.0
            for i in range(len(self.products)):
                diff += self.products[i].updatePrice()
            self.lastTotal = self.total
            self.total -= diff
            if (self.targetPrice is not None):
                if (self.total <= self.targetPrice):
                    self.writeUpdatedWatchlists(self.id)
                    return diff
            if (diff >= 5.0):
                self.writeUpdatedWatchlists(self.id)
                return diff
            return diff


        def loadFromJson(self, json_path:str) -> int:
            with open(json_path, "r", encoding='utf-8') as in_json:
                jsonObj = load(in_json)
                self.id = jsonObj.get('id')
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
            out_d['id'] = self.id
            out_d['products'] = []
            out_d['targetPrice'] = 0.0
            for prod in self.products:
                out_d["products"].append([(prod.name if prod.name is not None else prod.fullName),prod.url])
            if (self.targetPrice is not None):
                out_d["targetPrice"] = self.targetPrice

            out_path = json_path if json_path is not None else ("./resources/"+self.id+"_watchlist.json")
            with open(out_path, "w", encoding='utf-8') as out_json:
                dump(out_d,out_json,indent=4)
            return len(out_d["products"])

        def writeUpdatesToJson(self, json_path:str="./resources/updates.json") -> int:
            out_d = dict()
            with open(json_path,"r",encoding='utf-8') as updates_json:
                out_d = load(updates_json)
            out_d[self.id] = self.toDict()
            if (self.lastTotal is not None):
                out_d[self.id]["difference"] = self.lastTotal - self.total
            with open(json_path,"w",encoding='utf-8') as updates_json:
                dump(out_d,updates_json,indent=4)
            return len(out_d[self.id]['products'])

        def writeUpdatedWatchlists(self, id:str, txt_path:str="./resources/updates.txt") -> None:
            with open(txt_path,"a",encoding='utf-8') as txt:
                txt.write(id+'\n')



    ##?## ----------------------------------- Database --------------------------------------- ##?##



    database:Dict[str,Watchlist] = None

    def __init__(self) -> None:
        self.database = dict()

    def __str__(self) -> str:
        ret = ""
        for wl in self.database.values():
            ret += str(wl)
            ret += "\n---\n"
        return ret
    def __repr__(self) -> str:
        ret = ""
        for wl in self.database.values():
            ret += str(wl)
        return ret



    def addWatchlist(self, id:str, targetPrice:float=None, json_path:str=None) -> None:
        new_watchlist = self.Watchlist(id,targetPrice,json_path)
        self.database[id] = new_watchlist



    def removeWatchlist(self, name:str) -> int:
        if (name not in self.database.keys()): return -1
        prods = [prod.name if prod.name is not None else prod.fullName for prod in self.database[name].products]
        #for prod in self.database[id].products:
        #    prods.append(prod.name if prod.name is not None else prod.fullName)
        for prod_name in prods:
            self.database[name].removeProduct(prod_name)
        self.database.pop(name)
        return 0

    

    def addProduct(self, wl_name:str, url:str, prod_name:str=None) -> int:
        return self.database[wl_name].addProduct(url,prod_name)



    def removeProduct(self, wl_name:str, prod_name:str) -> int:
        return self.database[wl_name].removeProduct(prod_name)



    def toDict(self) -> dict:
        out_d = dict()
        for id,watchlist in self.database.items():
            out_d[id] = watchlist.toDict()
        return out_d

    def fromDict(self, d:dict) -> None:
        for id,watchlist_d in d.items():
            self.addWatchlist(id)
            self.database[id].fromDict(id,watchlist_d)

    

    def read(self, filepath:str="./resources/database.json") -> int:
        r_obj = {}
        with open(filepath,"r",encoding='utf-8') as r_file:
            r_obj = load(r_file)
        self.fromDict(r_obj)
        return len(self.database.keys())

    def write(self, filepath:str="./resources/database.json") -> None:
        with open(filepath,"w",encoding='utf-8') as w_file:
            dump(self.toDict(),w_file,indent=4)
