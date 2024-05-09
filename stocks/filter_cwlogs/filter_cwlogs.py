""" this module sends error logs from the SaveOptionsStack lamba functions to
a slack channel"""

# %%
from datetime import datetime
import gzip
import base64
from io import BytesIO
import os
import json
from pytz import timezone
import requests

HOOK_URL = os.getenv("SLACK_URL")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

# %%
TZ_EST = timezone("America/New_York")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# %%
def handler(event, context):
    """function converts utc to EST and sends to slack channel"""
    cw_data = str(event["awslogs"]["data"])
    cw_logs = gzip.GzipFile(
        fileobj=BytesIO(base64.b64decode(cw_data, validate=True))
    ).read()
    log_events = json.loads(cw_logs)
    for event in log_events["logEvents"]:
        est_datetime = TZ_EST.fromutc(datetime.fromtimestamp(event["timestamp"] / 1000))
        event["time"] = est_datetime.strftime(TIME_FORMAT)

    slack_data = {"channel": SLACK_CHANNEL, "text": str(log_events)}
    res = requests.post(HOOK_URL, json=slack_data)
    res.raise_for_status()
