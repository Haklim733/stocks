""" this file tests the lambda function to work properly """

import boto3
from datetime import datetime
import logging
import os

import pandas_market_calendars as mcal
from assets.static_vars import tickers

logger = logging.getLogger(__name__)

QUEUE_URL = os.environ["QUEUE_URL"]
STAGE = os.environ["STAGE"]

NOW = datetime.now()
API_CALL_TIME = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
START_DATE = API_CALL_TIME[0:10]
END_DATE = API_CALL_TIME[0:10]
NYSE_SCHEDULE = mcal.get_calendar("NYSE").schedule(
    start_date=START_DATE, end_date=END_DATE
)


def handler(event, context):

    print(API_CALL_TIME)
    print(NYSE_SCHEDULE)

    client = boto3.client("sqs")

    if STAGE == "dev":
        client.send_message(QueueUrl=QUEUE_URL, MessageBody=tickers[0])
        return

    if NYSE_SCHEDULE.empty:
        message = f"{API_CALL_TIME} is not within the NYSE_SCHEDULE ({NYSE_SCHEDULE})"
        logger.info(message)
        return

    for ticker in tickers:
        client.send_message(QueueUrl=QUEUE_URL, MessageBody=ticker)
        print(f"Sent message: {ticker}")
