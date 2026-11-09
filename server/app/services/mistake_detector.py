"""
Deterministic Mistake Taxonomy & Detection Engine.

Classifies failed submissions into the 5 core Debug Dojo mistake categories:
1. off_by_one
2. unhandled_short_input
3. print_not_return
4. boundary_comparison
5. mutates_input

And separates non-core one-off slips so they never pollute recurring mistakes:
- syntax_or_name_error
- infinite_loop
- hardcoded_values
- other_logic_error
"""
from __future__ import annotations

import ast
from typing import Any

CORE_MISTAKE_SLUGS = frozenset({
    "off_by_one",
    "unhandled_short_input",
    "print_not_return",
    "boundary_comparison",
    "mutates_input",
})


def _extract_call_args(call_str: str) -> list[Any]:
    """Safely parse literal arguments from a test call string (server-side only)."""
    try:
        tree = ast.parse(call_str.strip(), mode="eval")
        if isinstance(tree.body, ast.Call):
            return [ast.literal_eval(arg) for arg in tree.body.args]
    except Exception:
        pass
    return []


def _is_short_or_empty_case(call_str: str) -> tuple[bool, str]:
    """
    Determine whether a test case represents an empty, short, or k > len(list) input.
    Returns (is_short, safe_category_description).
    """
    args = _extract_call_args(call_str)
    if not args:
        if "[]" in call_str or '""' in call_str:
            return True, "an empty input"
        return False, ""

    first = args[0]
    # Case 1: (list, k) where k > len(list) or list is empty or k == 0
    if isinstance(first, list) and len(args) >= 2 and isinstance(args[1], int):
        k = args[1]
        if k > len(first):
            return True, "cases where k is larger than the number of items in the list"
        if len(first) == 0:
            return True, "an empty list"
        if k == 0:
            return True, "cases where k is 0"

    # Case 2: single list argument
    if isinstance(first, list):
        if len(first) == 0:
            return True, "an empty list"
        if "middle_three" in call_str and len(first) < 3:
            return True, "lists with fewer than 3 items"
        if len(first) == 1:
            return True, "a single-element list"

    # Case 3: string argument
    if isinstance(first, str) and len(first) == 0:
        return True, "an empty string"

    # Case 4: integer n == 0
    if isinstance(first, int) and first == 0:
        return True, "the case when n is 0"

    return False, ""


def _is_boundary_threshold_case(call_str: str) -> bool:
    """Determine if a test case specifically probes a comparison threshold (e.g. 40 in count_passes)."""
    args = _extract_call_args(call_str)
    if not args:
        return False
    first = args[0]
    if "count_passes" in call_str and isinstance(first, list):
        return 40 in first or 39 in first
    if isinstance(first, list) and len(args) >= 2 and isinstance(args[1], int):
        return len(first) == args[1] or args[1] == 0
    return False


def _analyze_ast(source_code: str) -> dict[str, bool]:
    """Inspect learner AST for structural mistake signatures."""
    flags = {
        "syntax_error": False,
        "has_print": False,
        "has_value_return": False,
        "has_in_place_mutation": False,
        "has_strict_comparison": False,
        "has_inclusive_comparison": False,
        "has_range_without_plus_one": False,
        "has_slice_off_by_one": False,
        "has_unclamped_len_minus_k": False,
        "has_negative_slice_without_zero_guard": False,
        "has_short_len_guard": False,
        "only_constant_return": False,
    }
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        flags["syntax_error"] = True
        return flags

    func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    target_node = func_defs[0] if func_defs else tree
    param_names = {arg.arg for arg in func_defs[0].args.args} if func_defs else set()

    return_nodes = []
    has_k_zero_guard = False

    for node in ast.walk(target_node):
        # 1. Print call detection
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            flags["has_print"] = True

        # 2. Return value detection
        if isinstance(node, ast.Return):
            return_nodes.append(node)
            if node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
                flags["has_value_return"] = True

        # 3. In-place mutation detection on parameter names (.sort, .pop, .reverse, .append, .clear, .remove)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in param_names
                and node.func.attr in {"sort", "pop", "reverse", "append", "extend", "insert", "remove", "clear"}
            ):
                flags["has_in_place_mutation"] = True

        if isinstance(node, (ast.Delete, ast.Assign, ast.AugAssign)):
            targets = (
                node.targets
                if isinstance(node, (ast.Delete, ast.Assign))
                else [node.target]
            )
            for t in targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id in param_names:
                    flags["has_in_place_mutation"] = True

        # 4. Comparison operators (<, > vs <=, >=)
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.Lt, ast.Gt)):
                    flags["has_strict_comparison"] = True
                elif isinstance(op, (ast.LtE, ast.GtE)):
                    flags["has_inclusive_comparison"] = True
            unparsed = ast.unparse(node)
            if ("k == 0" in unparsed or "k <= 0" in unparsed or "not k" in unparsed):
                has_k_zero_guard = True
            if "len(" in unparsed and any(
                isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq)) for op in node.ops
            ):
                flags["has_short_len_guard"] = True

        # 5. Range bounds check: range(1, n) or range(len(...) - 1) or range(len(marks) - k, ...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                start_src = ast.unparse(node.args[0])
                stop_src = ast.unparse(node.args[1])
                if start_src == "1" and "+" not in stop_src:
                    flags["has_range_without_plus_one"] = True
                if "len(" in start_src and "-" in start_src and "max(" not in start_src:
                    flags["has_unclamped_len_minus_k"] = True
            elif len(node.args) == 1:
                stop_src = ast.unparse(node.args[0])
                if "len(" in stop_src and "- 1" in stop_src:
                    flags["has_range_without_plus_one"] = True

        # 6. Slice bounds check: items[mid - 1 : mid + 1] or marks[-k:]
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            lower_src = ast.unparse(node.slice.lower) if node.slice.lower else ""
            upper_src = ast.unparse(node.slice.upper) if node.slice.upper else ""
            if lower_src.startswith("-") and not lower_src[1:].isdigit():
                flags["has_negative_slice_without_zero_guard"] = True
            if "mid - 1" in lower_src and ("mid + 1" in upper_src or upper_src == "mid"):
                flags["has_slice_off_by_one"] = True
            if upper_src == "-1":
                flags["has_slice_off_by_one"] = True

    if has_k_zero_guard:
        flags["has_negative_slice_without_zero_guard"] = False

    # Check if the function body is just returning a hardcoded constant (e.g. `return 0` or `return -999`)
    if func_defs:
        stmts = [
            s for s in func_defs[0].body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
        ]
        if len(stmts) == 1 and isinstance(stmts[0], ast.Return) and isinstance(stmts[0].value, (ast.Constant, ast.UnaryOp)):
            flags["only_constant_return"] = True

    return flags


def detect_mistakes(
    challenge_slug: str,
    source_code: str,
    test_cases: list[dict],
    raw_results: list[dict],
) -> list[str]:
    """
    Analyze a failed submission and return a list of distinct mistake category tags.
    Guarantees that the 5 core categories are kept distinct and one-off slips
    (syntax/name errors, timeouts, trivial constants) do not falsely trigger core tags.
    """
    if all(r.get("outcome") == "passed" for r in raw_results):
        return []

    ast_flags = _analyze_ast(source_code)

    # 0. Check for pure syntax / name / import errors or timeouts first
    if ast_flags["syntax_error"] or all(
        r.get("error_type") in {"SyntaxError", "NameError", "IndentationError", "UnboundLocalError", "ImportError"}
        for r in raw_results
        if r.get("outcome") != "passed"
    ):
        return ["syntax_or_name_error"]

    if any(r.get("outcome") == "timeout" for r in raw_results) and not any(
        r.get("outcome") in {"wrong_output", "runtime_error"} for r in raw_results
    ):
        return ["infinite_loop"]

    tags: list[str] = []

    # 1. mutates_input: Runner detected in-place mutation of an input collection
    if any(r.get("mutated") for r in raw_results):
        tags.append("mutates_input")

    # 2. print_not_return: Prints output and returns None on failing tests
    all_wrong_are_none = any(r.get("outcome") == "wrong_output" for r in raw_results) and all(
        r.get("actual_output") is None or str(r.get("actual_output")).strip() == "None"
        for r in raw_results
        if r.get("outcome") == "wrong_output"
    )
    if (ast_flags["has_print"] and (all_wrong_are_none or not ast_flags["has_value_return"])) or (
        any(r.get("printed_stdout") for r in raw_results) and all_wrong_are_none
    ):
        tags.append("print_not_return")
        return tags

    # If the learner only wrote a stub like `return 0` or `return -999`, do not misclassify as a subtle boundary/short-input bug
    if ast_flags["only_constant_return"] and not tags:
        return ["other_logic_error"]

    # Partition test outcomes by test type
    short_failed = False
    normal_passed = False
    normal_failed = False
    boundary_failed = False

    for tc, res in zip(test_cases, raw_results):
        call_str = tc.get("description") or ""
        is_short, _ = _is_short_or_empty_case(call_str)
        is_bound = _is_boundary_threshold_case(call_str)
        passed = res.get("outcome") == "passed"

        if is_short:
            if not passed:
                short_failed = True
        else:
            if passed:
                normal_passed = True
            else:
                normal_failed = True

        if is_bound and not passed:
            boundary_failed = True

    # 3. unhandled_short_input:
    # Fails on short/empty/k>len cases while passing at least one normal case, OR has known unclamped short-input AST bug
    has_index_error = any(r.get("error_type") == "IndexError" for r in raw_results)
    if (
        short_failed
        and (
            normal_passed
            or has_index_error
            or ast_flags["has_unclamped_len_minus_k"]
            or ast_flags["has_negative_slice_without_zero_guard"]
        )
    ) or ("middle" in challenge_slug and not ast_flags["has_short_len_guard"]):
        tags.append("unhandled_short_input")

    # 4. boundary_comparison:
    # Uses `<` or `>` instead of `<=` or `>=` on threshold comparison, or fails boundary threshold cases while passing non-boundary cases
    if (
        ("count" in challenge_slug and ast_flags["has_strict_comparison"] and not ast_flags["has_inclusive_comparison"])
        or (boundary_failed and normal_passed and ast_flags["has_strict_comparison"] and "unhandled_short_input" not in tags)
    ):
        tags.append("boundary_comparison")

    # 5. off_by_one:
    # AST has off-by-one loop/slice bounds, OR normal tests fail with an off-by-one length/index pattern
    if (
        ast_flags["has_range_without_plus_one"]
        or ast_flags["has_slice_off_by_one"]
        or (normal_failed and has_index_error and "unhandled_short_input" not in tags)
    ):
        tags.append("off_by_one")

    # Check if visible outputs differ by 1 item or 1 step from expected
    if "off_by_one" not in tags and "boundary_comparison" not in tags and "unhandled_short_input" not in tags:
        for tc, res in zip(test_cases, raw_results):
            if res.get("outcome") == "wrong_output" and res.get("actual_output") is not None:
                try:
                    exp_val = ast.literal_eval(str(tc.get("expected_output", "")))
                    got_val = ast.literal_eval(str(res.get("actual_output", "")))
                    if isinstance(exp_val, list) and isinstance(got_val, list) and len(exp_val) > 0:
                        if abs(len(exp_val) - len(got_val)) == 1 and (
                            exp_val[:-1] == got_val or exp_val[1:] == got_val
                        ):
                            tags.append("off_by_one")
                            break
                except Exception:
                    pass

    if not tags:
        tags.append("other_logic_error")

    return tags


def summarize_hidden_failure_patterns(test_cases: list[dict], raw_results: list[dict]) -> dict[str, Any]:
    """
    Build a strictly confidential summary of hidden test outcomes and input categories.
    NEVER includes hidden input values, expected outputs, actual outputs, or exception messages.
    """
    hidden_total = 0
    hidden_passed = 0
    hidden_wrong = 0
    hidden_errors = 0
    hidden_timeouts = 0
    categories: list[str] = []

    for tc, res in zip(test_cases, raw_results):
        if tc.get("visibility") != "hidden":
            continue
        hidden_total += 1
        outcome = res.get("outcome")
        if outcome == "passed":
            hidden_passed += 1
            continue
        if outcome == "wrong_output":
            hidden_wrong += 1
        elif outcome == "runtime_error":
            hidden_errors += 1
        elif outcome == "timeout":
            hidden_timeouts += 1

        call_str = tc.get("description") or ""
        is_short, desc = _is_short_or_empty_case(call_str)
        if is_short and desc and desc not in categories:
            categories.append(desc)
        elif _is_boundary_threshold_case(call_str):
            b_desc = "inputs right on the boundary value"
            if b_desc not in categories:
                categories.append(b_desc)

    return {
        "hidden_total": hidden_total,
        "hidden_passed": hidden_passed,
        "hidden_failed": hidden_total - hidden_passed,
        "hidden_wrong": hidden_wrong,
        "hidden_errors": hidden_errors,
        "hidden_timeouts": hidden_timeouts,
        "categories": categories,
    }
