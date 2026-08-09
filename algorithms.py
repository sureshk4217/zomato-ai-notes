def insertion_sort_by_key(items: list[dict], key: str) -> list[dict]:
    result = [item.copy() for item in items]
    for i in range(1, len(result)):
        current = result[i]
        j = i - 1
        while j >= 0 and result[j].get(key, 0) < current.get(key, 0):
            result[j + 1] = result[j]
            j -= 1
        result[j + 1] = current
    return result

def binary_search_iterative(sorted_titles: list[str], target: str) -> int:
    start, end = 0, len(sorted_titles) - 1
    target_cmp = target.casefold()
    while start <= end:
        mid = start + (end - start) // 2
        value = sorted_titles[mid].casefold()
        if value == target_cmp:
            return mid
        if value < target_cmp:
            start = mid + 1
        else:
            end = mid - 1
    return -1

def binary_search_recursive(
    sorted_titles: list[str], target: str, start: int, end: int
) -> int:
    if start > end:
        return -1
    mid = start + (end - start) // 2
    target_cmp = target.casefold()
    value = sorted_titles[mid].casefold()
    if value == target_cmp:
        return mid
    if value < target_cmp:
        return binary_search_recursive(sorted_titles, target, mid + 1, end)
    return binary_search_recursive(sorted_titles, target, start, mid - 1)

def linear_search(items: list[dict], key: str, value):
    found = False
    result = None
    for item in items:
        if item.get(key) == value:
            result = item
            found = True
            break
    return result if found else None
