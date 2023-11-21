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

# def linear_encode(keys, values, allow_repeats=False):
#     '''
#     Assigns values from the values list to the keys list in a linear fashion. Allows for an option to repeat values.
    
#     Args:
#     - keys (list): A list of string symbols to be used as dictionary keys.
#     - values (list): A list of string symbols to be assigned linearly to the keys.
#     - allow_repeats (bool): If True, values will be repeated by re-shuffling once all are used.
    
#     Returns:
#     - dict: A dictionary with keys from the keys list and values from the values list.
#     '''
#     if not keys or not values:
#         return {}  # Return an empty dictionary if either list is empty

