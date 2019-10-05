import os

aws_access_key_id = os.environ['SEB_AWS_ACCESS_KEY']
aws_secret_access_key = os.environ['SEB_AWS_SECRET_KEY']

######### Getting data from API ########################################################################################
from i2i.py2request.py2request import Py2Request
import pandas as pd
import xmltodict

root_url = "https://www.aviationweather.gov/"
base_url = root_url + "adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&"

raw_to_df = lambda r: pd.DataFrame(xmltodict.parse(r.content.decode())['response']['data']['METAR'])
raw_to_dict = lambda r: xmltodict.parse(r.content.decode())['response']['data']['METAR']
raw_to_str = lambda r: r.content.decode()
raw_to_raw = lambda r: r

output_trans = raw_to_dict

method_specs = {
    'get_recent_metar_data': {
        'url_template': base_url + '&stationString={airport_id}' + '&hoursBeforeNow={hours_before_now}',
        'output_trans': output_trans
    },
    'get_metar_data_for_interval': {
        'url_template': base_url + '&stationString={airport_id}&startTime={start}&endTime={end}',
        'output_trans': output_trans
    },
}

gd = Py2Request(method_specs)

######### Persister ########################################################################################

from py2store.stores.s3_store import S3BinaryStore
import pickle

s3_kwargs = dict(bucket_name='nextmetar',
                 _prefix='',
                 resource_kwargs=dict(aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key))


class S3PickleStore(S3BinaryStore):
    def _obj_of_data(self, data):
        return pickle.loads(data)

    def _data_of_obj(self, obj):
        return pickle.dumps(obj)


s = S3PickleStore(**s3_kwargs)

######### Getting data from API ########################################################################################
import dateutil

from os.path import sep as path_sep
from string import Formatter

str_formatter = Formatter()


def add_append_functionality_to_store_cls(store_cls, item_to_key, new_store_name=None):
    """Makes a new class with append and extend capabilities"""

    if new_store_name is None:
        new_store_name = 'Appendable' + store_cls.__name__

    def append(self, item):
        self[item_to_key(item)] = item

    def extend(self, items):
        for item in items:
            self.append(item)

    return type(new_store_name, (store_cls,), {'append': append, 'extend': extend})


def add_append_functionality_to_str_key_store(store_cls,
                                              item_to_key_params,
                                              key_template=None,
                                              new_store_name=None):
    def item_to_key(item):
        nonlocal key_template
        if key_template is None:
            key_params = item_to_key_params(item)
            key_template = path_sep.join('{{{}}}'.format(p) for p in key_params)
        return key_template.format(**item_to_key_params(item))

    return add_append_functionality_to_store_cls(store_cls, item_to_key, new_store_name)


def item_to_key_params(item):
    obs_time = dateutil.parser.parse(item['observation_time'])
    return {'airport_id': item['station_id'].lower(),
            'year': obs_time.year,
            'month': obs_time.month,
            'day': obs_time.day,
            'hour': obs_time.hour}


key_template = '{airport_id}/d/{year}/{month}/{day}/{hour}'

MyStore = add_append_functionality_to_str_key_store(S3PickleStore,
                                                    item_to_key_params,
                                                    key_template=key_template)

######### Acquiring a batch of data ###################################################################################
DFLT_HOURS_BEFORE_NOW = 26
DFLT_AIRPORT_IDS = tuple(['ksfo', 'kpao'])


def acquire_metar_data(airport_ids=DFLT_AIRPORT_IDS, hours_before_now=DFLT_HOURS_BEFORE_NOW):
    s = MyStore(**s3_kwargs)
    for airport_id in airport_ids:
        items = gd.get_recent_metar_data(airport_id, hours_before_now)
        s.extend(items)


if __name__ == '__main__':
    acquire_metar_data()
    # try:
    #     import argh
    #
    #     argh.dispatch_command(acquire_metar_data)
    #
    # except ImportError:
    #     print("You don't have argh: Pity")
    #
    #     acquire_metar_data()
