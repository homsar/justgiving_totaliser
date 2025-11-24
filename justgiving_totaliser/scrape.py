from decimal import Decimal
import logging

import requests
from bs4 import BeautifulSoup

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from .types import Donor, Total, NULL_DONOR


known_currencies = {
    "GBP": "£",
    "USD": "$",
    "EUR": "€",
    "AUD": "AU$",
    "NZD": "NZ$",
    "CAD": "CA$",
}


def query_graphql(query):
    url = "https://graphql.justgiving.com/"
    response = requests.post(url, json={"query": query})

    if not 200 <= response.status_code < 300:
        raise RuntimError(f"{response.status_code} from graphql server")

    return response.json()


def get_totals_fallback(soup, _):
    raised_block = soup.find_all("dd")[0]
    amount_block = raised_block.find_all("div")[0]
    raised_text = amount_block.text
    currency = raised_text[0]
    raised = Decimal(raised_text[1:].replace(",", ""))
    return Total(raised, None, currency)


def get_totals_graphql(_, url):
    slug = get_slug(url)
    query = f"""
    {{
      page(slug: "{slug}", type: ONE_PAGE) {{
        targetWithCurrency {{
          value
          currencyCode
        }}
        donationSummary {{
          totalAmount {{
            value
            currencyCode
          }}
        }}
      }}
    }}"""

    result = query_graphql(query)
    currency_code = result["data"]["page"]["donationSummary"]["totalAmount"][
        "currencyCode"
    ]
    assert currency_code == result["data"]["page"]["targetWithCurrency"]["currencyCode"]

    target = normalise_currency(
        currency_code, result["data"]["page"]["targetWithCurrency"]["value"]
    )
    raised = normalise_currency(
        currency_code, result["data"]["page"]["donationSummary"]["totalAmount"]["value"]
    )
    currency = known_currencies.get(currency_code, f"{currency_code} ")
    return Total(raised, target, currency)


def get_totals(soup, _):
    raised_of_block = soup.find(string="raised of")
    relevant_block = raised_of_block.find_parents()

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
        if len(children) > 1:
            comment = children[1].text
        else:
            comment = None
        if len(children) > 2:
            amount = children[2].text
        else:
            amount = None

        donors.append(Donor(name, comment, amount))

    return donors


def normalise_currency(currencyCode, value):
    if currencyCode in known_currencies:
        return Decimal(value) / 100
    return Decimal(value)


def currency_to_string(currencyCode, value):
    normalised_value = normalise_currency(currencyCode, value)
    symbol = known_currencies.get(currencyCode, f"{currencyCode} ")
    return f"{symbol}{normalised_value}"


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

    result = query_graphql(query)
    raw_donations = result["data"]["page"]["donations"]["nodes"]
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
    for total_getter in [get_totals, get_totals_graphql, get_totals_fallback]:
        try:
            totals = total_getter(soup, url)
        except Exception as ex:
            continue
        else:
            break
    else:
        totals = Total(Decimal(0), Decimal(0), "£")

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
