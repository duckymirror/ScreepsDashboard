import screepsapi
from screepsdashboard.services.cache import cache

from screepsdashboard import app

def get_client():
    user = app.config['screeps_user']
    password = app.config['screeps_password']
    return screepsapi.API(user, password)


def get_gcl(user):
    return get_me().get('gcl', 0)


def get_power():
    return get_me().get('power', 0)


def get_credits():
    return get_me().get('credits', 0)


@cache.cache(expire=120)
def get_me():
    client = get_client()
    me = client.me()
    sanitize = ['gcl', 'power', 'credits']
    for key in sanitize:
        if key not in me:
            me[key] = 0
    return me


@cache.cache(expire=120)
def get_memory(shard, path=''):
    client = get_client()
    memory = client.memory(path, shard)
    return memory


@cache.cache(expire=120)
def get_segment(shard, segmentid):
    client = get_client()
    segment = client.get_segment(segmentid, shard)
    return segment

@cache.cache(expire=120)
def get_shards():
    client = get_client()
    return client.get_shards()



get_shards


def import_socket():
    screepsconsole = ScreepsConsole(
        user=app.config['screeps_user'],
        password=app.config['screeps_password'],
        ptr=app.config('screeps_ptr', False),
    )
    screepsconsole.set_es_host(
        host=app.config('es_host', 'localhost'),
        index_prefix=app.config('es_index_prefix', 'screepsdash-%s-' % (app.config['screeps_user'],)),
    )
    screepsconsole.start()




## Python before 2.7.10 or so has somewhat broken SSL support that throws a warning; suppress it
import warnings; warnings.filterwarnings('ignore', message='.*true sslcontext object.*')

class ScreepsConsole(screepsapi.Socket):

    def set_es_host(self, host='localhost', index_prefix='screepsdash-'):
        self.es = Elasticsearch([host])
        self.index_prefix = index_prefix

    def set_subscriptions(self):
        self.subscribe_user('console')
        self.subscribe_user('cpu')

    def process_log(self, ws, message):

        message_soup = BeautifulSoup(message,  "lxml")
        body = {
            'timestamp': datetime.now(),
            'mtype': 'log'
        }

        if message_soup.log:
            tag = message_soup.log
        elif message_soup.font:
            tag = message_soup.font
        else:
            tag = False

        if tag:
            for key,elem in tag.attrs.items():
                if key == 'color':
                    continue

                # If it's an integer convert it from string
                if elem.isdigit():
                    body[key] = int(elem)
                    continue

                # Check to see if it is a float
                try:
                    newelem = float(elem)
                    body[key] = newelem
                except ValueError:
                    pass

                # Okay fine it's a string
                body[key] = elem

        message_text = message_soup.get_text()
        body['message_raw'] = message_text
        message_text.strip()
        body['message'] = message_text.replace("\t", ' ')
        res = self.es.index(index="screeps-console-" + time.strftime("%Y_%m"), doc_type="log", body=body)

    def process_results(self, ws, message):
        body = {
            'timestamp': datetime.now(),
            'message': message,
            'mtype': 'results'
        }
        res = self.es.index(index="screeps-console-" + time.strftime("%Y_%m"), doc_type="log", body=body)

    def process_error(self, ws, message):
        body = {
            'timestamp': datetime.now(),
            'message': message,
            'mtype': 'error',
            'severity': 5
        }
        res = self.es.index(index="screeps-console-" + time.strftime("%Y_%m"), doc_type="log", body=body)

    def process_cpu(self, ws, data):
        body = {
            'timestamp': datetime.now()
        }

        if 'cpu' in data:
            body['cpu'] = data['cpu']

        if 'memory' in data:
            body['memory'] = data['memory']

        if 'cpu' in data or 'memory' in data:
            res = self.es.index(index="screeps-performance-" + time.strftime("%Y_%m"), doc_type="performance", body=body)