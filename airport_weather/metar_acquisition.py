import os

######### Getting data from API ########################################################################################
from py2misc.py2request.py2request import Py2Request
import pandas as pd
import xmltodict

root_url = "https://www.aviationweather.gov/"
base_url = root_url + "adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&"

raw_to_raw = lambda r: r
raw_to_str = lambda r: r.content.decode()
raw_to_dict = lambda r: xmltodict.parse(raw_to_str(r))['response']['data']['METAR']
raw_to_df = lambda r: pd.DataFrame(raw_to_dict(r))

output_trans = raw_to_dict  # enter here the function you want to use to process the raw output

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

from py2store.stores.s3_store import S3PickleStore
from py2store import user_configs, user_configs_filepath

s3_kwargs = user_configs.get('s3_nextmetar_rw', None)
if s3_kwargs is None:
    raise KeyError(f"I'll need you to specify configs for s3_nextmetar_rw in {user_configs_filepath}"
                   "(see user_configs in py2store.__init__)")

######### Store ########################################################################################
import dateutil
from py2store.utils.appendable import add_append_functionality_to_store_cls, mk_item2kv_for


def item_to_key_params_and_val(item):
    obs_time = dateutil.parser.parse(item['observation_time'])
    k = {'airport_id': item['station_id'].lower(),
         'year': obs_time.year,
         'month': obs_time.month,
         'day': obs_time.day,
         'hour': obs_time.hour}
    return k, item


key_template = '{airport_id}/d/{year}/{month:02.0f}/{day:02.0f}/{hour:02.0f}'
item2kv = mk_item2kv_for.item_to_key_params_and_val(item_to_key_params_and_val, key_template)
MyStore = add_append_functionality_to_store_cls(S3PickleStore, item2kv)
store = MyStore(**s3_kwargs)

######### Acquiring a batch of data ###################################################################################
DFLT_HOURS_BEFORE_NOW = 26
DFLT_AIRPORT_IDS = tuple(['ksfo', 'kpao'])


def acquire_metar_data(airport_ids=DFLT_AIRPORT_IDS, hours_before_now=DFLT_HOURS_BEFORE_NOW):
    for airport_id in airport_ids:
        items = gd.get_recent_metar_data(airport_id, hours_before_now)
        store.extend(items)


######### Getting data ###################################################################################
import pandas as pd


def get_all_data_as_df():
    return pd.DataFrame(store.values())


if __name__ == '__main__':
    try:
        import argh

        _acquire_metar_data = acquire_metar_data


        def acquire_metar_data(airport_ids=DFLT_AIRPORT_IDS, hours_before_now=DFLT_HOURS_BEFORE_NOW):
            airport_ids = airport_ids.split(',')
            hours_before_now = int(hours_before_now)
            return _acquire_metar_data(airport_ids, hours_before_now)


        argh.dispatch_command(_acquire_metar_data)

    except ImportError:
        print("You don't have argh: Pity (you should really ")

        acquire_metar_data()
