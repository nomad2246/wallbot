#!/usr/bin/python3.5

import requests
import time
import datetime
import telebot
from dbhelper import DBHelper, ChatSearch, Item
from re import sub
from decimal import Decimal
import logging
import sys
import threading
import os

TOKEN = os.getenv("BOT_TOKEN", "Bot Token does not exist")
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
URL_ITEMS = "https://api.wallapop.com/api/v3/general/search"

db = DBHelper()

ICON_VIDEO_GAMES = u'\U0001F3AE'  # 🎮
ICON_WARNING____ = u'\U000026A0'  # ⚠️
ICON_HIGH_VOLTAG = u'\U000026A1'  # ⚡️
ICON_COLLISION__ = u'\U0001F4A5'  # 💥
ICON_EXCLAMATION = u'\U00002757'  # ❗
ICON_DIRECT_HIT_ = u'\U0001F3AF'  # 🎯


def notel(chat_id, price, title, url_item, obs=None):
    # https://apps.timwhitlock.info/emoji/tables/unicode
    if obs is not None:
        text = ICON_EXCLAMATION
    else:
        text = ICON_DIRECT_HIT_
    text += ' *' + title + '*'
    text += '\n'
    if obs is not None:
        text += ICON_COLLISION__ + ' '
    text += price
    if obs is not None:
        text += obs
        text += ' ' + ICON_COLLISION__
    text += '\n'
    text += 'https://es.wallapop.com/item/'
    text += url_item
    urlz0rb0t = URL + "sendMessage?chat_id=%s&parse_mode=markdown&text=%s" % (chat_id, text)
    requests.get(url=urlz0rb0t)


def get_url_list(search):
    url = URL_ITEMS
    url += '?keywords='
    url += "+".join(search.kws.split(" "))
    if search.cat_ids is not None:
        url += '&category_ids='
        url += search.cat_ids
    if search.min_price is not None:
        url += '&min_sale_price='
        url += search.min_price
    if search.max_price is not None:
        url += '&max_sale_price='
        url += search.max_price
    if search.dist is not None:
        url += '&dist='
        url += search.dist
    if search.publish_date is not None:
        url += '&publishDate='
        url += str(search.publish_date)
    if search.orde is not None:
        url += '&order='
        url += search.orde
    return url


def get_items(url, chat_id):
    try:
        resp = requests.get(url=url)
        data = resp.json()
        # print(data)
        for x in data['search_objects']:
            print(x)
            print('\t'.join((datetime.datetime.today().strftime('%Y-%m-%d %H:%M'),
                             str(x['id']), str(x['price']), x['title'], x['user']['id'])))
            i = db.search_item(x['id'], chat_id)
            if i is None:
                db.add_item(x['id'], chat_id, x['title'], x['price'], x['web_slug'], x['user']['id'])
                notel(chat_id, str(x['price']), x['title'], x['web_slug'])
                print('\t'.join((datetime.datetime.today().strftime('%Y-%m-%d %H:%M'),
                                 'NEW ', str(x['id']), str(x['price']), x['title'])))
            else:
                # Si está comparar precio...
                money = str(x['price'])
                value_json = Decimal(sub(r'[^\d.]', '', money))
                value_db = Decimal(sub(r'[^\d.]', '', i.price))
                if value_json < value_db:
                    new_obs = i.price
                    if i.observaciones is not None:
                        new_obs += ' < '
                        new_obs += i.observaciones
                    db.update_item(x['id'], money, new_obs)
                    obs = ' < ' + new_obs
                    notel(chat_id, x['price'], x['title'], x['web_slug'], obs)
                    print('\t'.join((datetime.datetime.today().strftime('%Y-%m-%d %H:%M'),
                                     'BAJA', str(x['id']), x['price'], x['title'])))
    except Exception as e:
        print(e)


# INI Actualización de db a partir de la librería de Telegram
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start', 'help', 's', 'h'])
def send_welcome(message):
    bot.send_message(message.chat.id, ("*Utilización*\n"
                                       "/help\n"
                                       "*Añadir búsquedas:*\n"
                                       "\t/add `búsqueda,min-max`\n"
                                       "\t/add zapatos rojos,5-25\n"
                                       "*Borrar búsqueda:*\n"
                                       "\t/del `búsqueda`\n"
                                       "\t/del zapatos rojos\n"
                                       "*Lista de búsquedas:*\n"
                                       "\t/lis",)
                     , parse_mode='Markdown')


@bot.message_handler(commands=['del', 'borrar', 'd'])
def delete_search(message):
    parametros = str(message.text).split(' ', 1)
    if len(parametros) < 2:
        # Solo puso el comando
        return
    db.del_chat_search(message.chat.id, ' '.join(parametros[1:]))


@bot.message_handler(commands=['lis', 'listar', 'l'])
def get_searchs(message):
    text = ''
    for chat_search in db.get_chat_searchs(message.chat.id):
        if len(text) > 0:
            text += '\n'
        text += chat_search.kws
        text += '|'
        if chat_search.min_price is not None:
            text += chat_search.min_price
        text += '-'
        if chat_search.max_price is not None:
            text += chat_search.max_price
        if chat_search.cat_ids is not None:
            text += '|'
            text += chat_search.cat_ids
    if len(text) > 0:
        bot.send_message(message.chat.id, (text,))


# /add búsqueda,min-max,categorías separadas por comas
@bot.message_handler(commands=['add', 'añadir', 'append', 'a'])
def add_search(message):
    cs = ChatSearch()
    cs.chat_id = message.chat.id
    parametros = str(message.text).split(' ', 1)
    if len(parametros) < 2:
        # Solo puso el comando
        return
    token = ' '.join(parametros[1:]).split(',')
    if len(token) < 1:
        # Puso un espacio después del comando, nada más
        return
    cs.kws = token[0].strip()
    if len(token) > 1:
        rango = token[1].split('-')
        cs.min_price = rango[0].strip()
        if len(rango) > 1:
            cs.max_price = rango[1].strip()
    if len(token) > 2:
        cs.cat_ids = sub('[\s+]', '', ','.join(token[2:]))
        if len(cs.cat_ids) == 0:
            cs.cat_ids = None
    cs.username = message.from_user.username
    cs.name = message.from_user.first_name
    cs.active = 1
    print(cs)
    db.add_search(cs)


# @bot.message_handler(func=lambda message: True)
# def echo_all(message):
#     print('echo: "' + message.text + '"')
#     bot.reply_to(message, message.text)

logger = telebot.logger
formatter = logging.Formatter('[%(asctime)s] %(thread)d {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
                              '%m-%d %H:%M:%S')
ch = logging.StreamHandler(sys.stdout)
logger.addHandler(ch)
logger.setLevel(logging.ERROR)  # or use logging.INFO
ch.setFormatter(formatter)


# FIN

def wallapop():
    while True:
        # Recupera de db las búsquedas que hay que hacer en wallapop con sus respectivos chats_id
        for search in db.get_chats_searchs():
            u = get_url_list(search)

            # Lanza las búsquedas y notificaciones ...
            get_items(u, search.chat_id)

        # Borrar items antiguos (> 24hrs?)
        # No parece buena idea. Vuelven a entrar cada 5min algunos
        # db.deleteItems(24)

        time.sleep(300)
        continue


# def recovery(times):
# try:
#        bot.polling(none_stop=True, timeout=600)
# except Exception as e:
#    print("¡¡¡ERROR!!! %s intento" % (times, ))
#    print(times)
#    print(datetime.datetime.today().strftime('%Y-%m-%d %H:%M'))
#    print(e)
#    recovery(times+1)


def main():
    print("JanJanJan starting...")
    db.setup()

    threading.Thread(target=wallapop).start()

    # recovery(1)
    bot.polling(none_stop=True, timeout=3000)


if __name__ == '__main__':
    main()
