from os.path import abspath
import json


def _load_settings():
    try:
        with open(abspath(__file__ + '/../TigLoader.json'), 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    except Exception:
        return {}


def load_settings():
    settings = _load_settings()
    return settings


def save_settings(data):
    settings = {}
    for k, v in data.iteritems():
        if v is not None:
            settings[k] = v
    if not settings:
        return
    #log('save {!r}', settings)
    with open(abspath(__file__ + '/../TigLoader.json'), 'wb') as f:
        return f.write(json.dumps(settings).encode('utf-8'))
