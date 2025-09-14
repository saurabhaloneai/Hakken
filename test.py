def factorial(n):
    # Base case: stop the recursion
    if n == 0 or n == 1:
        return 1
    
    # Recursive case: function calls itself
    return n * factorial(n - 1)

# Example: factorial(5) = 5 * 4 * 3 * 2 * 1 = 120
print(factorial(5))  # Output: 120
