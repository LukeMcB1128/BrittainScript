def primes_below(limit):
    flags = []
    for index in range(limit):
        flags.append(True)
    number = 2
    while number * number < limit:
        if flags[number]:
            multiple = number * number
            while multiple < limit:
                flags[multiple] = False
                multiple = multiple + number
        number += 1
    found = []
    for candidate in range(2, limit):
        if flags[candidate]:
            found.append(candidate)
    return found

print(primes_below(50))
