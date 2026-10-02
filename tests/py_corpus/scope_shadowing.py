total = 100
value = 7

def accumulate(items):
    total = 0
    for value in items:
        total = total + value
    return total

print(accumulate([1, 2, 3]))
print(total)
print(value)
