from stocks import schwab
from datetime import datetime, timedelta

NOW = datetime.now()
start = NOW.strftime("%Y-%m-%d")
end = (NOW + timedelta(days=7)).strftime("%Y-%m-%d")


def test_get_options_data():
    df = schwab.get_options_data(
        "AMD",
        key,
        underlying_quote=False,
        start_date=start,
        end_date=end,
        contract_type="CALL",
        strike_count=1,
    )
    assert df.empty is False
