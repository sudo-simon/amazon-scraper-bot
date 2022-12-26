from web_scraper.productSearch import Product, getProducts, updatePrices

JSON_PATH = "resources/products.json"
PRODUCTS = getProducts(JSON_PATH)

for product in PRODUCTS:
    print(product)
print("Done :)\n")

