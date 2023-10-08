from collections import namedtuple
from decimal import Decimal

import requests
from bs4 import BeautifulSoup


Total = namedtuple("Total", ["raised", "target", "currency"])
Donor = namedtuple("Donor", ["name", "comment", "amount"])

NULL_DONOR = Donor("", "", "")


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
        name = list(list(relevant_block.children)[0].children)[0].text
        comment = list(relevant_block.children)[1].text
        amount = list(relevant_block.children)[2].text
        donors.append(Donor(name, comment, amount))

    return donors


def get_data(url):
    """Given a JustGiving `url`, return the current total and target amounts, and the currency symbol."""

    response = requests.get(url)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(
            f"Couldn't get data from the server; got a {response.status_code} error."
        )

    soup = BeautifulSoup(markup=response.text, features="html.parser")
    totals = get_totals(soup)
    donors = get_donors(soup)

    return totals, donors
