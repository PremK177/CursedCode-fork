export const CHALLENGES = [
  {
    id: 'last-k-total',
    slug: 'last-k-total',
    title: 'Last K Total',
    description: 'Return the total of the last k marks, or of all marks if k is larger than the list.',
    statement: 'Write a function named `last_k_total(marks, k)` that takes a list of integers `marks` (possibly empty) and an integer `k` (0 or more). It returns the total of the last `k` marks, or the total of all marks if `k` is larger than the list.',
    function_signature: 'def last_k_total(marks: list[int], k: int) -> int',
    grade: 'Grade 4',
    difficulty: 'Easy',
    tags: ['Lists', 'Slicing', 'Loops'],
    status: 'New',
    estimatedTime: '10 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(marks) ≤ 10⁵; -10⁹ ≤ marks[i] ≤ 10⁹; k ≥ 0',
      time_complexity: 'O(min(n, k))'
    },
    starterCode: `def last_k_total(marks, k):
    total = 0
    for i in range(len(marks) - k, len(marks)):
        total += marks[i]
    return total
`,
    example: {
      call: 'last_k_total([10, 20, 30, 40], 2)',
      expected: '70',
      explanation: 'The last 2 marks are 30 and 40. Their total is 70.'
    },
    visibleTests: [
      { test: 1, call: 'last_k_total([10, 20, 30, 40], 2)', expected: '70' },
      { test: 2, call: 'last_k_total([5, 5, 5], 3)', expected: '15' },
      { test: 3, call: 'last_k_total([7], 1)', expected: '7' }
    ],
    hiddenTestCount: 6
  },
  {
    id: 'count-passes',
    slug: 'count-passes',
    title: 'Count Passes',
    description: 'Count how many marks in a list are 40 or more.',
    statement: 'Write a function named `count_passes(marks)` that takes a list of integer `marks` (possibly empty) and returns how many of them are 40 or more.',
    function_signature: 'def count_passes(marks: list[int]) -> int',
    grade: 'Grade 4',
    difficulty: 'Easy',
    tags: ['Loops', 'Comparison'],
    status: 'New',
    estimatedTime: '10 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(marks) ≤ 10⁵; -10⁹ ≤ marks[i] ≤ 10⁹',
      time_complexity: 'O(n)'
    },
    starterCode: `def count_passes(marks):
    count = 0
    for mark in marks:
        if mark > 40:
            count += 1
    return count
`,
    example: {
      call: 'count_passes([30, 40, 50])',
      expected: '2',
      explanation: 'Marks 40 and 50 are 40 or more, so the count is 2.'
    },
    visibleTests: [
      { test: 1, call: 'count_passes([30, 40, 50])', expected: '2' },
      { test: 2, call: 'count_passes([10, 20, 30])', expected: '0' },
      { test: 3, call: 'count_passes([40, 40, 40])', expected: '3' }
    ],
    hiddenTestCount: 6
  },
  {
    id: 'first-n-squares',
    slug: 'first-n-squares',
    title: 'First N Squares',
    description: 'Build and return the list [1, 4, 9, ..., n²], or [] when n is 0.',
    statement: 'Write a function named `first_n_squares(n)` that receives an integer `n` (0 or more) and returns the list `[1, 4, 9, ..., n²]`, or `[]` when `n` is 0.',
    function_signature: 'def first_n_squares(n: int) -> list[int]',
    grade: 'Grade 4',
    difficulty: 'Easy',
    tags: ['Loops', 'Lists'],
    status: 'New',
    estimatedTime: '10 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ n ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def first_n_squares(n):
    result = []
    for i in range(1, n):
        result.append(i * i)
    return result
`,
    example: {
      call: 'first_n_squares(4)',
      expected: '[1, 4, 9, 16]',
      explanation: 'The first 4 positive integers squared are 1, 4, 9, and 16.'
    },
    visibleTests: [
      { test: 1, call: 'first_n_squares(4)', expected: '[1, 4, 9, 16]' },
      { test: 2, call: 'first_n_squares(1)', expected: '[1]' },
      { test: 3, call: 'first_n_squares(0)', expected: '[]' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'middle-three',
    slug: 'middle-three',
    title: 'Middle Three',
    description: 'Return the middle three items as a list, or the whole list if it has fewer than 3 items.',
    statement: 'Write a function named `middle_three(items)` that takes a list `items` of odd length, or with fewer than 3 items. Return the middle three items as a list, or the whole list if it has fewer than 3 items.',
    function_signature: 'def middle_three(items: list) -> list',
    grade: 'Grade 3',
    difficulty: 'Medium',
    tags: ['Lists', 'Indexing', 'Slicing'],
    status: 'New',
    estimatedTime: '15 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(items) ≤ 10⁵; len(items) is odd or < 3',
      time_complexity: 'O(1)'
    },
    starterCode: `def middle_three(items):
    mid = len(items) // 2
    return items[mid - 1 : mid + 1]
`,
    example: {
      call: 'middle_three([1, 2, 3, 4, 5])',
      expected: '[2, 3, 4]',
      explanation: 'The center element is 3. The middle 3 items are [2, 3, 4].'
    },
    visibleTests: [
      { test: 1, call: 'middle_three([1, 2, 3, 4, 5])', expected: '[2, 3, 4]' },
      { test: 2, call: 'middle_three([\'a\', \'b\', \'c\'])', expected: "['a', 'b', 'c']" },
      { test: 3, call: 'middle_three([10, 20, 30, 40, 50, 60, 70])', expected: '[30, 40, 50]' }
    ],
    hiddenTestCount: 6
  },
  {
    id: 'word-boundary',
    slug: 'word-boundary',
    title: 'Word Boundary',
    description: 'Determine whether a sentence starts or ends with a specific target keyword.',
    statement: 'Write a function named `is_at_boundary(sentence, keyword)` that checks if the given `sentence` either begins with or concludes with the exact string `keyword` (case-sensitive). If `keyword` is empty or `sentence` is shorter than `keyword`, return `False`.',
    function_signature: 'def is_at_boundary(sentence: str, keyword: str) -> bool',
    grade: 'Grade 3',
    difficulty: 'Medium',
    tags: ['Strings', 'Comparison', 'Slicing'],
    status: 'New',
    estimatedTime: '15 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(sentence), len(keyword) ≤ 10⁴',
      time_complexity: 'O(len(keyword))'
    },
    starterCode: `def is_at_boundary(sentence, keyword):
    k = len(keyword)
    return sentence[:k] == keyword and sentence[-k:] == keyword
`,
    example: {
      call: 'is_at_boundary("curse energy flows", "curse")',
      expected: 'True',
      explanation: "The sentence starts with 'curse'."
    },
    visibleTests: [
      { test: 1, call: 'is_at_boundary("curse energy flows", "curse")', expected: 'True' },
      { test: 2, call: 'is_at_boundary("the quiet realm", "realm")', expected: 'True' },
      { test: 3, call: 'is_at_boundary("inside the barrier now", "barrier")', expected: 'False' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'pair-sum',
    slug: 'pair-sum',
    title: 'Pair Sum',
    description: 'Find two distinct elements in a list whose sum equals the target value.',
    statement: 'Write a function named `has_pair_sum(numbers, target)` that returns `True` if any two elements at different positions in the list `numbers` sum to `target`, otherwise `False`.',
    function_signature: 'def has_pair_sum(numbers: list[int], target: int) -> bool',
    grade: 'Grade 3',
    difficulty: 'Medium',
    tags: ['Loops', 'Lists'],
    status: 'New',
    estimatedTime: '20 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(numbers) ≤ 10⁴',
      time_complexity: 'O(n)'
    },
    starterCode: `def has_pair_sum(numbers, target):
    for x in numbers:
        if (target - x) in numbers:
            return True
    return False
`,
    example: {
      call: 'has_pair_sum([2, 7, 11, 15], 9)',
      expected: 'True',
      explanation: '2 + 7 equals 9.'
    },
    visibleTests: [
      { test: 1, call: 'has_pair_sum([2, 7, 11, 15], 9)', expected: 'True' },
      { test: 2, call: 'has_pair_sum([3, 5, 1], 10)', expected: 'False' },
      { test: 3, call: 'has_pair_sum([5], 10)', expected: 'False' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'mirror-check',
    slug: 'mirror-check',
    title: 'Mirror Check',
    description: 'Verify if a string reads the same forwards and backwards, ignoring case and non-alphanumeric characters.',
    statement: 'Write a function named `is_mirror(text)` that returns `True` if `text` is a palindrome when comparing alphanumeric characters case-insensitively, otherwise `False`.',
    function_signature: 'def is_mirror(text: str) -> bool',
    grade: 'Grade 3',
    difficulty: 'Medium',
    tags: ['Strings', 'Indexing'],
    status: 'New',
    estimatedTime: '15 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(text) ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def is_mirror(text):
    cleaned = text.lower()
    return cleaned == cleaned[::-1]
`,
    example: {
      call: 'is_mirror("Level")',
      expected: 'True',
      explanation: '"level" reads identically in reverse.'
    },
    visibleTests: [
      { test: 1, call: 'is_mirror("Level")', expected: 'True' },
      { test: 2, call: 'is_mirror("sorcery")', expected: 'False' },
      { test: 3, call: 'is_mirror("A man a plan a canal Panama")', expected: 'True' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'common-start',
    slug: 'common-start',
    title: 'Common Start',
    description: 'Identify the longest common starting prefix shared across a list of strings.',
    statement: 'Write a function named `common_start(words)` that returns the longest string prefix shared by every word in the given list. If the list is empty or there is no common prefix, return `""`.',
    function_signature: 'def common_start(words: list[str]) -> str',
    grade: 'Grade 2',
    difficulty: 'Hard',
    tags: ['Strings', 'Loops'],
    status: 'New',
    estimatedTime: '25 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(words) ≤ 10⁴',
      time_complexity: 'O(S)'
    },
    starterCode: `def common_start(words):
    prefix = words[0]
    for word in words[1:]:
        while not word.startswith(prefix):
            prefix = prefix[:-1]
    return prefix
`,
    example: {
      call: 'common_start(["domain", "domino", "domestic"])',
      expected: '"dom"',
      explanation: "All three words start with 'dom'."
    },
    visibleTests: [
      { test: 1, call: 'common_start(["domain", "domino", "domestic"])', expected: '"dom"' },
      { test: 2, call: 'common_start(["flash", "spark", "bolt"])', expected: '""' },
      { test: 3, call: 'common_start(["curse", "cursed", "curiosity"])', expected: '"cur"' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'missing-step',
    slug: 'missing-step',
    title: 'Missing Step',
    description: 'Find the single missing value in an arithmetic progression.',
    statement: 'Write a function named `find_missing_step(sequence)` that receives an arithmetic sequence of at least 3 numbers where exactly one interior number is missing. Return that missing number.',
    function_signature: 'def find_missing_step(sequence: list[int]) -> int',
    grade: 'Grade 2',
    difficulty: 'Hard',
    tags: ['Lists', 'Comparison', 'Loops'],
    status: 'New',
    estimatedTime: '20 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '3 ≤ len(sequence) ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def find_missing_step(sequence):
    n = len(sequence)
    diff = (sequence[-1] - sequence[0]) // (n - 1)
    for i in range(n - 1):
        if sequence[i + 1] - sequence[i] != diff:
            return sequence[i] + diff
    return sequence[0]
`,
    example: {
      call: 'find_missing_step([2, 4, 8, 10])',
      expected: '6',
      explanation: 'The common difference is 2; 6 is the missing step.'
    },
    visibleTests: [
      { test: 1, call: 'find_missing_step([2, 4, 8, 10])', expected: '6' },
      { test: 2, call: 'find_missing_step([10, 7, 1])', expected: '4' },
      { test: 3, call: 'find_missing_step([1, 3, 5, 9])', expected: '7' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'balanced-brackets',
    slug: 'balanced-brackets',
    title: 'Balanced Brackets',
    description: 'Check whether all brackets in a string have matching and correctly nested closers.',
    statement: 'Write a function named `is_balanced(expr)` that returns `True` if all parentheses `()`, square brackets `[]`, and curly braces `{}` are correctly paired and nested.',
    function_signature: 'def is_balanced(expr: str) -> bool',
    grade: 'Grade 2',
    difficulty: 'Hard',
    tags: ['Strings', 'Loops', 'Lists'],
    status: 'New',
    estimatedTime: '25 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(expr) ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def is_balanced(expr):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for ch in expr:
        if ch in pairs.values():
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return True
`,
    example: {
      call: 'is_balanced("{[()]}")',
      expected: 'True',
      explanation: 'All brackets are properly closed in correct order.'
    },
    visibleTests: [
      { test: 1, call: 'is_balanced("{[()]}")', expected: 'True' },
      { test: 2, call: 'is_balanced("([)]")', expected: 'False' },
      { test: 3, call: 'is_balanced("({[")', expected: 'False' }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'frequency-count',
    slug: 'frequency-count',
    title: 'Character Frequency',
    description: 'Count occurrences of each unique character in lowercase, ignoring spaces.',
    statement: 'Write a function named `char_frequency(text)` that returns a dictionary mapping each distinct lowercase character in `text` to its total frequency count. Ignore whitespace characters.',
    function_signature: 'def char_frequency(text: str) -> dict[str, int]',
    grade: 'Grade 3',
    difficulty: 'Medium',
    tags: ['Strings', 'Loops'],
    status: 'New',
    estimatedTime: '15 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(text) ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def char_frequency(text):
    freq = {}
    for ch in text:
        if not ch.isspace():
            freq[ch] = freq.get(ch, 0) + 1
    return freq
`,
    example: {
      call: 'char_frequency("seal")',
      expected: "{'s': 1, 'e': 1, 'a': 1, 'l': 1}",
      explanation: 'Each character appears once.'
    },
    visibleTests: [
      { test: 1, call: 'char_frequency("seal")', expected: "{'s': 1, 'e': 1, 'a': 1, 'l': 1}" },
      { test: 2, call: 'char_frequency("banana")', expected: "{'b': 1, 'a': 3, 'n': 2}" },
      { test: 3, call: 'char_frequency("a a")', expected: "{'a': 2}" }
    ],
    hiddenTestCount: 5
  },
  {
    id: 'streak-counter',
    slug: 'streak-counter',
    title: 'Longest Streak',
    description: 'Calculate the maximum length of consecutive occurrences of target in a list.',
    statement: 'Write a function named `longest_streak(values, target)` that returns the maximum number of consecutive times `target` appears in the sequence `values`.',
    function_signature: 'def longest_streak(values: list, target: any) -> int',
    grade: 'Grade 4',
    difficulty: 'Easy',
    tags: ['Loops', 'Comparison'],
    status: 'New',
    estimatedTime: '10 min',
    constraints: {
      time_limit_ms: 500,
      memory_limit_mb: 64,
      input_constraints: '0 ≤ len(values) ≤ 10⁵',
      time_complexity: 'O(n)'
    },
    starterCode: `def longest_streak(values, target):
    max_streak = 0
    current = 0
    for val in values:
        if val == target:
            current += 1
        else:
            if current > max_streak:
                max_streak = current
            current = 0
    return max_streak
`,
    example: {
      call: 'longest_streak([1, 1, 0, 1, 1, 1, 0], 1)',
      expected: '3',
      explanation: 'The longest contiguous run of 1s has length 3.'
    },
    visibleTests: [
      { test: 1, call: 'longest_streak([1, 1, 0, 1, 1, 1, 0], 1)', expected: '3' },
      { test: 2, call: 'longest_streak([0, 0, 0], 1)', expected: '0' },
      { test: 3, call: "longest_streak(['a', 'a', 'b', 'a'], 'a')", expected: '2' }
    ],
    hiddenTestCount: 5
  }
];

export const CONCEPTS = [
  'Lists',
  'Loops',
  'Strings',
  'Slicing',
  'Indexing',
  'Comparison'
];

export const GRADE_SCALE = [
  { grade: 'Grade 4', difficulty: 'Easy', minScore: 0.0 },
  { grade: 'Grade 3', difficulty: 'Medium', minScore: 0.2 },
  { grade: 'Grade 2', difficulty: 'Hard', minScore: 0.4 },
  { grade: 'Semi-Grade 1', difficulty: 'Advanced', minScore: 0.6 },
  { grade: 'Grade 1', difficulty: 'Expert', minScore: 0.8 },
  { grade: 'Special Grade', difficulty: 'Supreme', minScore: 0.93 }
];

export const STATUSES = ['New', 'Attempted', 'Solved'];
