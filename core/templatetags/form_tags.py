from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter(name="addclass")
def addclass(field, css):
    """Add a CSS class to a form field."""
    return field.as_widget(attrs={"class": css})


@register.filter(name="split")
def split_string(value, arg):
    """
    Splits a string by a delimiter and returns a list of stripped, non-empty strings.
    Usage: {{ some_string|split:"," }}
    """
    if isinstance(value, str):
        # Split by the delimiter, then strip whitespace from each item,
        # and filter out any empty strings that might result from multiple delimiters
        # or delimiters at the start/end of the string after stripping.
        return [item.strip() for item in value.split(arg) if item.strip()]
    return []  # Return empty list if not a string or if value is None


@register.filter
@stringfilter
def trim(value):
    """Remove leading and trailing whitespace."""
    return value.strip()


@register.filter
@stringfilter
def split(value, delimiter=","):
    """Split a string by delimiter and return a list."""
    return [item.strip() for item in value.split(delimiter) if item.strip()]
