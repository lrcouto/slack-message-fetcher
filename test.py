import random

class Solution:
    def sumZero(self, n: int) -> list[int]:
        response: list[int] = []

        if n is 1:
            return response.append(0)

        while sum(response) is not 0:
            response = [random.randint(-500, 500) for i in n]
    
        return response

solution = Solution()
print(solution.sumZero(5))
