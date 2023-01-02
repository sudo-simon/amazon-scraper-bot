from database import Database
from json import load
from time import time

def getProducts(json_path:str) -> list:
    prods = []
    with open(json_path,"r",encoding='utf-8') as in_json:
        prods = list(dict(load(in_json)).get("products"))
    return prods

JSON_PATH = "resources/test_products.json"
TESTS = 10

test_db = Database()
test_db.addWatchlist("test")

test_products = getProducts(JSON_PATH)
error_count = 0

print(f"Running {TESTS} tests...\n")
start = time()
for _ in range(TESTS):
    for prod in test_products:
        test_db.database['test'].addProduct(prod[1],prod[0])
        if ((test_db.database['test'].products[test_db.database['test'].findProduct(prod[0])]).price is None):
            error_count += 1
            break
elapsed = time()-start


list_str = ""
for prod in test_db.database['test'].products:
    list_str += "\t"+str(prod)+"\n"
out_str = (
        f"Stats for the parsing of {len(test_products)} products:\n"
        f"Average time = {(elapsed/TESTS):.3f} ({((elapsed/TESTS)/len(test_products)):.3f}/product)\n"
        f"Correctness = {TESTS-error_count}/{TESTS}\n"
        f"Product list = [\n{list_str}]"
    )

print(out_str)