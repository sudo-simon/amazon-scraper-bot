from json import load,dump
import requests
from typing import List, Tuple
from bs4 import BeautifulSoup

MIN_PRICE_DIFF = 1.0
MAX_CONNECTION_TESTS = 10


class Product:

    url = None
    name = None
    oldPrice = None
    price = None


    def webScrape(self,url:str=None) -> Tuple[str,float]:

        name = None
        price = None
        
        for test in range(MAX_CONNECTION_TESTS):
            if (price is not None): break

            r = requests.get(self.url) if url is None else requests.get(url)
            if (r.status_code != 200): continue
            
            pageContent = BeautifulSoup(r.content, 'html.parser')

            whole_price = pageContent.find("span",class_="a-price-whole")
            cent_price = pageContent.find("span",class_="a-price-fraction")
            price_str = f"{whole_price.text.replace(',','.')}{cent_price.text}"
            price = float(price_str)

            if (name is None): name = pageContent.find("span",id="productTitle").text

        return (name,price)

    
    def __init__(self, url:str, name:str=None) -> None:
        if (len(url) > 0): self.url = url
        else: return
        self.name, self.price = self.webScrape(url=url)
        if (name is not None and len(name) > 0): self.name = name


    def updatePrice(self) -> float:
        name, price = self.webScrape()
        if (self.name in name):
            self.oldPrice = self.price
            self.price = price
            return self.oldPrice - self.price
        else: return None
    

    def __str__(self) -> str:
        return f"{self.name}: {self.price} €"
    def __repr__(self) -> str:
        return f"{self.name}: {self.price} €"



def getProducts(json:str) -> List[Product]:
    productList = []
    with open(json,"r",encoding='utf-8') as json_file:
        objectsList = load(json_file).get("products")
        for i in range(len(objectsList)):
            name = objectsList[i][0]
            url = objectsList[i][1]
            new_prod = Product(url, name if name != "None" else None)
            productList.append(new_prod)
    return productList


def updatePrices(productList:List[Product]) -> List[int]:
    updatedIndexes = []
    for index,product in enumerate(productList):
        priceDiff = product.updatePrice()
        if (priceDiff >= MIN_PRICE_DIFF):
            updatedIndexes.append(index)
    return updatedIndexes

    