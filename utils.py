import re


def sanitize_filename(name: str) -> str:
    """
    Return a safe filesystem name: collapse spaces, remove unsafe characters.
    Keeps Unicode letters/digits, dash, underscore, dot.
    """
    if not isinstance(name, str):
        name = str(name)
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Remove path separators and control chars
    name = name.replace("/", "_").replace("\\", "_")
    # Keep only allowed chars
    name = re.sub(r"[^\w\-. ]", "_", name)
    # Collapse underscores
    name = re.sub(r"_+", "_", name)
    return name


def print_info(message: str) -> None:
    print(f"[INFO] {message}")
