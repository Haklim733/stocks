""" this file tests the lambda function to work properly """
from datetime import datetime
from pytz import timezone
import json
import time
import os
from pathlib import Path
import sys
import awswrangler as wr
import boto3
from loguru import logger
import pandas as pd
import requests
from requests.exceptions import RequestException
import pandas_market_calendars as mcal
import tdameritrade as TD
import static_vars

logger.remove()
logger.add(sys.stderr,
           level="INFO",
           format="{time: YYYY-MM-DD at HH:mm:ss} | {level:<8} | {name: ^15} "
           "|{function: ^15} | {line: >3} | {message}",
           colorize=True,
           backtrace=False)

# S3_CLIENT = boto3.client('s3', endpoint_url='http://172.17.0.1:4572')
BUCKET = os.environ['S3_BUCKET']
KEY = os.environ['S3_KEY']
HOOK_URL = os.environ['FAIL_NOTIFICATION_DEST']
TICKERS = static_vars.tickers
COLUMN_TYPES = static_vars.options_col_types

NOW = datetime.now()
API_CALL_TIME = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
START_DATE = API_CALL_TIME[0:10]
END_DATE = API_CALL_TIME[0:10]
NYSE_SCHEDULE = mcal.get_calendar('NYSE').schedule(start_date=START_DATE, end_date=END_DATE)


def lambda_handler(event, context):
    ''' lambda function that will run on schedule every hour, once at 9:30 EST,
    then 10-4 with 3:45pm included'''
    if NYSE_SCHEDULE.empty:
        pass
    else:
        start_time = time.time()
        fail_list = []
        dfs = []

        for idx, ticker in enumerate(TICKERS):
            if idx != 0 and idx % 115 == 0:
                time.sleep(13)
            try:
                df = TD.get_options_data(ticker)
                dfs.append(df)
            except Exception as err:
                print(f"failed to dl {ticker}, {time.time()-start_time}"\
                                f"sec from the start")
                logger.critical(f"failed to dl {ticker}, {time.time()-start_time}"\
                                f"sec from the start; {err.args}")
                fail_list.append(ticker)
        
        if fail_list:
            message = json.dumps({'time': API_CALL_TIME, 'tickers': fail_list})
            res = requests.post(HOOK_URL, json=message)
            logger.info(res)

        dfs = pd.concat(dfs)
        dfs.reset_index(drop=True, inplace=True)

        dl_tickers = set([x.split('_')[0] for x in dfs.symbol.tolist()])

        logger.info(f"{dl_tickers} downloaded")
        
        dfs['year'] = NOW.year
        dfs['month'] = NOW.month
        dfs['day'] = NOW.day
        dfs['api_call_time'] = NOW

        s3_file_path = f"s3://{BUCKET}/{KEY}/"
        wr.catalog.sanitize_dataframe_columns_names(dfs)

        for x in ['delta', 'gamma', 'theta', 'rho', 'theoretical_option_value']:
            dfs[x] = dfs[x].astype(float)

        wr.s3.to_parquet(df=dfs,
                        path=s3_file_path,
                        sanitize_columns=False,
                        dataset=True,
                        partition_cols=['year', 'month', 'day'],
                        database='stocks',
                        table='options',
                        mode='append',
                        dtype=COLUMN_TYPES)
        #writing with partition cols and dataset=True without year and month as
        #columns and values does not result in an athena queryable  table by year
        #month
        logger.info(f"end time: {time.time() - start_time}")