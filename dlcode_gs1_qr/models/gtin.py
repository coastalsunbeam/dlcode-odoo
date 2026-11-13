def valid_gtin(code):
    digits = (code or "").replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return None
    gtin = digits.zfill(14)
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(gtin[:13]))
    return gtin if (10 - total % 10) % 10 == int(gtin[13]) else None
