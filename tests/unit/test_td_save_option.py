""" this file tests the lambda function to work properly """
from pathlib import Path
import json
import time
import sys
import boto3
from loguru import logger
import pandas as pd
import awswrangler as wr
import pyarrow as pa
from requests.exceptions import RequestException
import tdameritrade as TD

with open('../../static/options_tickers.json', 'r') as handle:
    tickers = json.load(handle)
    tickers.sort()

logger.remove()
log_filename = Path(__name__).resolve().parent / 'test_lambda_function.log'
logger.add(log_filename,
           level="INFO",
           format="{time: YYYY-MM-DD at HH:mm:ss} | {level:<8} | {name: ^15} "
           "|{function: ^15} | {line: >3} | {message}",
           colorize=True,
           backtrace=False,
           mode='w')


def test_lambda_handler():
    start_time = time.time()
    dfs = []
    for idx, ticker in enumerate(tickers):
        if idx != 0 and idx % 115 == 0:
            time.sleep(20)
        try:
            df = TD.get_options_data(ticker)
            dfs.append(df)
        except Exception as err:
            logger.critical(f"failed to dl {ticker}, {time.time()-start_time}"\
                            f"sec from the start")
    dfs = pd.concat(dfs)

    dl_tickers = [x.split('_')[0] for x in dfs.symbol.tolist()]
    logger.info(f"{dl_tickers} downloaded")
    logger.info(f"end time: {time.time() - start_time}")
    dfs.to_csv(
        Path(__file__).resolve().parent.parent / 'data/full_api_call.csv')
    # dfs.to_csv(Path.cwd().parent / 'data/full_api_call.csv')


def test_nulls():
    dfs = pd.read_csv(
        Path(__file__).resolve().parent.parent / 'data/full_api_call.csv')
    df1 = dfs.isna().sum()
    print(df1[df1 > 0])


def test_max():

    dfs = pd.read_csv(
        Path(__file__).resolve().parent.parent / 'data/full_api_call.csv')

    cols_int = dfs.select_dtypes('int').columns

    def get_max(df, col):
        idx = df[col].idxmax()
        size = df[col].loc[idx]
        print(f" {col}: {size}")

    for col in cols_int:
        get_max(dfs, col)


def test_max_len():

    dfs = pd.read_csv(
        Path(__file__).resolve().parent.parent / 'data/full_api_call.csv')

    cols_str = dfs.select_dtypes('object').columns

    def get_max_len(df, col):
        try:
            idx = df[col].apply(lambda x: len(x)).idxmax()
            value = df[col].loc[idx]
            size = len(value)
            print(f"{col}: {size}, {value}")
        except:
            print(f"nulls: {col}")

    for col in cols_str:
        logger.info(get_max_len(dfs, col))


def test_lambda():
    """ tests the lambda function. Note the lambda_function.py file in the
    lambda.zip file, has endpoint_urls that point to the approrpriate i
    localstack docker ports """
    setup_lambda(role_arn=role_arn, queue_url=queue_url)
    setup_s3()
    upload_to_s3(file_name=filename)
    objects = LSS3.list_bucket_objects(os.environ['S3_BUCKET'])
    print(f"objects in bucketlist are: {objects}")
    s3_c = LSS3.get_client()

    for item in objects:
        obj = s3_c.get_object(Bucket=os.environ['S3_BUCKET'], Key=item['Key'])
        j = json.loads(obj['Body'].read())
    print(j)


def test_tickers():
    """ tests if all the tickers have been saved, delete tickers that do not
    exist """
    df = pd.read_parquet("")
