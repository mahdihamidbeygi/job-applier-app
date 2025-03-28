from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css_class):
    """Add a CSS class to a form field."""
    return field.as_widget(attrs={'class': css_class}) 