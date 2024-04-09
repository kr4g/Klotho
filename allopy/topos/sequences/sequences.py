import numpy as np

class Norg():
    '''
    Class for Per Nørgård's sequences.
    '''
    @staticmethod
    def inf(start: int = 0, size: int = 128, step:int = 1):
        if start == 0 and step == 1:
            p = np.empty(size, dtype=int)
            p[0] = 0
            p[1] = 1        
            for i in range(1, (size - 1) // 2 + 1):
                delta = p[i] - p[i - 1]
                if 2 * i < size:
                    p[2 * i] = p[2 * i - 2] - delta
                if 2 * i + 1 < size:
                    p[2 * i + 1] = p[2 * i - 1] + delta
            return p
        return np.array([Norg.inf_num(start + step * i) for i in range(size)])

    @staticmethod
    def inf_num(n):
        '''
        Computes the infinite number for a given integer `n` by converting it to binary,
        filtering left zeros, and then applying the infinity digits transformation.
        '''
        def _infinity_digits(s):
            '''
            Applies the infinity digits transformation to a string `s` of binary digits.
            '''
            output = 0
            for char in s:
                if char == '0':
                    output *= -1
                elif char == '1':
                    output += 1
            return output
                
        def _filter_left_zeros(digits):
            '''
            Filters out leading zeros from a list of binary digits.
            '''
            # Find the index of the first 1 and slice from there, if no 1 found return empty list
            try:
                first_one_index = digits.index(1)
                return digits[first_one_index:]
            except ValueError:
                return []

        # Convert to binary, remove the '0b' prefix, and convert to a list of integers
        binary_digits = list(map(int, bin(n)[2:]))
        filtered_digits = _filter_left_zeros(binary_digits)
        return _infinity_digits(filtered_digits)



