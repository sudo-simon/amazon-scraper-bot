# Jaf's AWS - Amazon Web Scraper Telegram bot

Python web scraper for Amazon offers with Telegram bot integration

Developed and tested with Python 3.8.10


## Required python libraries

- beautifulsoup4
- pyTelegramBotAPI
- python-dotenv
- requests
- schedule

All are automatically installed by the [pip.sh](pip.sh) script via pip, or just use your favourite package manager.


## How to use

Run [main.py](src/main.py) once to create all the needed local files, then fill the ".env" file generated this way with your Telegram bot token and your Telegram ID ([MY_ID_getter.py](src/MY_ID_getter.py) can be used to retrieve your Telegram ID).

Server terminal:
```sh
cd src
nohup python3 main.py
```