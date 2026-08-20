# utils/helpers.py
def validate_file_extension(filename: str, allowed: set) -> bool:
    """Validate file extension"""
    ext = "." + filename.lower().split('.')[-1]
    return ext in allowed