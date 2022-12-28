from json import load,dump
from typing import List,Tuple,Union
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


    products = None
    targetPrice = None

    def __init__(self,targetPrice:float=None) -> None:
        self.products = []
        if (targetPrice is not None): self.targetPrice = targetPrice

    def __str__(self) -> str:
        return f""
    def __repr__(self) -> str:
        return f""

    
    def editTargetPrice(self, targetPrice:Union[float,None]) -> None:
        self.targetPrice = targetPrice

    def addProduct(self, product:Product) -> int:
        if (product in self.products): return -1
        self.products.append(product)
        self.products.sort()
        return 0
    
    def removeProduct(self,name:str) -> Product:
        for i in range(len(self.products)):
            prod = self.products[i]
            if (prod.name if prod.name is not None else prod.fullName) == name:
                ret = self.products.pop(i)
                self.products.sort()
                return ret
        
        return None



    