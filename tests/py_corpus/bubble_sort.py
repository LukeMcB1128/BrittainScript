def bubble_sort(values):
    count = len(values)
    for outer in range(count):
        for inner in range(count - outer - 1):
            if values[inner] > values[inner + 1]:
                held = values[inner]
                values[inner] = values[inner + 1]
                values[inner + 1] = held
    return values

print(bubble_sort([5, 2, 9, 1, 5, 6]))
print(bubble_sort([]))
