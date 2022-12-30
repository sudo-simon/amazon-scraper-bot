from json import load,dump
from typing import Union, List
import requests
from bs4 import BeautifulSoup

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
            self.webScrape()
            if ((name is not None) and (len(name) > 0)): self.name = name

        def __str__(self) -> str:
            return f"{self.name if (self.name is not None) else self.fullName}: {self.price} €"
        def __repr__(self) -> str:
            return f"{self.name if (self.name is not None) else self.fullName}: {self.price} €"

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


        def webScrape(self, max_retries:int=10) -> None:

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



    ##!## ------------------------------------------------------------------------------------ ##!##



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
            self.id = id
            self.products = []
            if (targetPrice is not None): self.targetPrice = targetPrice
            self.total = 0.0

    def __str__(self) -> str:
        ret = ""
        for prod in self.products:
            ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
        ret += f"\nTotal: {self.total} €\n"
        return ret
    def __repr__(self) -> str:
        ret = ""
        for prod in self.products:
            ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
        return ret

    
    def editTargetPrice(self, targetPrice:Union[float,None]) -> None:
        self.targetPrice = targetPrice


    def addProduct(self, url:str, name:str=None) -> int:
        if (self.findProduct(name) is not None): return -1
        new_prod = self.Product(url,name)
        self.total += new_prod.price
        self.products.append(new_prod)
        self.products.sort()
        return 0
    
    def removeProduct(self, name:str) -> Product:
        index = self.findProduct(name)
        if (index is not None):
            ret = self.products.pop(index)
            self.total -= ret.price
            self.products.sort()
            return ret
        return None
    

    def findProduct(self, name:str) -> Union[int,None]:
        
        top = len(self.products)-1
        bot = 0
        
        while (top > bot):
            mid = (top+bot)//2
            elem = self.products[mid]
            elem_name = elem.name if elem.name is not None else elem.fullName
            if (name == elem_name):
                return mid
            if (name < elem_name):
                top = mid
                continue
            if (name > elem_name):
                bot = mid
                continue
        
        return None


    def updatePrices(self) -> float:
        diff = 0.0
        for i in range(len(self.products)):
            diff += self.products[i].updatePrice()
        self.lastTotal = self.total
        self.total -= diff
        self.writeUpdatesToJson()
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

    def writeUpdatesToJson(self, json_path:str=None) -> int:
        out_d = dict()
        out_d['id'] = self.id
        out_d['products'] = []
        out_d['difference'] = 0.0
        for prod in self.products:
            prod_d = dict()
            prod_d['name'] = prod.name if prod.name is not None else prod.fullName
            prod_d['price'] = prod.price
            prod_d['url'] = prod.url
            out_d["products"].append(prod_d)
        if (self.lastTotal is not None):
            out_d["difference"] = self.lastTotal - self.total
        
        out_path = json_path if json_path is not None else ("./resources/"+self.id+"_update.json")
        with open(out_path,"w",encoding='utf-8') as out_json:
            dump(out_d,out_json,indent=4)
        return len(out_d["products"])



    