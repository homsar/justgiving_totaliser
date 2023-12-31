from decimal import Decimal
import logging

import requests
from bs4 import BeautifulSoup

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from .types import Donor, Total, NULL_DONOR


def get_totals(soup):
    relevant_block = soup.find(string="raised of").find_parents()

    raised_text = relevant_block[1].previousSibling.string
    target_text = relevant_block[0].nextSibling.nextSibling.string

    currency = raised_text[0]
    if target_text[0] != currency:
        raise ValueError(
            f"Currencies are not consistent! Raised is in {currency}, but total in {target_text[0]}"
        )

    raised = Decimal(raised_text[1:].replace(",", ""))
    target = Decimal(target_text[1:].replace(",", ""))

    return Total(raised, target, currency)


def get_donors(soup):
    donors = []
    for relevant_block in soup.findAll(
        "div", {"class": lambda L: L and L.startswith("SupporterDetails_content")}
    ):
        children = list(relevant_block.children)
        name = list(children[0].children)[0].text
        comment = children[1].text
        if len(children) > 2:
            amount = children[2].text
        else:
            amount = None

        donors.append(Donor(name, comment, amount))

    return donors


def currency_to_string(currencyCode, value):
    known_currencies = {
        "GBP": "£",
        "USD": "$",
        "EUR": "€",
        "AUD": "AU$",
        "NZD": "NZ$",
        "CAD": "CA$",
    }

    if currencyCode in known_currencies:
        return f"{known_currencies[currencyCode]}{value / 100:.02f}"

    return f"{currencyCode} {value}"


def get_donors_graphql(soup, slug, num_donors):
    query = f"""
    {{
      page(slug: "{slug}", type: ONE_PAGE) {{
        donations (last: {num_donors}) {{
          nodes {{
            amount {{
              currencyCode
              value
            }}
            message
            displayName
          }}
        }}
      }}
    }}"""

    url = "https://graphql.justgiving.com/"
    response = requests.post(url, json={"query": query})

    if not 200 <= response.status_code < 300:
        raise RuntimError(f"{response.status_code} from graphql server")

    raw_donations = response.json()["data"]["page"]["donations"]["nodes"]
    donations = []

    for raw_donation in raw_donations:
        donations.append(
            Donor(
                raw_donation["displayName"],
                raw_donation["message"],
                currency_to_string(**raw_donation["amount"])
                if raw_donation["amount"]
                else None,
            )
        )

    return donations


def get_slug(url):
    site = "justgiving.com/"
    if site not in url:
        raise ValueError("URL is not on justgiving.com, giving up")
    slug = url[url.index(site) + len(site) :]
    if "?" in slug:
        slug = slug[: slug.index("?")]

    return slug


def get_data(url, num_donors=5):
    """Given a JustGiving `url`, return the current total and target amounts, and the currency symbol."""

    logging.debug("get_data entered")
    response = requests.get(url)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(
            f"Couldn't get data from the server; got a {response.status_code} error."
        )

    soup = BeautifulSoup(markup=response.text, features="html.parser")
    totals = get_totals(soup)
    donors = get_donors(soup)

    if len(donors) < num_donors:
        try:
            slug = get_slug(url)
            donors = get_donors_graphql(soup, slug, num_donors)
        except (requests.exceptions.RequestException, RuntimeError) as ex:
            print(f"Couldn't get graphql: {ex}")

    return totals, donors


def fake_get_data(url, num_donors=5):
    """Return an implausible JustGiving response."""

    return Total(Decimal(2000), Decimal(1000), "£"), []


class DataSignals(QObject):
    finished = pyqtSignal(tuple)


class DataGetter(QRunnable):
    local_get_data = staticmethod(get_data)

    def __init__(self, url, num_donors=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.debug("DataGetter created.")

        self.url = url
        self.num_donors = num_donors
        self.signals = DataSignals()

    @pyqtSlot()
    def run(self):
        logging.debug("Trying to call get_data.")
        if not self.url:
            self.signals.finished.emit((None, None))
        try:
            self.signals.finished.emit(self.local_get_data(self.url, self.num_donors))
        except Exception as ex:
            logging.debug(f"Couldn't get_data due to {ex}")
            self.signals.finished.emit((ex, None))
