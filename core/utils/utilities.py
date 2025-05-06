import re
import unicodedata
import urllib.parse


def clean_string(input_string: str, **kwargs) -> str:
    """
    Thoroughly cleans a string by removing or replacing characters unsuitable for filenames

    Args:
        input_string (str): The string to clean
        options (dict, optional): Configuration options
            - decode_url_chars (bool): Whether to decode URL-encoded characters (default: True)
            - replace_special_chars (bool): Whether to replace special chars with safe alternatives (default: True)
            - normalize_whitespace (bool): Whether to normalize whitespace (default: True)
            - normalize_unicode (bool): Whether to normalize Unicode characters (default: True)
            - ascii_only (bool): Whether to convert to ASCII only (default: False)
            - lowercase (bool): Whether to convert to lowercase (default: False)
            - max_length (int): Maximum length of filename (default: 255)
            - replacement (str): Character to use for replacement (default: '_')
            - allow_chars (str): Additional characters to allow (default: '')

    Returns:
        str: The cleaned string suitable for filenames
    """
    if not isinstance(input_string, str) or not input_string:
        return ""

    # Default options
    if not kwargs:
        kwargs = {}

    config = {
        "decode_url_chars": True,
        "replace_special_chars": True,
        "normalize_whitespace": True,
        "normalize_unicode": True,
        "ascii_only": False,
        "lowercase": False,
        "max_length": 255,
        "replacement": "_",
        "allow_chars": "",
    }

    # Update defaults with provided options
    config.update(kwargs)

    result = input_string

    # Step 1: Decode URL-encoded characters if enabled
    if config["decode_url_chars"]:
        try:
            result = urllib.parse.unquote(result)
        except Exception:
            # If decoding fails, continue with original string
            print("URL decoding failed, proceeding with original string")

    # Step 2: Normalize Unicode if enabled
    if config["normalize_unicode"]:
        # Convert to normal form (NFC)
        result = unicodedata.normalize("NFC", result)

        # Handle accented characters based on ascii_only setting
        if config["ascii_only"]:
            # Convert to NFKD form and strip accents
            result = "".join(
                [c for c in unicodedata.normalize("NFKD", result) if not unicodedata.combining(c)]
            )

    # Step 3: Replace special characters if enabled
    if config["replace_special_chars"]:
        # Define safe characters (alphanumeric, underscore, hyphen, period) - no spaces
        safe_chars = r"a-zA-Z0-9._\-()[\]" + re.escape(config["allow_chars"])

        # Replace control characters and non-printable chars
        result = re.sub(r"[\x00-\x1F\x7F-\x9F]", config["replacement"], result)

        # Replace characters problematic in filenames across all operating systems
        result = re.sub(r'[<>:"/\\|?*]', config["replacement"], result)

        # Replace spaces with underscores
        result = re.sub(r"\s", "_", result)

        # Replace all other non-safe characters
        result = re.sub(r"[^" + safe_chars + "]", config["replacement"], result)

        # Replace multiple consecutive replacement characters with a single one
        result = re.sub(re.escape(config["replacement"]) + "{2,}", config["replacement"], result)

    # Step 4: Normalize whitespace if enabled
    if config["normalize_whitespace"]:
        # Replace multiple spaces/tabs with underscores
        result = re.sub(r"\s+", "_", result)
        # Trim leading and trailing whitespace
        result = result.strip()
        # Remove underscores at the beginning and end
        result = result.strip("_")

    # Step 5: Apply lowercase if enabled
    if config["lowercase"]:
        result = result.lower()

    # Step 6: Trim to max length if specified
    if config["max_length"] > 0 and len(result) > config["max_length"]:
        # Try to cut at a word boundary if possible
        cutoff = result[: config["max_length"]].rfind(" ")
        if cutoff > config["max_length"] * 0.8:  # Only use word boundary if it's not too short
            result = result[:cutoff]
        else:
            result = result[: config["max_length"]]

    # Final cleanup: remove leading/trailing replacement characters
    result = result.strip(config["replacement"])

    # Ensure we don't have an empty string after all cleaning
    if not result:
        result = "unnamed"

    return result
