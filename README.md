# amazon-scraper-bot

Python web scraper for Amazon offers with Telegram bot integration

Developed and tested with Python 3.8.10


## Required python lybraries

- requests
- beautifulsoup4
- schedule
- pyTelegramBotAPI
- python-dotenv

All are automatically installed by the [init.sh](init.sh) script via pip, or you can use your favourite package manager


## How to run

Run once to create all the needed local files, then fill the ".env" file generated this way ([MY_ID_getter.py](src/MY_ID_getter.py) can be used to retrieve your Telegram ID)

Server terminal:
```sh
cd src
nohup python3 main.py
```