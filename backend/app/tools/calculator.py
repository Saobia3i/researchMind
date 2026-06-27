import re


def calculate(expression: str) -> str:
    """
    Safely evaluates basic mathematical expressions.
    Supports addition, subtraction, multiplication, division, exponentiation, and parentheses.
    """
    # Remove all spaces and normalize exponentiation operator
    expr = expression.replace(" ", "").replace("^", "**")

    # Regex to whitelist only safe mathematical characters: numbers, operations, decimals, parentheses
    safe_pattern = r"^[0-9+\-*/().]*$"

    if not re.match(safe_pattern, expr):
        return (
            "Error: Invalid characters in expression. "
            "Only numbers and basic arithmetic operators (+, -, *, /, **, parenthese) are allowed."
        )

    # Prevent double asterisks that are not for exponentiation (e.g. ***) or other weird combos
    if "***" in expr or "//" in expr:
        return "Error: Unsupported operations (like floor division or invalid operator repetition)."

    try:
        # Run eval in a highly restricted sandbox
        result = eval(expr, {"__builtins__": None}, {})
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"
