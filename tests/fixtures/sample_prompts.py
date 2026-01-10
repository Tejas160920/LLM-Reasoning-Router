"""Sample prompts for testing the router.

These prompts are categorized by expected complexity level
and can be used to verify routing decisions.
"""

# Simple prompts - should route to fast model (complexity < 30)
SIMPLE_PROMPTS = [
    "What is Python?",
    "Define recursion",
    "List the planets in our solar system",
    "What time is it in Tokyo?",
    "Translate 'hello' to Spanish",
    "What is 2 + 2?",
    "Who wrote Romeo and Juliet?",
    "What color is the sky?",
]

# Medium complexity prompts - should use fast model with quality check (30-70)
MEDIUM_PROMPTS = [
    "Explain how a binary search tree works",
    "What are the differences between SQL and NoSQL databases?",
    "How do I implement a REST API in Python?",
    "Summarize the main concepts of machine learning",
    "Describe the MVC architecture pattern",
    "What is the difference between GET and POST requests?",
    "Explain how DNS works",
    "How does garbage collection work in Python?",
]

# Complex prompts - should route to complex model (complexity > 70)
COMPLEX_PROMPTS = [
    """
    Analyze the trade-offs between microservices and monolithic architectures.
    Consider: scalability, maintainability, deployment complexity, and team structure.
    Provide specific examples for each point.
    """,
    """
    Debug this recursive function and explain why it causes a stack overflow:
    ```python
    def fib(n):
        return fib(n-1) + fib(n-2)
    ```
    Then provide an optimized solution with memoization.
    """,
    """
    Design a distributed caching system that handles:
    1. Cache invalidation across multiple nodes
    2. Consistent hashing for load distribution
    3. Failover and replication
    Step by step, explain your architectural decisions.
    """,
    """
    Compare and contrast the following sorting algorithms:
    - QuickSort
    - MergeSort
    - HeapSort

    Analyze their time complexity, space complexity, stability,
    and provide scenarios where each would be preferred.
    """,
    """
    I have a Python web application with performance issues.
    The database queries are slow and the API response times are high.

    Analyze the potential causes and provide a step-by-step
    optimization strategy covering:
    1. Database query optimization
    2. Caching strategies
    3. Async processing
    4. Connection pooling
    """,
]

# Prompts with code - should increase complexity
CODE_PROMPTS = [
    """
    What does this code do?
    ```python
    def mystery(n):
        if n <= 1:
            return n
        return mystery(n-1) + mystery(n-2)
    ```
    """,
    """
    Fix the bug in this JavaScript code:
    ```javascript
    function sum(arr) {
        let total;
        for (let i = 0; i <= arr.length; i++) {
            total += arr[i];
        }
        return total;
    }
    ```
    """,
]

# Prompts with math - should increase complexity
MATH_PROMPTS = [
    "Solve for x: $x^2 + 5x + 6 = 0$",
    "Calculate the integral: $\\int x^2 dx$",
    "What is the probability of rolling two sixes with two dice?",
]

# Multi-part questions - should increase complexity
MULTIPART_PROMPTS = [
    """
    1. What is React?
    2. How does it compare to Vue?
    3. When should I use one over the other?
    """,
    """
    First, explain what Docker is.
    Second, describe how containers differ from virtual machines.
    Finally, provide a simple example of a Dockerfile.
    """,
]

# Prompts that might produce low quality responses - for testing escalation
ESCALATION_TEST_PROMPTS = [
    "What will the weather be like tomorrow?",  # Uncertain - model can't know
    "Predict the stock price of Apple next year",  # Can't be answered confidently
    "Write a 10-page essay on quantum physics",  # Too long for single response
]

# All prompts categorized
ALL_PROMPTS = {
    "simple": SIMPLE_PROMPTS,
    "medium": MEDIUM_PROMPTS,
    "complex": COMPLEX_PROMPTS,
    "code": CODE_PROMPTS,
    "math": MATH_PROMPTS,
    "multipart": MULTIPART_PROMPTS,
    "escalation_test": ESCALATION_TEST_PROMPTS,
}
