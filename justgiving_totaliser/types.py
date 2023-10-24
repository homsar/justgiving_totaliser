from collections import namedtuple


Total = namedtuple("Total", ["raised", "target", "currency"])
Donor = namedtuple("Donor", ["name", "comment", "amount"])

NULL_DONOR = Donor("", "", "")
