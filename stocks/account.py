import os
import requests
import pandas as pd
from utils._aws import retrieve_secret


class AccountsTrading:
    def __init__(self):
        # Initialize access token during class instantiation
        self.access_token = None
        self.account_hash_value = None
        self.refresh_access_token()
        self.base_url = "https://api.schwabapi.com/trader/v1"
        self.headers = {"Authorization": f"Bearer {self.access_token}"}
        self.get_account_number_hash_value()

    def refresh_access_token(self):
        self.access_token = retrieve_secret()

    def get_account_number_hash_value(self):
        account = os.getenv("ACCOUNT")
        response = requests.get(
            self.base_url + f"/accounts/{account}", headers=self.headers
        )
        response_frame = pd.json_normalize(response.json())
        self.account_hash_value = response_frame["hashValue"].iloc[0]
