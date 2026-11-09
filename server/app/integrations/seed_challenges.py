"""
Seed challenges and test cases matching client/src/data/challenges.js.
Ensures both frontend and backend are aligned on challenge IDs, statements, tests, and progressive hints.
"""

SEED_CHALLENGES = [
    {
        "id": "last-k-total",
        "title": "Last K Total",
        "description": "Return the total of the last k marks, or of all marks if k is larger than the list.",
        "statement": "Write a function named `last_k_total(marks, k)` that takes a list of integers `marks` (possibly empty) and an integer `k` (0 or more). It returns the total of the last `k` marks, or the total of all marks if `k` is larger than the list.",
        "function_signature": "def last_k_total(marks: list[int], k: int) -> int",
        "grade": "Grade 4",
        "difficulty": "Easy",
        "tags": ["Lists", "Slicing", "Loops"],
        "estimatedTime": "10 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(marks) ≤ 10⁵; -10⁹ ≤ marks[i] ≤ 10⁹; k ≥ 0",
        "time_complexity": "O(min(n, k))",
        "starterCode": "def last_k_total(marks, k):\n    total = 0\n    for i in range(len(marks) - k, len(marks)):\n        total += marks[i]\n    return total\n",
        "example": {
            "call": "last_k_total([10, 20, 30, 40], 2)",
            "expected": "70",
            "explanation": "The last 2 marks are 30 and 40. Their total is 70."
        },
        "visibleTests": [
            {"call": "last_k_total([10, 20, 30, 40], 2)", "expected": "70"},
            {"call": "last_k_total([5, 5, 5], 3)", "expected": "15"},
            {"call": "last_k_total([7], 1)", "expected": "7"}
        ],
        "hiddenTests": [
            {"call": "last_k_total([1, 2, 3, 4, 5], 0)", "expected": "0"},
            {"call": "last_k_total([], 0)", "expected": "0"},
            {"call": "last_k_total([], 3)", "expected": "0"},
            {"call": "last_k_total([2, 5], 3)", "expected": "7"},
            {"call": "last_k_total([10, 20], 4)", "expected": "30"},
            {"call": "last_k_total([-5, 10, 15], 2)", "expected": "25"}
        ],
        "hints": [
            "Your three visible examples never ask for more marks than the list holds. What should last_k_total return when k is bigger than the list?",
            "Work out last_k_total([2, 5], 3) by hand. Which index does your loop start at, and what does marks[-1] mean in Python?",
            "In Python a negative index counts back from the end, so some marks get added twice or raise IndexError on an empty list. Your start index must never go below 0.",
            "Python has a built-in that returns the larger of two numbers. Use it to work out the start index once, before the loop."
        ]
    },
    {
        "id": "count-passes",
        "title": "Count Passes",
        "description": "Count how many marks in a list are 40 or more.",
        "statement": "Write a function named `count_passes(marks)` that takes a list of integer `marks` (possibly empty) and returns how many of them are 40 or more.",
        "function_signature": "def count_passes(marks: list[int]) -> int",
        "grade": "Grade 4",
        "difficulty": "Easy",
        "tags": ["Loops", "Comparison"],
        "estimatedTime": "10 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(marks) ≤ 10⁵; -10⁹ ≤ marks[i] ≤ 10⁹",
        "time_complexity": "O(n)",
        "starterCode": "def count_passes(marks):\n    count = 0\n    for mark in marks:\n        if mark > 40:\n            count += 1\n    return count\n",
        "example": {
            "call": "count_passes([30, 40, 50])",
            "expected": "2",
            "explanation": "Marks 40 and 50 are 40 or more, so the count is 2."
        },
        "visibleTests": [
            {"call": "count_passes([30, 40, 50])", "expected": "2"},
            {"call": "count_passes([10, 20, 30])", "expected": "0"},
            {"call": "count_passes([40, 40, 40])", "expected": "3"}
        ],
        "hiddenTests": [
            {"call": "count_passes([])", "expected": "0"},
            {"call": "count_passes([39, 40, 41])", "expected": "2"},
            {"call": "count_passes([39])", "expected": "0"},
            {"call": "count_passes([100, 5, 40, 0, 41])", "expected": "3"},
            {"call": "count_passes([0])", "expected": "0"},
            {"call": "count_passes([40, 39])", "expected": "1"}
        ],
        "hints": [
            "What happens when a student's mark is exactly 40? Should that count as a pass?",
            "Trace your function by hand on count_passes([40, 40, 40]). Which branch does your if-statement take when mark is 40?",
            "A strict greater-than comparison excludes the boundary value itself, so every mark of 40 is skipped.",
            "Update your comparison operator so that values equal to the passing threshold of 40 are included in the count."
        ]
    },
    {
        "id": "first-n-squares",
        "title": "First N Squares",
        "description": "Build and return the list [1, 4, 9, ..., n²], or [] when n is 0.",
        "statement": "Write a function named `first_n_squares(n)` that receives an integer `n` (0 or more) and returns the list `[1, 4, 9, ..., n²]`, or `[]` when `n` is 0.",
        "function_signature": "def first_n_squares(n: int) -> list[int]",
        "grade": "Grade 4",
        "difficulty": "Easy",
        "tags": ["Loops", "Lists"],
        "estimatedTime": "10 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ n ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def first_n_squares(n):\n    result = []\n    for i in range(1, n):\n        result.append(i * i)\n    return result\n",
        "example": {
            "call": "first_n_squares(4)",
            "expected": "[1, 4, 9, 16]",
            "explanation": "The first 4 positive integers squared are 1, 4, 9, and 16."
        },
        "visibleTests": [
            {"call": "first_n_squares(4)", "expected": "[1, 4, 9, 16]"},
            {"call": "first_n_squares(1)", "expected": "[1]"},
            {"call": "first_n_squares(0)", "expected": "[]"}
        ],
        "hiddenTests": [
            {"call": "first_n_squares(5)", "expected": "[1, 4, 9, 16, 25]"},
            {"call": "first_n_squares(2)", "expected": "[1, 4]"},
            {"call": "first_n_squares(3)", "expected": "[1, 4, 9]"},
            {"call": "first_n_squares(6)", "expected": "[1, 4, 9, 16, 25, 36]"},
            {"call": "first_n_squares(10)", "expected": "[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]"}
        ],
        "hints": [
            "Compare the length of the list your function returns with n. How many squares are in your output for n = 4?",
            "Trace first_n_squares(1) by hand. Which numbers does range(1, 1) produce in Python?",
            "In Python, range(start, stop) stops one integer before stop, so the final value n is never reached.",
            "Adjust the upper bound of your range call so the loop includes n before stopping."
        ]
    },
    {
        "id": "middle-three",
        "title": "Middle Three",
        "description": "Return the middle three items as a list, or the whole list if it has fewer than 3 items.",
        "statement": "Write a function named `middle_three(items)` that takes a list `items` of odd length, or with fewer than 3 items. Return the middle three items as a list, or the whole list if it has fewer than 3 items.",
        "function_signature": "def middle_three(items: list) -> list",
        "grade": "Grade 3",
        "difficulty": "Medium",
        "tags": ["Lists", "Indexing", "Slicing"],
        "estimatedTime": "15 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(items) ≤ 10⁵; len(items) is odd or < 3",
        "time_complexity": "O(1)",
        "starterCode": "def middle_three(items):\n    mid = len(items) // 2\n    return items[mid - 1 : mid + 1]\n",
        "example": {
            "call": "middle_three([1, 2, 3, 4, 5])",
            "expected": "[2, 3, 4]",
            "explanation": "The center element is 3. The middle 3 items are [2, 3, 4]."
        },
        "visibleTests": [
            {"call": "middle_three([1, 2, 3, 4, 5])", "expected": "[2, 3, 4]"},
            {"call": "middle_three(['a', 'b', 'c'])", "expected": "['a', 'b', 'c']"},
            {"call": "middle_three([10, 20, 30, 40, 50, 60, 70])", "expected": "[30, 40, 50]"}
        ],
        "hiddenTests": [
            {"call": "middle_three([])", "expected": "[]"},
            {"call": "middle_three([42])", "expected": "[42]"},
            {"call": "middle_three([1, 2])", "expected": "[1, 2]"},
            {"call": "middle_three([9, 8, 7, 6, 5])", "expected": "[8, 7, 6]"},
            {"call": "middle_three([1, 2, 3, 4, 5, 6, 7, 8, 9])", "expected": "[4, 5, 6]"},
            {"call": "middle_three([0, 0, 1, 0, 0])", "expected": "[0, 1, 0]"}
        ],
        "hints": [
            "Check two things: how many elements your slice returns on a 5-item list, and what happens when the list has fewer than 3 items.",
            "Work out middle_three([1, 2, 3, 4, 5]) by hand. When mid is 2, how many elements are in items[1:3], and what happens when items is [42]?",
            "A Python slice items[start:stop] has length stop - start, and when len(items) < 3, mid - 1 becomes negative.",
            "First check if the list length is under 3 to return a copy of the list early, then make sure your slice stop index is 2 positions past mid."
        ]
    },
    {
        "id": "word-boundary",
        "title": "Word Boundary",
        "description": "Determine whether a sentence starts or ends with a specific target keyword.",
        "statement": "Write a function named `is_at_boundary(sentence, keyword)` that checks if the given `sentence` either begins with or concludes with the exact string `keyword` (case-sensitive). If `keyword` is empty or `sentence` is shorter than `keyword`, return `False`.",
        "function_signature": "def is_at_boundary(sentence: str, keyword: str) -> bool",
        "grade": "Grade 3",
        "difficulty": "Medium",
        "tags": ["Strings", "Comparison", "Slicing"],
        "estimatedTime": "15 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(sentence), len(keyword) ≤ 10⁴",
        "time_complexity": "O(len(keyword))",
        "starterCode": "def is_at_boundary(sentence, keyword):\n    k = len(keyword)\n    return sentence[:k] == keyword and sentence[-k:] == keyword\n",
        "example": {
            "call": "is_at_boundary(\"curse energy flows\", \"curse\")",
            "expected": "True",
            "explanation": "The sentence starts with 'curse'."
        },
        "visibleTests": [
            {"call": "is_at_boundary(\"curse energy flows\", \"curse\")", "expected": "True"},
            {"call": "is_at_boundary(\"the quiet realm\", \"realm\")", "expected": "True"},
            {"call": "is_at_boundary(\"inside the barrier now\", \"barrier\")", "expected": "False"}
        ],
        "hiddenTests": [
            {"call": "is_at_boundary(\"infinite void\", \"void\")", "expected": "True"},
            {"call": "is_at_boundary(\"hollow purple\", \"hollow\")", "expected": "True"},
            {"call": "is_at_boundary(\"sukuna\", \"sukuna\")", "expected": "True"},
            {"call": "is_at_boundary(\"domain expansion\", \"expand\")", "expected": "False"},
            {"call": "is_at_boundary(\"\", \"curse\")", "expected": "False"}
        ],
        "hints": [
            "Read the problem statement carefully: does the sentence need to both start AND end with the keyword, or is either one enough?",
            "Trace is_at_boundary('curse energy flows', 'curse'). What does sentence[:k] == keyword evaluate to, and what does sentence[-k:] == keyword evaluate to?",
            "Using the logical 'and' requires both ends to match simultaneously, which fails whenever the keyword is only at the start or only at the end.",
            "Combine the start check and end check with the logical operator that succeeds when at least one side is True, and guard against empty inputs."
        ]
    },
    {
        "id": "pair-sum",
        "title": "Pair Sum",
        "description": "Find two distinct elements in a list whose sum equals the target value.",
        "statement": "Write a function named `has_pair_sum(numbers, target)` that returns `True` if any two elements at different positions in the list `numbers` sum to `target`, otherwise `False`.",
        "function_signature": "def has_pair_sum(numbers: list[int], target: int) -> bool",
        "grade": "Grade 3",
        "difficulty": "Medium",
        "tags": ["Loops", "Lists"],
        "estimatedTime": "20 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(numbers) ≤ 10⁴",
        "time_complexity": "O(n)",
        "starterCode": "def has_pair_sum(numbers, target):\n    for x in numbers:\n        if (target - x) in numbers:\n            return True\n    return False\n",
        "example": {
            "call": "has_pair_sum([2, 7, 11, 15], 9)",
            "expected": "True",
            "explanation": "2 + 7 equals 9."
        },
        "visibleTests": [
            {"call": "has_pair_sum([2, 7, 11, 15], 9)", "expected": "True"},
            {"call": "has_pair_sum([3, 5, 1], 10)", "expected": "False"},
            {"call": "has_pair_sum([5], 10)", "expected": "False"}
        ],
        "hiddenTests": [
            {"call": "has_pair_sum([1, 2, 3, 4], 7)", "expected": "True"},
            {"call": "has_pair_sum([5, 5], 10)", "expected": "True"},
            {"call": "has_pair_sum([], 5)", "expected": "False"},
            {"call": "has_pair_sum([10, -2, 3], 8)", "expected": "True"},
            {"call": "has_pair_sum([1, 2, 4], 8)", "expected": "False"}
        ],
        "hints": [
            "What happens when target is twice a single element in the list, such as target = 10 and numbers = [3, 5, 1]?",
            "Trace has_pair_sum([5], 10) by hand. When x is 5, what is target - x, and is it in numbers?",
            "Checking (target - x) in numbers allows the same element at the same index to pair with itself.",
            "Keep track of numbers you have already visited before the current index so you only pair two distinct positions."
        ]
    },
    {
        "id": "mirror-check",
        "title": "Mirror Check",
        "description": "Verify if a string reads the same forwards and backwards, ignoring case and non-alphanumeric characters.",
        "statement": "Write a function named `is_mirror(text)` that returns `True` if `text` is a palindrome when comparing alphanumeric characters case-insensitively, otherwise `False`.",
        "function_signature": "def is_mirror(text: str) -> bool",
        "grade": "Grade 3",
        "difficulty": "Medium",
        "tags": ["Strings", "Indexing"],
        "estimatedTime": "15 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(text) ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def is_mirror(text):\n    cleaned = text.lower()\n    return cleaned == cleaned[::-1]\n",
        "example": {
            "call": "is_mirror(\"Level\")",
            "expected": "True",
            "explanation": "\"level\" reads identically in reverse."
        },
        "visibleTests": [
            {"call": "is_mirror(\"Level\")", "expected": "True"},
            {"call": "is_mirror(\"sorcery\")", "expected": "False"},
            {"call": "is_mirror(\"A man a plan a canal Panama\")", "expected": "True"}
        ],
        "hiddenTests": [
            {"call": "is_mirror(\"racecar\")", "expected": "True"},
            {"call": "is_mirror(\"hello\")", "expected": "False"},
            {"call": "is_mirror(\"\")", "expected": "True"},
            {"call": "is_mirror(\"No 'x' in Nixon\")", "expected": "True"},
            {"call": "is_mirror(\"12321\")", "expected": "True"}
        ],
        "hints": [
            "Look at the third visible test case: why does a multi-word palindrome fail when you only lowercase the string?",
            "Trace what cleaned[::-1] looks like when spaces or apostrophes are left inside the string.",
            "Spaces and punctuation are not symmetric in phrases like 'A man a plan a canal Panama', so they cause the reversed comparison to fail.",
            "Filter the string to keep only alphanumeric characters (using a character method) in lowercase before comparing with its reverse."
        ]
    },
    {
        "id": "common-start",
        "title": "Common Start",
        "description": "Identify the longest common starting prefix shared across a list of strings.",
        "statement": "Write a function named `common_start(words)` that returns the longest string prefix shared by every word in the given list. If the list is empty or there is no common prefix, return `\"\"`.",
        "function_signature": "def common_start(words: list[str]) -> str",
        "grade": "Grade 2",
        "difficulty": "Hard",
        "tags": ["Strings", "Loops"],
        "estimatedTime": "25 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(words) ≤ 10⁴",
        "time_complexity": "O(S) where S is total characters",
        "starterCode": "def common_start(words):\n    prefix = words[0]\n    for word in words[1:]:\n        while not word.startswith(prefix):\n            prefix = prefix[:-1]\n    return prefix\n",
        "example": {
            "call": "common_start([\"domain\", \"domino\", \"domestic\"])",
            "expected": "\"dom\"",
            "explanation": "All three words start with 'dom'."
        },
        "visibleTests": [
            {"call": "common_start([\"domain\", \"domino\", \"domestic\"])", "expected": "\"dom\""},
            {"call": "common_start([\"flash\", \"spark\", \"bolt\"])", "expected": "\"\""},
            {"call": "common_start([\"curse\", \"cursed\", \"curiosity\"])", "expected": "\"cur\""}
        ],
        "hiddenTests": [
            {"call": "common_start([\"black\", \"blackout\", \"blacksmith\"])", "expected": "\"black\""},
            {"call": "common_start([\"a\"])", "expected": "\"a\""},
            {"call": "common_start([])", "expected": "\"\""},
            {"call": "common_start([\"same\", \"same\", \"same\"])", "expected": "\"same\""},
            {"call": "common_start([\"prefix\", \"prefer\", \"prepare\"])", "expected": "\"pre\""}
        ],
        "hints": [
            "All three visible tests pass, but what happens when the input list words is completely empty?",
            "Trace the very first line of your function when words is []. Which index is it trying to read?",
            "Indexing words[0] on an empty list raises an IndexError before the loop even starts.",
            "Add a check at the start of the function to handle an empty list before reading the first element."
        ]
    },
    {
        "id": "missing-step",
        "title": "Missing Step",
        "description": "Find the single missing value in an arithmetic progression.",
        "statement": "Write a function named `find_missing_step(sequence)` that receives an arithmetic sequence of at least 3 numbers where exactly one interior number is missing. Return that missing number.",
        "function_signature": "def find_missing_step(sequence: list[int]) -> int",
        "grade": "Grade 2",
        "difficulty": "Hard",
        "tags": ["Lists", "Comparison", "Loops"],
        "estimatedTime": "20 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "3 ≤ len(sequence) ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def find_missing_step(sequence):\n    n = len(sequence)\n    diff = (sequence[-1] - sequence[0]) // (n - 1)\n    for i in range(n - 1):\n        if sequence[i + 1] - sequence[i] != diff:\n            return sequence[i] + diff\n    return sequence[0]\n",
        "example": {
            "call": "find_missing_step([2, 4, 8, 10])",
            "expected": "6",
            "explanation": "The common difference is 2; 6 is the missing step."
        },
        "visibleTests": [
            {"call": "find_missing_step([2, 4, 8, 10])", "expected": "6"},
            {"call": "find_missing_step([10, 7, 1])", "expected": "4"},
            {"call": "find_missing_step([1, 3, 5, 9])", "expected": "7"}
        ],
        "hiddenTests": [
            {"call": "find_missing_step([10, 20, 40])", "expected": "30"},
            {"call": "find_missing_step([5, 10, 15, 25])", "expected": "20"},
            {"call": "find_missing_step([100, 90, 70])", "expected": "80"},
            {"call": "find_missing_step([0, 3, 9])", "expected": "6"},
            {"call": "find_missing_step([2, 6, 8])", "expected": "4"}
        ],
        "hints": [
            "Think about how many total steps exist between the first and last value when one number is missing from the sequence.",
            "Work out diff on [2, 4, 8, 10] by hand. Here n is 4, and the full sequence without a gap would have 5 numbers (4 steps).",
            "Dividing (sequence[-1] - sequence[0]) by (n - 1) forgets to count the missing step itself, producing the wrong step size.",
            "Divide the total span between the last and first element by n (the number of steps including the missing one)."
        ]
    },
    {
        "id": "balanced-brackets",
        "title": "Balanced Brackets",
        "description": "Check whether all brackets in a string have matching and correctly nested closers.",
        "statement": "Write a function named `is_balanced(expr)` that returns `True` if all parentheses `()`, square brackets `[]`, and curly braces `{}` are correctly paired and nested.",
        "function_signature": "def is_balanced(expr: str) -> bool",
        "grade": "Grade 2",
        "difficulty": "Hard",
        "tags": ["Strings", "Loops", "Lists"],
        "estimatedTime": "25 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(expr) ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def is_balanced(expr):\n    stack = []\n    pairs = {')': '(', ']': '[', '}': '{'}\n    for ch in expr:\n        if ch in pairs.values():\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return True\n",
        "example": {
            "call": "is_balanced(\"{[()]}\")",
            "expected": "True",
            "explanation": "All brackets are properly closed in correct order."
        },
        "visibleTests": [
            {"call": "is_balanced(\"{[()]}\")", "expected": "True"},
            {"call": "is_balanced(\"([)]\")", "expected": "False"},
            {"call": "is_balanced(\"({[\")", "expected": "False"}
        ],
        "hiddenTests": [
            {"call": "is_balanced(\"\")", "expected": "True"},
            {"call": "is_balanced(\"((()))\")", "expected": "True"},
            {"call": "is_balanced(\"][\")", "expected": "False"},
            {"call": "is_balanced(\"(()\")", "expected": "False"},
            {"call": "is_balanced(\"{[]}\")", "expected": "True"}
        ],
        "hints": [
            "What happens when the input string contains only opening brackets, like '({[' or '(()'?",
            "Trace your function on is_balanced('({['). What is inside stack when the loop finishes, and what does the final line return?",
            "Returning True unconditionally at the end ignores any unclosed opening brackets still sitting on the stack.",
            "At the end of the loop, check that the stack is completely empty before returning True."
        ]
    },
    {
        "id": "frequency-count",
        "title": "Character Frequency",
        "description": "Count occurrences of each unique character in lowercase, ignoring spaces.",
        "statement": "Write a function named `char_frequency(text)` that returns a dictionary mapping each distinct lowercase character in `text` to its total frequency count. Ignore whitespace characters.",
        "function_signature": "def char_frequency(text: str) -> dict[str, int]",
        "grade": "Grade 3",
        "difficulty": "Medium",
        "tags": ["Strings", "Loops"],
        "estimatedTime": "15 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(text) ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def char_frequency(text):\n    freq = {}\n    for ch in text:\n        if not ch.isspace():\n            freq[ch] = freq.get(ch, 0) + 1\n    return freq\n",
        "example": {
            "call": "char_frequency(\"seal\")",
            "expected": "{'s': 1, 'e': 1, 'a': 1, 'l': 1}",
            "explanation": "Each character appears once."
        },
        "visibleTests": [
            {"call": "char_frequency(\"seal\")", "expected": "{'s': 1, 'e': 1, 'a': 1, 'l': 1}"},
            {"call": "char_frequency(\"banana\")", "expected": "{'b': 1, 'a': 3, 'n': 2}"},
            {"call": "char_frequency(\"a a\")", "expected": "{'a': 2}"}
        ],
        "hiddenTests": [
            {"call": "char_frequency(\"curse\")", "expected": "{'c': 1, 'u': 1, 'r': 1, 's': 1, 'e': 1}"},
            {"call": "char_frequency(\"\")", "expected": "{}"},
            {"call": "char_frequency(\"GoJo\")", "expected": "{'g': 1, 'o': 2, 'j': 1}"},
            {"call": "char_frequency(\"xyz\")", "expected": "{'x': 1, 'y': 1, 'z': 1}"},
            {"call": "char_frequency(\"  \")", "expected": "{}"}
        ],
        "hints": [
            "All three visible examples use lowercase letters, but what happens when the input string contains uppercase letters?",
            "Trace your function on a word with mixed case like 'GoJo'. Does 'G' get counted together with 'g'?",
            "Iterating over text directly without normalizing case treats uppercase and lowercase letters as separate keys.",
            "Convert the input text (or each character) to lowercase before updating the dictionary counts."
        ]
    },
    {
        "id": "streak-counter",
        "title": "Longest Streak",
        "description": "Calculate the maximum length of consecutive occurrences of target in a list.",
        "statement": "Write a function named `longest_streak(values, target)` that returns the maximum number of consecutive times `target` appears in the sequence `values`.",
        "function_signature": "def longest_streak(values: list, target: any) -> int",
        "grade": "Grade 4",
        "difficulty": "Easy",
        "tags": ["Loops", "Comparison"],
        "estimatedTime": "10 min",
        "time_limit_ms": 500,
        "memory_limit_mb": 64,
        "input_constraints": "0 ≤ len(values) ≤ 10⁵",
        "time_complexity": "O(n)",
        "starterCode": "def longest_streak(values, target):\n    max_streak = 0\n    current = 0\n    for val in values:\n        if val == target:\n            current += 1\n        else:\n            if current > max_streak:\n                max_streak = current\n            current = 0\n    return max_streak\n",
        "example": {
            "call": "longest_streak([1, 1, 0, 1, 1, 1, 0], 1)",
            "expected": "3",
            "explanation": "The longest contiguous run of 1s has length 3."
        },
        "visibleTests": [
            {"call": "longest_streak([1, 1, 0, 1, 1, 1, 0], 1)", "expected": "3"},
            {"call": "longest_streak([0, 0, 0], 1)", "expected": "0"},
            {"call": "longest_streak(['a', 'a', 'b', 'a'], 'a')", "expected": "2"}
        ],
        "hiddenTests": [
            {"call": "longest_streak([1, 2, 2, 2, 2, 1], 2)", "expected": "4"},
            {"call": "longest_streak([], 5)", "expected": "0"},
            {"call": "longest_streak([7, 7, 7, 7], 7)", "expected": "4"},
            {"call": "longest_streak([1, 0, 1, 0], 1)", "expected": "1"},
            {"call": "longest_streak([4, 5, 6], 10)", "expected": "0"}
        ],
        "hints": [
            "What happens when the longest streak of target values is at the very end of the list, with no non-matching element after it?",
            "Trace longest_streak([7, 7, 7, 7], 7) by hand. Does the else branch ever run?",
            "Because max_streak is only updated inside the else branch, a streak that continues until the end of the list is never recorded.",
            "Update max_streak immediately whenever current increases (or once more after the loop finishes)."
        ]
    }
]
