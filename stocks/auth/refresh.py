import logging
import base64
import requests

logger = logging.getLogger(__name__)


def refresh_tokens(app_key: str, app_secret: str, refresh_token: str):
    logger.info("Initializing...")

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    secret = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {secret}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    refresh_token_response = requests.post(
        url="https://api.schwabapi.com/v1/oauth/token",
        headers=headers,
        data=payload,
    )
    if refresh_token_response.status_code == 200:
        logger.info("Retrieved new tokens successfully using refresh token.")
    else:
        logger.error(f"Error refreshing access token: {refresh_token_response.text}")
        return None

    refresh_token_dict = refresh_token_response.json()

    logger.debug(refresh_token_dict)

    logger.info("Token dict refreshed.")

    return "Done!"


if __name__ == "__main__":
    refresh_tokens()
