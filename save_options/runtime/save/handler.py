""" this file tests the lambda function to work properly """

from datetime import datetime
import logging
import time
import os
import awswrangler as wr
import boto3
import pandas as pd
import assets.tdameritrade as TD
from assets.column_types import options_col_types

logger = logging.getLogger()

NOW = datetime.now()
BUCKET = os.environ["S3_BUCKET"]


def get_secure_string(parameter_name):
    """Read a secure string from AWS Systems Manager Parameter Store"""
    ssm = boto3.client("ssm")
    parameter = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


def lambda_handler(event, context):
    """lambda function that will run on schedule every hour, once at 9:30
    EST, then 10-4 and 3:45 pm. The function is triggered by a cloudwatch
    event so no filtering is necessary"""

    start_time = time.time()
    td_consumer_key = get_secure_string("/stocks/secret/td_consumer_key")

    for record in event["Records"]:
        # Get the body of the message
        ticker = record["body"]
        print(f"Received message: {ticker}")

        options_df = pd.DataFrame()
        try:
            options_df = TD.get_options_data(ticker, td_consumer_key)
        except Exception as err:
            print(
                f"failed to dl {ticker}, {time.time()-start_time}" f"sec from the start"
            )
            logger.critical(
                f"failed to dl {ticker}, {time.time()-start_time}"
                f"sec from the start; {err.args}"
            )
            options_df = TD.get_options_data(ticker)

        options_df["year"] = NOW.year
        options_df["month"] = NOW.month
        options_df["day"] = NOW.day
        options_df["api_call_time"] = NOW

        s3_file_path = f"s3://{BUCKET}/data/option/raw/year={NOW.year}/\
            month={NOW.month}/day={NOW.day}/ticker={ticker}/{NOW}.parquet"

        wr.catalog.sanitize_dataframe_columns_names(options_df)

        for col in ["delta", "gamma", "theta", "rho", "theoretical_option_value"]:
            options_df[col] = options_df[col].astype(float)

        wr.s3.to_parquet(
            df=options_df,
            path=s3_file_path,
            sanitize_columns=False,
            database="Stocks",
            table="Options",
            dtype=options_col_types,
        )
    logger.info(f"end time: {time.time() - start_time}")
