import random

def rand_encode(keys, values, allow_repeats=False):
    '''
    Assigns random keys from the values list to the keys list. Allows for an option to repeat values.

    Args:
    - keys (list): A list of string symbols to be used as dictionary keys.
    - values (list): A list of string symbols to be assigned randomly to the keys.
    - allow_repeats (bool): If True, values will be repeated by re-shuffling once all are used.

    Returns:
    - dict: A dictionary with keys from the keys list and random values from the values list.
    '''
    if not keys or not values:
        return {}  # Return an empty dictionary if either list is empty

    assignments = {}
    values_pool = values.copy()
    random.shuffle(values_pool)

    for i, key in enumerate(keys):
        if not values_pool:  # If values_pool is empty
            if not allow_repeats:
                break  # Stop assigning if repeats are not allowed
            values_pool = values.copy()  # Replenish the values pool
            random.shuffle(values_pool)

        # Assign a value to the key
        assignments[key] = values_pool.pop()

    return assignments

# # Example usage
# keys_list = ['key1', 'key2', 'key3', 'key4', 'key5', 'key6']
# values_list = ['A', 'B', 'C']
# result = rand_encode(keys_list, values_list, allow_repeats=True)
# print(result)
