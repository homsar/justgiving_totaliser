from decimal import Decimal

import requests
from bs4 import BeautifulSoup

def get_data(url):
    """Given a JustGiving `url`, return the current total and target amounts, and the currency symbol."""

    response = requests.get(url)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"Couldn't get data from the server; got a {response.status_code} error.")

    soup = BeautifulSoup(markup=response.text, features="html.parser")
    relevant_block = soup.find(string = "raised of").find_parents()

    raised_text = relevant_block[1].previousSibling.string
    target_text = relevant_block[0].nextSibling.nextSibling.string

    currency = raised_text[0]
    if target_text[0] != currency:
        raise ValueError(f"Currencies are not consistent! Raised is in {currency}, but total in {target_text[0]}")

    raised = Decimal(raised_text[1:].replace(",", ""))
    target = Decimal(target_text[1:].replace(",", ""))

    return raised, target, currency
