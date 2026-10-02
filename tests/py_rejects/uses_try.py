try:
    print(1)
except ValueError:
    raise ValueError("bad value") from None
