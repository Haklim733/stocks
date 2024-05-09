""" this module defines functions to retrieve data from the TD Ameritrade API"""

import json
import logging
import boto3
import requests
from requests.exceptions import RequestException
import pandas as pd

logger = logging.getLogger(__name__)

BASE_URL = "https://api.schwabapi.com/marketdata/v1"


def get_ssm_param(parameter_path):
    """function retrieves value from systems manager parameter store"""
    ssm = boto3.client("ssm", region_name="us-east-1")
    resp = ssm.get_parameter(Name=parameter_path, WithDecryption=True)
    return resp["Parameter"]["Value"]


def get_fundamentals(ticker: str, td_consumer_key: str):
    """retrieves fundamental data from TDAMERITRADE"""
    url = f"{BASE_URL}{ticker}&projection=fundamental"
    page = requests.get(url=url, params={"apikey": td_consumer_key})
    content = json.loads(page.content)
    return content


def get_options_data(
    ticker: str,
    underlying_quote: bool = True,
    start_date: str = None,
    end_date: str = None,
    contract_type: str = None,
    strike_count: int = None,
    strategy: str = None,
):
    """function to get options data by ticker and date"""

    params = {
        "&symbol": ticker,
        "&includesUnderlyingQuote": underlying_quote,
        "&fromDate": start_date,
        "&toDate": end_date,
        "&contractType": contract_type,
        "&strikeCount": strike_count,
        "&strategy": strategy,
    }

    filtered_params = {k: v for k, v in params.items() if v is not None}

    response = requests.get(url=f"{BASE_URL}/chains", params=filtered_params)

    try:
        response.raise_for_status()
    except RequestException as err:
        logger.critical(f"HTTP ERROR: {err.args}")
        raise
    except Exception as err:
        logger.critical(f"ERROR: {err.args}")
        raise

    content = json.loads(response.content)
    return content


def convert_dict_to_df(content: dict) -> pd.DataFrame:
    """parses dictionary returned from TDAMERITRADE api to pandas dataframe"""
    mylist = []
    for expiry, values in content.values():
        for strike in values.keys():
            mylist.append(values[strike][0])
    return pd.DataFrame(mylist)


def get_instrument(ticker: str, projection: str, td_consumer_key: str) -> dict:
    """retrieves data from table specified by projection keyword"""
    url = (
        f"https://api.tdameritrade.com/v1/instruments?&symbol={ticker}&"
        f"projection={projection}"
    )
    page = requests.get(url=url, params={"apikey": td_consumer_key})
    content = json.loads(page.content)
    return content


def main(ticker: str) -> pd.DataFrame:
    content = get_options_data(ticker)
    put = convert_dict_to_df(content["putExpDateMap"])
    call = convert_dict_to_df(content["callExpDateMap"])
    df = pd.concat(put, call)
    return df
