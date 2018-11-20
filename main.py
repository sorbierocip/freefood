# [START gae_python37_render_template]
from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
import urllib3
import time
import traceback
import logging
import re
from queue import Queue
from multiprocessing.pool import ThreadPool

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


urllib3.disable_warnings()
app = Flask(__name__)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/')
def root():
    return render_template('index.html')

@app.route('/couponList')
def couponList():
    return render_template('couponList.html')

@app.route('/support')
def support():
    return render_template('support.html')

pool = ThreadPool(processes=10)
@app.route('/get_data', methods=['POST'])
def get_data():


    content = request.form
    if content is None:
        raise InvalidUsage('CEP, Number and coupon value are required', status_code=400)
    if 'cep' not in content or 'number' not in content or 'couponValue' not in content:
        raise InvalidUsage('CEP, Number and coupon value are required', status_code=400)

    if re.match('\d{5}\-\d{3}', content['cep']):
        cep = content['cep'].replace('-', '')
    else:
        raise InvalidUsage('CEP is not in correct format', status_code=400)

    if re.match('\d+', content['number']):
        number = content['number']
    else:
        raise InvalidUsage('Number is not in correct format', status_code=400)

    if re.match('\d+,\d{2}', content['couponValue']):
        value = float(content['couponValue'].replace(',','.'))
    else:
        raise InvalidUsage('Coupon value is not in correct format', status_code=400)

    try:
        sess = requests.session()

        sess.verify = False
        sess.get('https://www.ifood.com.br/')

        location = sess.post('https://www.ifood.com.br/location/by-zip-code',
                             data={
                                 'zipCode': cep,
                                 'address': '',
                                 'streetNumber': number
                             },
                             headers={'X-Requested-With': 'XMLHttpRequest'}
                             ).json()['Records'][0]

        sess.post('https://www.ifood.com.br/lista-restaurantes',
                  data={
                      'location.locationId': location['locationId'],
                      'location.lat': location['lat'],
                      'location.lon': location['lon'],
                      'location.zipCode': location['zipCode'],
                      'location.district': location['district'],
                      'location.city': location['city'],
                      'location.state': location['state'],
                      'location.country': location['country'],
                      'location.address': location['address'],
                      'location.requireCompl': location['requireCompl'],
                      'compl': '',
                      'alias': '',
                      'reference': '',
                      'streetNumber': number
                  })

        page = 1
        no_stop = True
        stores = []
        q = Queue()
        while no_stop:
            list_store_page = sess.post('https://www.ifood.com.br/lista-restaurantes/filtro',
                                        data=
                                        {
                                            'page': page,
                                            'locationId': location['locationId'],
                                            'city': '',
                                            'state': '',
                                            'ordenacao': '0',
                                            'free-delivery': 'on'
                                        })

            soup = BeautifulSoup(list_store_page.content, 'html.parser')

            stores_link = soup.find_all('a', class_='restaurant-card-link')
            for storeLink in stores_link:
                if 'open' in storeLink('article')[0]['class']:
                    data = {'rid': storeLink['data-rid'],
                                   'url': 'https://www.ifood.com.br/' + storeLink['href'],
                                   'name': storeLink['data-name']}
                    stores.append(data)
                    q.put(data)
                else:
                    no_stop = False
            page = page + 1

        thread_list = []
        for x in range(0, 10):
            async_result = pool.apply_async(processStore, (q, sess, value))
            thread_list.append(async_result)

        possible_stores = []
        for thread in thread_list:
            return_val = thread.get()
            possible_stores += return_val


        return jsonify({"success": True, "data": possible_stores})
    except Exception as ex:
        tb = traceback.format_exc()
        logging.critical('Error: Values('+cep+number+str(value)+').' + str(ex) + tb)

        raise InvalidUsage('Unable to process request. Try later.', status_code=400)


def processStore(queue, sess, value):
    result = []
    while not queue.empty():
        item = queue.get()
        if item is None:
            break

        store_page = sess.get('https://www.ifood.com.br/delivery/refresh-cart?rid=' + item['rid'] + '&_=' + str(
                int(round(time.time() * 1000))))

        item.pop('rid')
        if 'Pedido M&iacute;nimo' not in store_page.text:
            item['pedidoMinimo'] = float(0)
            result.append(item)
        else:
            soup = BeautifulSoup(store_page .content, 'html.parser')
            minium = float(
                soup.find('div', class_='clearfix minimum')('span')[1].text.replace('R$', '').strip().replace(',',
                                                                                                              '.'))
            item['pedidoMinimo'] = minium
            if minium <= value:
                result.append(item)
    return result

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
# [START gae_python37_render_template]
