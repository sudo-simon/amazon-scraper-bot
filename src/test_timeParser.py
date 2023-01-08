from AWSDatabase import AWSDatabase
from dotenv import load_dotenv
from os import getenv
from os.path import join
from json import load
from time import time

def getProducts(json_path:str) -> list:
    prods = []
    with open(json_path,"r",encoding='utf-8') as in_json:
        prods = list(dict(load(in_json)).get("products"))
    return prods

TEST_PATH = "./tests/"
TEST_WL_NAME = "Test Watchlist"
TESTS = 10

load_dotenv()
test_db = AWSDatabase(getenv("ADMIN_ID"),TEST_PATH)

test_products = getProducts(join(TEST_PATH,"test_products.json"))
test_db.addWatchlist(test_db.adminId,TEST_WL_NAME)
error_count = 0

print(f"Running {TESTS} tests...\n")
start = time()
for _ in range(TESTS):
    for prod in test_products:
        url = prod[1]
        name = prod[0]
        added_name = test_db.addProduct(test_db.adminId,TEST_WL_NAME,url,name)
        if (added_name is None):
            error_count += 1
            print(f"Error #{error_count}: [{name},{url}]")
        else: print(f"~> {added_name} added to watchlist")
elapsed = time()-start


list_str = ""
for prod_name in test_db.getProducts(test_db.adminId,TEST_WL_NAME):
    list_str += f"\t{prod_name}\n"
out_str = (
        f"Stats for the parsing of {len(test_products)} products:\n"
        f"Average time = {(elapsed/TESTS):.3f} ({((elapsed/TESTS)/len(test_products)):.3f}/product)\n"
        f"Correctness = {TESTS-error_count}/{TESTS}\n"
        f"Product list = [\n{list_str}]"
    )

print(out_str)