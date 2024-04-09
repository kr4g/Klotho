import numpy as np

class Norg():
    '''
    Class for Per Nørgård's sequences.

    see: https://web.archive.org/web/20071010091253/http://www.pernoergaard.dk/eng/strukturer/uendelig/uindhold.html

    '''
    @staticmethod
    def inf(start: int = 0, size: int = 128, step:int = 1):
        '''
        from: https://web.archive.org/web/20071010092334/http://www.pernoergaard.dk/eng/strukturer/uendelig/ukonstruktion05.html

        '''
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

        based on: https://github.com/smoge/InfinitySeries.git

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

    @staticmethod
    def trip(seed:list = [0,-2,-1], size:int = 128, inv_pat:list = [-1, 1, 1]):
        '''
        from: https://web.archive.org/web/20071010091606/http://www.pernoergaard.dk/eng/strukturer/uendelig/u3.html

        '''
        if len(seed) != 3 or len(inv_pat) != 3:
            raise ValueError('seed and inv_pat must be lists of length 3')
                
        p = np.empty(size, dtype=int)
        # p[0] = seed[0]
        # p[1] = seed[1]
        # p[2] = seed[2]
        p[:3] = seed
        for i in range(1, (size - 1) // 3 + 1):
            delta = p[i] - p[i - 1]
            if 3 * i < size:
                p[3 * i] = p[3 * i - 3] + inv_pat[(3 * i) % 3] * delta
            if 3 * i + 1 < size:
                p[3 * i + 1] = p[3 * i - 2] + inv_pat[(3 * i + 1) % 3] * delta
            if 3 * i + 2 < size:
                p[3 * i + 2] = p[3 * i - 1] + inv_pat[(3 * i + 2) % 3] * delta
        return p