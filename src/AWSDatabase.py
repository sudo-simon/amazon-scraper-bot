from json import load,dump
import csv
from os.path import join,isfile
from typing import Union, List, Dict, Tuple
import requests
from bs4 import BeautifulSoup

##?## ----------------------------------- Exceptions --------------------------------------- ##?##

class UserNotAuthorizedException(Exception):
    """Exception raised when a user that is not authorized tries to perform a command.
    """
    pass
class UserNotFoundError(Exception):
    """Exception raised when a user is not found in the database but is an authorized one.
    The only true error of the database.
    """
    pass
class WatchlistNotFoundException(Exception):
    """Exception raised when the selected watchlist is not found.
    """
    pass
class WatchlistDuplicateException(Exception):
    """Exception raised when a user tries to create a watchlist with an existing name.
    """
    pass
class ProductNotFoundException(Exception):
    """Exception raised when the selected product is not found.
    """
    pass
class EmptyProfileException(Exception):
    """Exception raised when the user has no watchlists
    """
    pass
class EmptyWatchlistException(Exception):
    """Exception raised when the watchlist has no products
    """
    pass
class BadAmazonProductException(Exception):
    """Exception raised when an Amazon product's page is not fit to be scraped
    """
    pass





class AWSDatabase:
    """Class for the database manipulation for the Amazon Web Scraper bot

    Attributes
    -----
    jsonPath : str
        The filepath of the json file containing the database
    
    database : Dict[int,Dict[str,dict]]
        The dictionary containing the actual database

    Methods
    -----
    addUser(user_id:int) -> int
        Adds a new user to the database, returns -1 if already present

    getUser(user_id:int) -> Dict[str,dict]
        Returns the user's watchlists dictionary, None if user is not present in the database

    addWatchlist(self, user_id:int, wl_name:str, targetPrice:float=None) -> int
        Adds a new watchlist for the user, and creates the user's entry if it's a new user
    
    removeWatchlist(self, user_id:int, wl_name:str) -> int
        Removes the watchlist named wl_name. Returns 0 if successful, -1 if not
    
    addProduct(self, user_id:int, wl_name:str, url:str, prod_name:str=None) -> int
        Adds a new product to the watchlist name wl_name.
        Returns 0 if successful, -1 if not
    
    removeProduct(self, user_id:int, wl_name:str, prod_name:str) -> int
        Removes the product named prod_name from the watchlist named wl_name
        Returns 0 if successful, -1 if not
    
    updateWatchlists(self, user_id:int) -> str
        Updates the prices of every product on every watchlist and returns the update message
    
    read() -> int
        Loads the database from the json file at jsonPath
    
    write() -> None
        Writes the database on the json file at jsonPath
    """

    class Watchlist:

        class Product:

            url:str
            name:Union[str,None]
            fullName:str
            lastPrice:Union[float,None]
            price:float

            def __init__(self, url:str, name:str=None, d:dict=None) -> None:
                self.url = None
                self.name = None
                self.fullName = None
                self.lastPrice = None
                self.price = None
                if (len(url) > 0): self.url = url
                else: return
                if (url.startswith("https://")): self.webScrape()
                if ((name is not None) and (len(name) > 0)): self.name = name
                if (d is not None): self.fromDict(d)

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

                    try:
                        whole_price = pageContent.find("span",class_="a-price-whole")
                        cent_price = pageContent.find("span",class_="a-price-fraction")
                        price_str = f"{whole_price.text.replace(',','.')}{cent_price.text}"
                        price = float(price_str)
                    except: raise BadAmazonProductException

                    if (fullName is None): fullName = pageContent.find("span",id="productTitle").text.strip()

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



        name:str
        products:List[Product]
        targetPrice:Union[float,None]
        lastTotal:Union[float,None]
        total:float

        def __init__(self, name:str, targetPrice:float=None, d:dict=None) -> None:
            if (not (len(name) > 0)): return
            self.name = name
            self.products = []
            self.targetPrice = targetPrice
            self.lastTotal = None
            self.total = 0.0
            if (d is not None):
                self.fromDict(d)

        def __str__(self) -> str:
            ret = self.name+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice:.2f} €\n" if self.targetPrice is not None else "")
            return ret
        def __repr__(self) -> str:
            ret = self.name+":\n"
            for prod in self.products:
                ret += f"\n{prod.name if prod.name is not None else prod.fullName}\n{prod.price} €\n{prod.url}\n"
            ret += f"\nTotal: {self.total:.2f} €\n" + (f"Target: {self.targetPrice:.2f} €\n" if self.targetPrice is not None else "")
            return ret

        def toDict(self) -> dict:
            out_d = {
                #"name":self.name,
                "products":[],
                "targetPrice":self.targetPrice,
                "lastTotal":self.lastTotal,
                "total":self.total
            }
            for prod in self.products:
                out_d["products"].append(prod.toDict())
            return out_d

        def fromDict(self, d:dict) -> None:
            #self.name = d['name']
            self.targetPrice = d['targetPrice']
            self.lastTotal = d['lastTotal']
            self.total = d['total']
            for prod_d in d['products']:
                new_prod = self.Product("fakeurl",d=prod_d)
                self.products.append(new_prod)
            self.products.sort(key=lambda p: p.name if p.name is not None else p.fullName)

        
        def editTargetPrice(self, targetPrice:Union[float,None]) -> None:
            self.targetPrice = targetPrice


        def addProduct(self, url:str, name:str=None) -> str:
            #if (self.findProduct(name) is not None): return -1
            try: new_prod = self.Product(url,name)
            except: raise BadAmazonProductException
            self.total += new_prod.price
            self.products.append(new_prod)
            self.products.sort(key=lambda p: p.name if p.name is not None else p.fullName)
            return new_prod.name if new_prod.name is not None else new_prod.fullName
        
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
            if (len(self.products) == 0): return False
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



    ##?## ----------------------------------- Database --------------------------------------- ##?##


    jsonPath:str
    csvPath:str
    txtPath:str
    adminId:int
    authorizedUsers:List[int]
    database:Dict[int,Dict[str,dict]]

    def __init__(self, adminId:int, resourcesPath:str) -> None:
        self.jsonPath = join(resourcesPath,"database.json")
        self.csvPath = join(resourcesPath,"authorized_users.csv")
        self.txtPath = join(resourcesPath,"pending_users.txt")
        if (not isfile(self.jsonPath)): self.createJsonFile()
        if (not isfile(self.csvPath)): self.createCsvFile()
        if (not isfile(self.txtPath)): self.createTxtFile()
        self.adminId = adminId
        self.authorizedUsers = []
        self.database = {}
        self.loadDb()
        if (self.adminId not in self.database.keys()):
            self.database[self.adminId] = dict()
            self.saveDb()


    def createJsonFile(self) -> None:
        with open(self.jsonPath,'x',encoding='utf-8') as new_json:
            new_json.write("{"+"}")
    def createCsvFile(self) -> None:
        with open(self.csvPath,'x',encoding='utf-8') as new_csv:
            new_csv.write("user_id,user_firstName,role\n")
    def createTxtFile(self) -> None:
        with open(self.txtPath,'x',encoding='utf-8') as new_txt:
            new_txt.write("")



    def readAuthUsersIds(self) -> List[int]:
        auth_users = []
        with open(self.csvPath,"r",encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file,delimiter=',')
            first_line = True
            for row in csv_reader:
                if (first_line):
                    first_line = False
                    continue
                user_id = int(row[0])
                role = row[2]
                if (role == "User"): auth_users.append(user_id)
        return auth_users

    

    def getAuthUsers(self) -> List[Tuple[int,str,str]]:
        ret = []
        with open(self.csvPath,"r",encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file,delimiter=',')
            first_line = True
            for row in csv_reader:
                if (first_line):
                    first_line = False
                    continue
                ret.append((int(row[0]),row[1],row[2]))
        return ret



    def addAuthUser(self,user_id:int, user_firstName:str) -> None:
        with open(self.csvPath,"a",encoding='utf-8') as csv_file:
            csv_file.write(f"{user_id},{user_firstName},User\n")
        self.authorizedUsers.append(user_id)

    def removeAuthUser(self, user_id:int) -> None:
        authUsers = self.getAuthUsers()
        i = 0
        for authUser_id,user_firstName,role in authUsers:
            if (authUser_id == user_id): break
            i += 1
        if (i < len(authUsers)): authUsers.pop(i)
        with open(self.csvPath,"w",encoding='utf-8') as csv_file:
            csv_file.write("user_id,user_firstName,role\n")
            for authUser_id,user_firstName,role in authUsers:
                csv_file.write(f"{authUser_id},{user_firstName},{role}\n")
        self.authorizedUsers.remove(user_id)


    def addUser(self, user_id:int, user_firstName:str) -> int:
        """Adds a new authorized user to both the authorized list and the database

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        Returns
        -----
        0 if successful, -1 if there's already a database entry for user_id (anomaly)
        """

        if (user_id in self.database.keys()): return -1
        self.addAuthUser(user_id,user_firstName)
        self.database[user_id] = dict()
        self.saveDb()
        return 0
        
    def banUser(self, user_id:int) -> int:
        if (user_id not in self.database.keys()): return -1
        self.removeAuthUser(user_id)
        self.database.pop(user_id)
        self.saveDb()
        return 0
            
    
    def getUser(self, user_id:int) -> Dict[str,dict]:
        return self.database.get(user_id,None)


    
    def getWatchlists(self, user_id:int) -> List[str]:
        """Gets all the user's watchlists' names

        Returns
        -----
        List[str]

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, EmptyProfileException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        ret = [wl_name for wl_name in user_dict.keys()]
        if (len(ret) == 0): raise EmptyProfileException
        return ret

    

    def getProducts(self, user_id:int, wl_name:str) -> List[str]:
        """Gets all the watchlist's products' names

        Returns
        -----
        List[str]

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException, EmptyWatchlistException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        wl_dict = user_dict.get(wl_name,None)
        if (wl_dict is None): raise WatchlistNotFoundException
        wl = self.Watchlist(wl_name,d=wl_dict)
        ret = [prod.name if prod.name is not None else prod.fullName for prod in wl.products]
        if (len(ret) == 0): raise EmptyWatchlistException
        return ret



    def addWatchlist(self, user_id:int, wl_name:str, targetPrice:float=None) -> int:
        """Adds a watchlist to the user user_id

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        wl_name : str
            The name of the watchlist to add

        targetPrice : float (optional)
            The target price to be associated with the watchlist

        Returns
        -----
        0 (ignore)

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, WatchlistDuplicateException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        if (wl_name in user_dict.keys()): raise WatchlistDuplicateException
        user_dict[wl_name] = self.Watchlist(wl_name,targetPrice).toDict()
        self.database[user_id] = user_dict
        self.saveDb()
        return 0



    def removeWatchlist(self, user_id:int, wl_name:str) -> int:
        """Removes a watchlist from the user user_id

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        wl_name : str
            The name of the watchlist to remove
        
        Returns
        -----
        0 (ignore)

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        popped = user_dict.pop(wl_name,None)
        if (popped is None): raise WatchlistNotFoundException
        self.database[user_id] = user_dict
        self.saveDb()
        return 0

    

    def addProduct(self, user_id:int, wl_name:str, url:str, prod_name:str=None) -> str:
        """Adds a product to the wl_name watchlist

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        wl_name : str
            The name of the watchlist to which the product will be added

        url : str
            The Amazon URL of the product

        prod_name : str (optional)
            The name of the product to add

        Returns
        -----
        str
            The name of the new product entry

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException, BadAmazonProductException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        wl_dict = user_dict.get(wl_name,None)
        if (wl_dict is None): raise WatchlistNotFoundException
        wl = self.Watchlist(wl_name,d=wl_dict)
        try: ret_name = wl.addProduct(url,prod_name)
        except BadAmazonProductException: raise BadAmazonProductException
        self.database[user_id][wl_name] = wl.toDict()
        self.saveDb()
        return ret_name



    def removeProduct(self, user_id:int, wl_name:str, prod_name:str) -> int:
        """Removes a product from the wl_name watchlist

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        wl_name : str
            The name of the watchlist from which the product will be removed
        
        prod_name : str
            The name of the product to remove
        
        Returns
        -----
        0 (ignore)

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, WatchlistNotFoundException, ProductNotFoundException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        wl_dict = user_dict.get(wl_name,None)
        if (wl_dict is None): raise WatchlistNotFoundException
        wl = self.Watchlist(wl_name,d=wl_dict)
        if (wl.removeProduct(prod_name) == -1): raise ProductNotFoundException
        self.database[user_id][wl_name] = wl.toDict()
        self.saveDb()
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

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError
        """

        self.loadDb()
        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        ret = "Some of your watchlists have been updated!\n\n"
        for wl_name in user_dict.keys():
            wl = self.Watchlist(wl_name,d=user_dict[wl_name])
            if (wl.updatePrices()):
                ret += str(wl) + "\n ~~~~~ \n"
            user_dict[wl_name] = wl.toDict()
        if (ret == "Some of your watchlists have been updated!\n\n"): ret = ""
        self.database[user_id] = user_dict
        self.saveDb()
        return ret


    
    def toString(self, user_id:int) -> str:
        """Returns the string representation of all the user's watchlists

        Parameters
        -----
        user_id : int
            The unique Telegram user ID

        Returns
        -----
        str
            The string representation of the user's watchlists

        Raises
        -----
        UserNotAuthorizedException, UserNotFoundError, EmptyProfileException
        """

        if ((user_id not in self.authorizedUsers) and (user_id != self.adminId)): raise UserNotAuthorizedException
        user_dict = self.getUser(user_id)
        if (user_dict is None): raise UserNotFoundError
        ret = ""
        for wl_name,wl_dict in user_dict.items():
            wl = self.Watchlist(wl_name,d=wl_dict)
            ret += str(wl) + "\n ~~~~~ \n"
        if (ret == ""): raise EmptyProfileException
        return ret



    def loadDb(self) -> None:
        """Reads the database from the json file at jsonPath"""
        tmp_d = {}
        with open(self.jsonPath,"r",encoding='utf-8') as r_file:
            tmp_d = load(r_file)
        self.database = {int(k):v for k,v in tmp_d.items()}
        self.authorizedUsers = self.readAuthUsersIds()
        

    def saveDb(self) -> None:
        """Writes the database to the json file at jsonPath"""

        with open(self.jsonPath,"w",encoding='utf-8') as w_file:
            dump(self.database,w_file,indent=4)
            #TODO: rimuovere l'indent per la memoria
