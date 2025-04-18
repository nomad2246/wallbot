#!/usr/bin/python3.5

import requests
import time
import telebot
import logging
import threading
import os
import locale
from dbhelper import DBHelper, ChatSearch, Item
from re import sub
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from telebot import TeleBot
from telebot import types
from telebot.types import InputMediaPhoto, InputMediaVideo
from datetime import datetime
from urllib.parse import urlparse

TOKEN = os.getenv("BOT_TOKEN", "Bot Token does not exist")
URL_ITEMS = "https://api.wallapop.com/api/v3/general/search"
URL_CATEGORIES = "https://api.wallapop.com/api/v3/categories"
PROFILE = os.getenv("PROFILE")

if PROFILE is None:
    db = DBHelper()
else:
    db = DBHelper("db.sqlite")


ICON_VIDEO_GAMES = u'\U0001F3AE'  # 🎮
ICON_WARNING____ = u'\U000026A0'  # ⚠️
ICON_HIGH_VOLTAG = u'\U000026A1'  # ⚡️
ICON_COLLISION__ = u'\U0001F4A5'  # 💥
ICON_EXCLAMATION = u'\U00002757'  # ❗
ICON_DIRECT_HIT_ = u'\U0001F3AF'  # 🎯


def notel(chat_id, price, title, url_item, obs=None, images=None):
    if obs is not None:
        text = ICON_EXCLAMATION
    else:
        text = ICON_DIRECT_HIT_
    text += ' <b>' + title + '</b>'
    text += '\n'
    if obs is not None:
        text += ICON_COLLISION__ + ' '
    text += locale.currency(price, grouping=True)
    if obs is not None:
        text += obs
        text += ' ' + ICON_COLLISION__
    text += '\n'
    text += 'https://it.wallapop.com/item/'
    text += url_item

    #listaFotos = []
    #listaArchivos = []

    #for image in imag
    #    archivo = urlparse(image['original'])
    #    nombreArchivo = os.path.basename(archivo.path)
    #    rutaArchivo = "data/media/" + nombreArchivo

    #    response = requests.get(image['original'])
    #    open(rutaArchivo, "wb").write(response.content)

    #    listaArchivos.append(rutaArchivo)

    #    with open(rutaArchivo, 'rb') as fh:
    #        data = fh.read()
    #        media = InputMediaPhoto(data)
    #        listaFotos.append(media)

    #bot.send_media_group(chat_id, listaFotos, disable_notification=True)
    bot.send_message(chat_id, text, parse_mode="HTML")

    #for foto in listaArchivos:
    #    os.remove(foto)


def get_url_list(search):
    url = URL_ITEMS
    url += '?source=recent_searches&longitude=12.4942&latitude=41.8905&keywords='
    url += "+".join(search.kws.split(" "))
    url += '&time_filter=today'
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
    if search.orde is not None:
        url += '&order_by='
        url += search.orde
    return url


def get_items(url, chat_id):
    try:
        resp = requests.get(url=url,headers={'Accept': '*/*', 'User-Agent': 'Wget/1.21.4','Accept-Encoding': 'identity', 'X-Deviceos': '0'})
        data = resp.json()
        for x in data['search_objects']:
            logging.info('Encontrado: id=%s, price=%s, title=%s, user=%s',str(x['id']), locale.currency(x['price'], grouping=True), x['title'], x['user']['id'])
            i = db.search_item(x['id'], chat_id)
            if i is None:
                creationDate = datetime.fromisoformat(x['creation_date']).strftime('%c')
                db.add_item(x['id'], chat_id, x['title'], x['price'], x['web_slug'], x['user']['id'], creationDate)
                notel(chat_id, x['price'], x['title'], x['web_slug'], None, x['images'])
                logging.info('New: id=%s, price=%s, title=%s', str(x['id']), locale.currency(x['price'], grouping=True), x['title'])
            else:
                # Si está comparar precio...
                money = str(x['price'])
                value_json = Decimal(sub(r'[^\d.]', '', money))
                value_db = Decimal(sub(r'[^\d.]', '', i.price))
                if value_json < value_db:
                    new_obs = locale.currency(i.price, grouping=True)
                    if i.observaciones is not None:
                        new_obs += ' < '
                        new_obs += i.observaciones
                    db.update_item(x['id'], money, new_obs)
                    obs = ' < ' + new_obs
                    notel(chat_id, x['price'], x['title'], x['web_slug'], obs)
                    logging.info('Baja: id=%s, price=%s, title=%s', str(x['id']), locale.currency(x['price'], grouping=True), x['title'])
    except Exception as e:
        logging.error(e)


def get_categories(url):
    try:
        resp = requests.get(url=url, headers={'Accept': '*/*', 'User-Agent': 'Wget/1.21.4','Accept-Encoding': 'identity', 'X-Deviceos': '0'})
        data = resp.json()
        return data
    
    except Exception as e:
        logging.error(e)


def handle_exception(self, exception):
    logging.exception(exception)
    logging.error("Ha ocurrido un error con la llamada a Telegram. Se reintenta la conexión")
    print("Ha ocurrido un error con la llamada a Telegram. Se reintenta la conexión")
    bot.polling(none_stop=True, timeout=3000)


# INI Actualización de db a partir de la librería de Telegram
# bot = telebot.TeleBot(TOKEN, exception_handler=handle_exception)
bot = telebot.TeleBot(TOKEN)
cs = ChatSearch()

@bot.message_handler(commands=['start', 'help', 'menu', 's', 'h', 'm'])
def send_test(message):
    inicio(message)


@bot.callback_query_handler(lambda call: call.data == "añadir")
def process_callback_añadir(call):
    añadir(call)


@bot.callback_query_handler(lambda call: call.data == "listar")
def process_callback_listar(call):
    listar(call)


@bot.callback_query_handler(lambda call: call.data == "borrar")
def process_callback_borrar(call):
    borrar(call)


@bot.callback_query_handler(lambda call: call.data == "categorias")
def process_callback_categorias(call):
    categorias(call)


def inicio(call):
    boton_añadir = types.InlineKeyboardButton('Add', callback_data='añadir')
    boton_listar = types.InlineKeyboardButton('List', callback_data='listar')
    boton_borrar = types.InlineKeyboardButton('Delete', callback_data='borrar')
    boton_categorias = types.InlineKeyboardButton('Categories', callback_data='categorias')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(boton_añadir, boton_listar)
    keyboard.row(boton_borrar, boton_categorias)

    bot.send_message(call.chat.id, text='Selecciona una acción a realizar', reply_markup=keyboard)


def añadir(call):
    busqueda = bot.send_message(call.message.chat.id,  'write search query:')
    bot.register_next_step_handler(busqueda, guardarBusqueda)


def guardarBusqueda(message):
    cs.chat_id = message.chat.id
    cs.kws = message.text

    rangoPrecio = bot.send_message(message.chat.id,  'write price range (min-max):')
    bot.register_next_step_handler(rangoPrecio, guardarRangoPrecio)


def guardarRangoPrecio(message):
    rango = message.text.split('-')
    cs.min_price = rango[0].strip()
    if len(rango) > 1:
        cs.max_price = rango[1].strip()

    cs.username = message.from_user.username
    cs.name = message.from_user.first_name
    cs.active = 1

    data = get_categories(URL_CATEGORIES)
    keyboard = types.InlineKeyboardMarkup()
    boton = types.InlineKeyboardButton(All , callback_data='categoria,' + "all")
    for x in data['categories']:
        boton = types.InlineKeyboardButton(str(x['name']), callback_data='categoria,' + str(x['id']))
        keyboard.add(boton)

    bot.send_message(message.chat.id, text='Select category', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    catAux = call.data.split(',')
    if catAux[0] == "categoria":
        categoriaId = catAux[1]
        call.message.text = categoriaId
        guardarCategoria(call)


def guardarCategoria(call):
    cs.cat_ids = call.message.text
    if call.message.text == 'all':
        cs.cat_ids = None
    logging.info('%s', cs)
    db.add_search(cs)
    bot.send_message(call.message.chat.id, "Search saved")


def borrar(call):
    busquedaBorrar = bot.send_message(call.message.chat.id,  'Select search to delete:')
    bot.register_next_step_handler(busquedaBorrar, borrarBusqueda)


def borrarBusqueda(call):
    db.del_chat_search(call.chat.id, call.text)
    bot.send_message(call.chat.id, "Search deleted")


def listar(call):
    text = ''

    for chat_search in db.get_chat_searchs(call.message.chat.id):
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
        bot.send_message(call.message.chat.id, (text,))


def categorias(call):
    data = get_categories(URL_CATEGORIES)

    texto = "*Categorias:*\n\n"

    for x in data['categories']:
        texto += "*" + str(x['name']) + "*\n"
        texto += "\t`" + str(x['id']) + "`\n"

    bot.send_message(call.message.chat.id, texto, parse_mode='Markdown')


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
    logging.info('%s', cs)
    db.add_search(cs)


pathlog = 'wallbot.log'
if PROFILE is None:
    pathlog = '/logs/' + pathlog

logging.basicConfig(
    handlers=[RotatingFileHandler(pathlog, maxBytes=1000000, backupCount=10, encoding='utf-8')],
#    filename='wallbot.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')


# FIN

def wallapop():
    while True:
        # Recupera de db las búsquedas que hay que hacer en wallapop con sus respectivos chats_id
        for search in db.get_chats_searchs():
            u = get_url_list(search)

            # Lanza las búsquedas y notificaciones ...
            get_items(u, search.chat_id)

        time.sleep(180)
        continue


def recovery(times):
    try:
        time.sleep(times)
        logging.info("Conexión a Telegram.")
        print("Conexión a Telegram")
        bot.polling(none_stop=True, timeout=3000)
    except Exception as e:
        logging.error("Ha ocurrido un error con la llamada a Telegram. Se reintenta la conexión", e)
        print("Ha ocurrido un error con la llamada a Telegram. Se reintenta la conexión")
        if times > 16:
            times = 16
        recovery(times*2)


def main():
    print("JanJanJan starting...")
    logging.info("JanJanJan starting...")
    db.setup(readVersion())
    threading.Thread(target=wallapop).start()
    recovery(1)


def readVersion():
    file = open("VERSION", "r")
    version = file.readline()
    logging.info("Version %s", version)
    return version


if __name__ == '__main__':
    main()
