# special_instruments' pip is the second place after the decimal (0.01) rather than the fourth (0.0001).
SPECIAL_INSTRUMENTS = ('XAU', 'JPY', 'BCO')


def has_special_instrument(instrument):
    return any(inst in instrument for inst in SPECIAL_INSTRUMENTS)
