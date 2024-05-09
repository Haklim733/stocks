""" this file tests the lambda function to work properly """

import logging
from pathlib import Path
import os
import time
import pandas as pd
import pytest
import stocks.schwab as TD


logger = logging.getLogger(__name__)
tickers = ["AMD"]
key = os.getenv("TD_CONSUMER_KEY")
print(key)
test_dir = Path(__file__).resolve().parent.parent.joinpath("tmp/data")
test_dir.mkdir(parents=-True, exist_ok=True)
test_file = test_dir.joinpath("full_api_call.csv")


# @pytest.mark.skipif(key is None, reason="TD_CONSUMER_KEY is not set")
def test_lambda_handler():
    start_time = time.time()
    dfs = []
    for idx, ticker in enumerate(tickers):
        df = TD.get_options_data(ticker, key)
    print(df.head9)
    logger.info(f"end time: {time.time() - start_time}")
    dfs.to_csv(
        Path(__file__).resolve().parents[2].joinpath("tmp/data/full_api_call.csv")
    )
    # dfs.to_csv(Path.cwd().parent / 'data/full_api_call.csv')


@pytest.mark.skipif(not test_file.exists(), reason="file does not exist")
def test_nulls():
    dfs = pd.read_csv(test_file)
    df1 = dfs.isna().sum()
    print(df1[df1 > 0])


@pytest.mark.skipif(not test_file.exists(), reason="file does not exist")
def test_max():

    dfs = pd.read_csv(test_file)
    cols_int = dfs.select_dtypes("int").columns

    def get_max(df, col):
        idx = df[col].idxmax()
        size = df[col].loc[idx]
        print(f" {col}: {size}")

    for col in cols_int:
        get_max(dfs, col)


@pytest.mark.skipif(not test_file.exists(), reason="file does not exist")
def test_max_len():

    dfs = pd.read_csv(test_file)

    cols_str = dfs.select_dtypes("object").columns

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
