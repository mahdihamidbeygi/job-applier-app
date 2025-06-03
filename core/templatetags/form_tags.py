import json
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe


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


@register.filter
def model_name(obj):
    return obj.model._meta.model_name


@register.filter
def parse_technologies(value):
    """Parse technologies string and return dictionary."""
    if not value:
        return {
            "languages": {},
            "frameworks_libraries": [],
            "databases": [],
            "tools_technologies": [],
        }

    try:
        fixed_json = value.replace("'", '"')
        return json.loads(fixed_json)
    except json.JSONDecodeError:
        return {
            "languages": {},
            "frameworks_libraries": [],
            "databases": [],
            "tools_technologies": [],
        }


@register.filter
def pretty_json(value, indent=4):
    """Convert dictionary to pretty formatted JSON string."""
    try:
        return mark_safe(json.dumps(value, indent=indent, ensure_ascii=False))
    except (TypeError, ValueError):
        return "{}"


@register.filter
def has_tech_content(tech_dict):
    """Check if technologies dict has any content."""
    if not isinstance(tech_dict, dict):
        return False

    return (
        bool(tech_dict.get("languages"))
        or bool(tech_dict.get("frameworks_libraries"))
        or bool(tech_dict.get("databases"))
        or bool(tech_dict.get("tools_technologies"))
    )
