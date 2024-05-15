import base64
import logging
import os
import re
import asyncio
import requests
from requests.cookies import cookiejar_from_dict
import pyotp
from . import urls

from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import stealth_async
import webbrowser

logger = logging.getLogger(__name__)

# Constants
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/"
)
VIEWPORT = {"width": 1920, "height": 1080}


class SessionManager:
    # https://github.com/itsjafer/schwab-api/blob/main/schwab_api/account_information.py
    def __init__(self) -> None:
        """
        This class is using asynchonous playwright mode.
        """
        self.headers = None
        self.session = requests.Session()
        self.playwright = None
        self.browser = None
        self.page = None

    def check_auth(self):
        r = self.session.get(urls.account_info_v2())
        if r.status_code != 200:
            return False
        return True

    def get_session(self):
        return self.session

    async def _app_login(self, app_key: str, username, password, totp_secret=None):
        """This function runs in async mode to perform login.
        Use with login function. See login function for details.
        """
        self.playwright = await async_playwright().start()
        if self.browserType == "firefox":
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        else:
            raise ValueError("Only supported browserType is 'firefox'")

        user_agent = USER_AGENT + self.browser.version
        self.page = await self.browser.new_page(
            user_agent=user_agent, viewport=VIEWPORT
        )
        await stealth_async(self.page)

        await self.page.goto(urls.APP_AUTH_URL + app_key)

        login_frame = "schwablmslogin"
        await self.page.frame(name=login_frame).click('[placeholder="Login ID"]')
        await self.page.frame(name=login_frame).fill(
            '[placeholder="Login ID"]', username
        )

        if totp_secret is not None:
            totp = pyotp.TOTP(totp_secret)
            password += str(totp.now())

        login_frame = "schwablmslogin"
        await self.page.frame(name=login_frame).press('[placeholder="Login ID"]', "Tab")
        await self.page.frame(name=login_frame).fill(
            '[placeholder="Password"]', password
        )

        try:
            await self.page.frame(name=login_frame).press(
                '[placeholder="Password"]', "Enter"
            )
            await self.page.wait_for_url(
                re.compile(r"app/trade"), wait_until="domcontentloaded"
            )  # Making it more robust than specifying an exact url which may change.
        except TimeoutError:
            raise Exception(
                "Login was not successful; please check username and password"
            )

        await self.page.wait_for_selector("#_txtSymbol")

        await self._async_save_and_close_session()
        return True

    def login(self, username, password, totp_secret=None):
        """This function will log the user into schwab using asynchronous
        Playwright and saving the authentication cookies in the session header.
        :type username: str
        :param username: The username for the schwab account.

        :type password: str
        :param password: The password for the schwab account/

        :type totp_secret: Optional[str]
        :param totp_secret: The TOTP secret used to complete multi-factor authentication
            through Symantec VIP. If this isn't given, sign in will use SMS.

        :rtype: boolean
        :returns: True if login was successful and no further action is needed or False
            if login requires additional steps (i.e. SMS - no longer supported)
        """
        result = asyncio.run(self._async_login(username, password, totp_secret))
        return result

    async def _async_login(self, username, password, totp_secret=None):
        """This function runs in async mode to perform login.
        Use with login function. See login function for details.
        """
        self.playwright = await async_playwright().start()
        if self.browserType == "firefox":
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        else:
            raise ValueError("Only supported browserType is 'firefox'")

        user_agent = USER_AGENT + self.browser.version
        self.page = await self.browser.new_page(
            user_agent=user_agent, viewport=VIEWPORT
        )
        await stealth_async(self.page)

        await self.page.goto("https://www.schwab.com/")

        await self.page.route(
            re.compile(r".*balancespositions*"), self._asyncCaptureAuthToken
        )

        login_frame = "schwablmslogin"
        await self.page.wait_for_selector("#" + login_frame)

        await self.page.frame(name=login_frame).select_option(
            "select#landingPageOptions", index=3
        )

        await self.page.frame(name=login_frame).click('[placeholder="Login ID"]')
        await self.page.frame(name=login_frame).fill(
            '[placeholder="Login ID"]', username
        )

        if totp_secret is not None:
            totp = pyotp.TOTP(totp_secret)
            password += str(totp.now())

        await self.page.frame(name=login_frame).press('[placeholder="Login ID"]', "Tab")
        await self.page.frame(name=login_frame).fill(
            '[placeholder="Password"]', password
        )

        try:
            await self.page.frame(name=login_frame).press(
                '[placeholder="Password"]', "Enter"
            )
            await self.page.wait_for_url(
                re.compile(r"app/trade"), wait_until="domcontentloaded"
            )  # Making it more robust than specifying an exact url which may change.
        except TimeoutError:
            raise Exception(
                "Login was not successful; please check username and password"
            )

        await self.page.wait_for_selector("#_txtSymbol")

        await self._async_save_and_close_session()
        return True

    async def _async_save_and_close_session(self):
        cookies = {
            cookie["name"]: cookie["value"]
            for cookie in await self.page.context.cookies()
        }
        self.session.cookies = cookiejar_from_dict(cookies)
        await self.page.close()
        await self.browser.close()
        await self.playwright.stop()

    async def _asyncCaptureAuthToken(self, route):
        self.headers = await route.request.all_headers()
        await route.continue_()


def construct_init_auth_url(app_key: str, app_secret: str) -> tuple[str, str, str]:

    auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?client_id={app_key}&\
        redirect_uri=https://127.0.0.1"

    logger.info("Click to authenticate:")
    logger.info(auth_url)

    return app_key, app_secret, auth_url


def construct_headers_and_payload(returned_url, app_key, app_secret):
    response_code = (
        f"{returned_url[returned_url.index('code=') + 5: returned_url.index('%40')]}@"
    )

    credentials = f"{app_key}:{app_secret}"
    base64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {base64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {
        "grant_type": "authorization_code",
        "code": response_code,
        "redirect_uri": "https://127.0.0.1",
    }

    return headers, payload


def retrieve_tokens(headers, payload) -> dict:
    init_token_response = requests.post(
        url="https://api.schwabapi.com/v1/oauth/token",
        headers=headers,
        data=payload,
    )

    init_tokens_dict = init_token_response.json()

    return init_tokens_dict


def main(app_key: str, app_secret: str):
    app_key, app_secret, cs_auth_url = construct_init_auth_url(app_key, app_secret)
    logger.info(cs_auth_url)
    webbrowser.open(cs_auth_url)

    logger.info("Paste Returned URL:")
    returned_url = input()

    init_token_headers, init_token_payload = construct_headers_and_payload(
        returned_url, app_key, app_secret
    )

    init_tokens_dict = retrieve_tokens(
        headers=init_token_headers, payload=init_token_payload
    )

    logger.debug(init_tokens_dict)

    return "Done!"


if __name__ == "__main__":
    main(app_key=os.getenv("APP_KEY"), app_secret=os.getenv("APP_SECRET"))
