def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value

print(clamp(15, 0, 10))
print(clamp(-4, 0, 10))
print(clamp(5, 0, 10))
