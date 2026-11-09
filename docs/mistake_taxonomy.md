# Debug Dojo — Mistake Taxonomy & Detection Specification

Per **Requirement 7 of Debug Dojo**, every failed submission is analyzed using AST static analysis and test-outcome differential evidence, then tagged with distinct mistake categories. A mistake category is marked as **recurring** once it is detected across at least **2 distinct challenges** for a learner.

---

## The 5 Core Categories & Detection Logic

| Category Slug | Display Name | What It Means | Deterministic Detection Logic (`mistake_detector.py`) |
|---|---|---|---|
| `off_by_one` | **Off by one** | Loop bound or slice range stops one step too early or goes one step too far. | • AST detects `range(1, n)` missing `+ 1`, `range(len(x) - 1)`, or slice `items[mid - 1 : mid + 1]` instead of `mid + 2`.<br>• Differential output check detects returned list is prefix/suffix off by 1 element from expected, or raises `IndexError` on standard-length inputs. |
| `unhandled_short_input` | **Short input not handled** | Code crashes (`IndexError`) or gives wrong output on empty inputs (`[]`, `""`), `n = 0`, `k = 0`, `< 3` items, or `k > len(list)`. | • Submission fails on empty/short/`k > len(marks)` test cases while passing standard-length cases.<br>• AST detects unclamped `range(len(marks) - k, ...)` without `max(0, ...)`, negative slice `marks[-k:]` without `k == 0` guard, or unguarded `words[0]` / `items[mid - 1 : ...]` when `< 3` items. |
| `print_not_return` | **Printed instead of returned** | Function prints the computed result to stdout instead of returning it, yielding `None` to the caller. | • AST contains `print(...)` inside the function and lacks a value-returning `return` statement, OR<br>• Runner captures non-empty user stdout while all failing tests return `None`. |
| `boundary_comparison` | **Boundary comparison** | Strict comparison (`<` or `>`) used where inclusive comparison (`<=` or `>=`) is required at the exact threshold (or vice versa). | • AST detects strict `<` or `>` comparison against threshold constants (e.g. `mark > 40` instead of `mark >= 40`), AND/OR<br>• Submission passes non-boundary cases while failing threshold test cases. |
| `mutates_input` | **Changes the input** | Function modifies caller's input list/dictionary in-place (`.sort()`, `.pop()`, `.reverse()`, `.append()`, `del`, or index assignment). | • Test harness snapshots input arguments with `copy.deepcopy()` prior to invocation and compares post-execution state (`arg != snapshot`).<br>• AST detects mutating method calls or subscript assignments on parameter variables. |

---

## Secondary Categories (Isolating One-Off Slips)

To ensure one-off slips never falsely trigger a core recurring mistake:
- **`syntax_or_name_error`**: Triggered on `SyntaxError`, `IndentationError`, `NameError`, `UnboundLocalError`, or `ImportError`.
- **`infinite_loop`**: Triggered when execution exceeds the CPU/wall-clock timeout (`timeout`).
- **`hardcoded_values`**: Triggered when the function only returns hardcoded literal constants matching sample outputs.
- **`other_logic_error`**: Safe fallback when a submission fails general logic assertions without matching any of the 5 specific structural mistake patterns.

---

## Recurring Mistake & Recommendation Engine

1. **Recurrence Rule**: A core mistake category is marked as **recurring** in `GET /api/learner/{learner_id}` only when it appears in submissions across **$\ge 2$ distinct `challenge_id`s**. Multiple failed attempts on the same challenge count as 1 challenge.
2. **Targeted Next Challenge**: When a learner has one or more recurring mistakes, the recommendation engine selects an unsolved challenge specifically mapped to practise the top recurring mistake category and explains why (naming the mistake category and how many challenges it appeared in).
