# %%
import json
from typing import List
import boto3
from datetime import datetime
from pathlib import Path
from pytz import timezone

# %%
current_tz = timezone("Asia/Seoul")
session = boto3.Session(profile_name="prod")
cwlogs = session.client("logs", region_name="us-east-1")
log_group_name = "/aws/lambda/SaveOptionsData"
# %%
response = cwlogs.describe_log_streams(
    logGroupName="/aws/lambda/SaveOptionsData", limit=50, orderBy="LastEventTime"
)

# %%
_paginator = cwlogs.get_paginator("describe_log_streams")
paginate_args = {"MaxItems": 50, "PageSize": 50}
resp_iterator = _paginator.paginate(
    logGroupName=log_group_name,
    orderBy="LastEventTime",
    descending=True,
    PaginationConfig=paginate_args,
)


# %%
def get_logstreams_names(
    log_group_name: str, log_stream_names: List = None, token: str = None
):

    if not log_stream_names:
        log_stream_names = []

    _paginator = cwlogs.get_paginator("describe_log_streams")

    paginate_args = {"MaxItems": 50, "PageSize": 50}
    if token:
        paginate_args.update({"StartingToken": token})

    resp_iterator = _paginator.paginate(
        logGroupName=log_group_name,
        orderBy="LastEventTime",
        descending=True,
        PaginationConfig=paginate_args,
    )

    for page in resp_iterator:
        for record in page["logStreams"]:
            log_stream_names.append(record["logStreamName"])

    if "nextToken" in page:
        get_logstreams_names(
            log_group_name=log_group_name,
            log_stream_names=log_stream_names,
            token=page["nextToken"],
        )
    return log_stream_names


# %%
stream_names = get_logstreams_names(log_group_name=log_group_name)


# %%
def filter_logs(
    log_group_name: str,
    log_stream_names: List,
    filter_pattern: str,
    interleaved=False,
    result_list: List = None,
):

    _log_stream_names = log_stream_names.copy()

    if not result_list:
        result_list = []

    _resp = cwlogs.filter_log_events(
        logGroupName=log_group_name,
        logStreamNames=_log_stream_names,
        filterPattern=filter_pattern,
        interleaved=interleaved,
    )
    result_list += _resp["events"]

    for log_stream in _resp["searchedLogStreams"]:
        if log_stream["searchedCompletely"]:
            _log_stream_names.remove(log_stream["logStreamName"])

    if "nextToken" in _resp:
        filter_logs(
            log_group_name=log_group_name,
            log_stream_names=_log_stream_names,
            filter_pattern=filter_pattern,
            interleaved=interleaved,
            result_list=result_list,
        )
    return result_list


def chunker_list(seq, size):
    return (seq[i::size] for i in range(size))


# %%
def get_logs(log_group_name: str, filter_pattern: str):
    log_stream_names = get_logstreams_names(log_group_name=log_group_name)

    log_results = []

    if len(log_results) >= 50:

        for log_stream_partition in zip(*[iter(log_stream_names)] * 50):
            log_results += filter_logs(
                log_group_name=log_group_name,
                log_stream_names=list(log_stream_partition),
                filter_pattern=filter_pattern,
            )

    else:

        log_results = filter_logs(
            log_group_name=log_group_name,
            log_stream_names=log_stream_names,
            filter_pattern=filter_pattern,
        )
    return log_results


# %%
log_results = get_logs(log_group_name=log_group_name, filter_pattern="ERROR")
# %%
now = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")
with open(Path(__file__).resolve().parent / f"caseid-error-{now}.json", "w") as handle:
    json.dump(log_results, handle)
# %%
tz_est = timezone("America/New_York")
time_format = "%Y-%m-%d %H:%M:%S"
# %%
for result in log_results:
    date = datetime.fromtimestamp(result["timestamp"] / 1000)
    print(current_tz.localize(date).astimezone(tz_est).strftime(time_format))
    print(result["message"], "\n")
# %%
now = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")
with open(Path(__file__).resolve().parent / f"caseid-error-{now}.json", "w") as handle:
    json.dump(log_results, handle)
