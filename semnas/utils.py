from flask import current_app
import time, random, string
import locale

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def pad_timestamp(filename):
    name = filename.split('.')
    return name[0] + str(round(time.time())) + '.' + name[1]

def generate_passphrase(length):
    letters = string.ascii_letters
    return ''.join(random.choices(letters)[0] for i in range(length))

def number_to_currency(x):
    locale.setlocale( locale.LC_ALL, 'id_ID.UTF-8' )
    return locale.currency( x, grouping=True )