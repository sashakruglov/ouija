import os

import MySQLdb
from flask import Flask, g, request
from flask.json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    """Implements custom encoding to JSON"""
    def default(self, obj):
        try:
            return vars(obj)
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return super(CustomJSONEncoder, self).default(obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder


app.config.from_object('app.settings.managed_settings')

with open('environment') as infile:
    target_env = infile.readline().strip('\n')
config_path = os.path.join('settings', '%s.py' % target_env.lower())
app.config.from_pyfile(config_path)


def connect_db():
    return MySQLdb.connect(**app.config['DATABASE'])


@app.before_request
def before_request():
    if not hasattr(g, 'db') and 'api' in request.path:
        g.db = connect_db()


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        g.db.close()

from app import views
