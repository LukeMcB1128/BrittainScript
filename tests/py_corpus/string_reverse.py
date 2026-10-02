def reverse(text):
    out = ""
    index = len(text) - 1
    while index >= 0:
        out = out + text[index]
        index -= 1
    return out

print(reverse("BrittainScript"))
print(reverse(""))
print(reverse("a"))
