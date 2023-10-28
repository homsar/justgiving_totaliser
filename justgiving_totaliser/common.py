def format_donor(donor, quotes="smart"):
    openquote = {"smart": "“", "straight": '"'}
    closequote = {"smart": "”", "straight": '"'}

    if donor.amount is None:
        amount = "an unknown amount"
    elif donor.amount:
        amount = donor.amount
    else:
        amount = "nothing"

    message = f"{donor.name} donated {amount}"
    if donor.comment:
        message += ", commenting "
        message += openquote[quotes]
        message += donor.comment
        message += closequote[quotes]

    return message
