def count_words(text):
    words = text.split(" ")
    total = 0
    for word in words:
        if len(word) > 0:
            total += 1
    return total

def longest(text):
    best = ""
    for word in text.split(" "):
        if len(word) > len(best):
            best = word
    return best

sentence = "the quick brown fox jumps over the lazy dog"
print(count_words(sentence))
print(longest(sentence))
print(count_words(""))
