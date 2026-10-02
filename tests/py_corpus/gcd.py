def gcd(a, b):
    while b != 0:
        held = b
        b = a % b
        a = held
    return a

print(gcd(48, 18))
print(gcd(17, 5))
print(gcd(0, 7))
