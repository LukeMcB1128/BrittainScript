def binary_search(values, target):
    low = 0
    high = len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1

data = [1, 3, 5, 7, 9, 11, 13]
for probe in [1, 7, 13, 4]:
    print(binary_search(data, probe))
