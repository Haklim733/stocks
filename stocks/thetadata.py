import os
import time
import requests

HOST = "127.0.0.1"
if os.getenv("DOCKER"):
    HOST = "thetadata"


def greek_snapshot(symbol):
    url = f"http://{HOST}:25510/v2/bulk_snapshot/option/greeks"
    querystring = {"root": symbol, "exp": "0", "use_csv": "true"}
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers, params=querystring)


def ohlc_snapshot(symbol):
    url = f"http://{HOST}:25510/v2/bulk_snapshot/option/ohlc"
    querystring = {"root": symbol, "exp": "0", "use_csv": "true"}
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers, params=querystring)


def open_interest_snapshot(symbol):
    url = f"http://{HOST}:25510/v2/bulk_snapshot/option/quote"
    querystring = {"root": symbol, "exp": "0", "use_csv": "true"}
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers, params=querystring)


def quote_snapshot(symbol):
    url = f"http://{HOST}:25510/v2/bulk_snapshot/option/quote"
    querystring = {"root": symbol, "exp": "0", "use_csv": "true"}
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers, params=querystring)


def quote_eod_options(
    root: str,
    strike: int,
    call: str = "C",
    start_date: int = None,
    end_date: int = None,
    exp_date: int = None,
):
    _strike = strike * 1000
    url = f"http://{HOST}:25510/v2/hist/option/eod"
    querystring = {
        "root": root,
        "strike": _strike,
        "right": call,
        "exp": exp_date,
        "start_date": start_date,
        "end_date": end_date,
        "use_csv": "true",
    }
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers, params=querystring)


if __name__ == "__main__":
    import pandas as pd
    from io import BytesIO

    time.sleep(2)
    st = time.time()
    # greeks = greek_snapshot("TSLA")
    # ohlc = ohlc_snapshot("TSLA")
    # open_interest = open_interest_snapshot("TSLA")
    # quote_snapshot = quote_snapshot("TSLA")
    eod_snapshot = quote_eod_options(
        "AMD",
        strike=170,
        call="C",
        exp_date=20240531,
        start_date=20240520,
        end_date=20240520,
    )
    print(eod_snapshot.content)
    print(pd.read_csv(BytesIO(eod_snapshot.content)))
    # res = requests.get("http://{HOST}:25510/v2/hist/option/eod?root=AMD&exp=2024053\
    # 1&strike=170000&right=C&start_date=20240520&end_date=20240520&use_csv=true")
    # print(res.content)
    et = time.time()
    print("request time: " + str(et - st))
