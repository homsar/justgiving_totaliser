def format_donor(donor):
    return f"{donor.name} donated {donor.amount}{(', commenting “' + donor.comment + '”') if donor.comment else ''}"
