from web_scraper.productSearch import getProducts
from time import time

JSON_PATH = "resources/products.json"
TESTS = 10

products = []
error_count = 0

print(f"Running {TESTS} tests...\n")
start = time()
for _ in range(TESTS):
    products = getProducts(JSON_PATH)
    for prod in products:
        if (prod.price is None):
            error_count += 1
            break
elapsed = time()-start


list_str = ""
for prod in products:
    list_str += "\t"+str(prod)+"\n"
out_str = (
        f"Stats for the parsing of {len(products)} products:\n"
        f"Average time = {(elapsed/TESTS):.3f} ({((elapsed/TESTS)/len(products)):.3f}/product)\n"
        f"Correctness = {TESTS-error_count}/{TESTS}\n"
        f"Product list = [\n{list_str}]"
    )

print(out_str)