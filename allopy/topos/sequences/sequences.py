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
                
        def _filter_left_zeros(binary_str):
            '''
            Filters out leading zeros from a binary string `binary_str`.
            '''            
            return binary_str.lstrip('0') # remove leading zeros
       
        binary_str = bin(n)[2:] # remove the '0b' prefix
        filtered_binary_str = _filter_left_zeros(binary_str)
        filtered_digits = list(filtered_binary_str)
        return _infinity_digits(filtered_digits)
