import boto3
import requests
from requests.exceptions import RequestException
import os
import json
import pandas as pd

CONSUMER_KEY = os.environ.get('TD_CONSUMER_KEY')
ACCESS_KEY = os.environ.get('TD_ACCESS_KEY')
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_KEY = os.environ.get('S3_KEY')


def get_fundamentals(ticker: str):
    url =f'https://api.tdameritrade.com/v1/instruments?&symbol='\
            f'{ticker}&projection=fundamental'
    headers = {'Authorization': ACCESS_KEY}
    page = requests.get(url=url, params={'apikey': CONSUMER_KEY})
    content = json.loads(page.content)
    return content


def get_options_data(ticker: str,
                     start_date: str = None,
                     end_date: str = None):
    """ function to get options data by ticker and date """

    url = f"https://api.tdameritrade.com/v1/marketdata/chains?&symbol="\
          f"{ticker}"

    if start_date:
        url = url + f"&fromDate={start_date}"
    if end_date:
        url = url + f"&toDate={end_date}"

    headers = {'Authorization': ACCESS_KEY}
    page = requests.get(url=url, params={'apikey': CONSUMER_KEY})

    try:
        page.raise_for_status()
    except RequestException as err:
        logger.critical(f"HTTP ERROR: {err.args}")
        raise
    except Exception as err:
        logger.critical(f"ERROR: {err.args}")
        raise

    content = json.loads(page.content)

    if 'error' in content:
        raise KeyValueError('check inputs')

    put = convert_dict_to_df(content['putExpDateMap'])
    call = convert_dict_to_df(content['callExpDateMap'])
    return put.append(call)


def convert_dict_to_df(option_dict: dict) -> pd.DataFrame:
    mylist = []
    for expiry, values in option_dict.items():
        for strike in values.keys():
            mylist.append(values[strike][0])
    return pd.DataFrame(mylist)


def get_instrument(ticker: str, projection: str) -> dict:
    url =f"https://api.tdameritrade.com/v1/instruments?&symbol={ticker}&"\
         f"projection={projection}"
    headers = {'Authorization': ACCESS_KEY}
    page = requests.get(url=url, params={'apikey': CONSUMER_KEY})
    content = json.loads(page.content)
    return content
