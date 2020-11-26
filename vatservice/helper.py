def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


def _is_well_formated(vatid: str) -> bool:
    """
    Check against some known rules
    https://de.wikipedia.org/wiki/Umsatzsteuer-Identifikationsnummer
    """
    l = len(vatid)
    c = vatid[:2]
    num = vatid[2:]

    if l < 8 or l > 14:
        return False

    if c == 'AT':
        return l == 11 and vatid[:3] == 'ATU' and is_integer(vatid[3:])
    elif c in ('DE', 'EE', 'PT'):
        return l == 11 and is_integer(num)
    elif c in ('SI', 'MT', 'LU', 'HU', 'FI', 'DK'):
        return l == 10
    return True


def get_clean_vat(vat_in: str) -> str:
    return vat_in.strip().replace(' ', '')