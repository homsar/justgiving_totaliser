def format_donor(donor, quotes="smart"):
    openquote = {"smart": "“", "straight": '"'}
    closequote = {"smart": "”", "straight": '"'}

    message = f"{donor.name} donated {donor.amount}"
    if donor.comment:
        message += ", commenting "
        message += openquote[quotes]
        message += donor.comment
        message += closequote[quotes]

    return message
