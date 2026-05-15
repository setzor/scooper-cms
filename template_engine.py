"""
Scooper CMS Template Engine

A simple template engine wrapper that adds auto-escaping to the regex-based approach.
This provides XSS protection while maintaining backward compatibility.
"""


class SafeString(str):
    """
    A string subclass that indicates the content is safe HTML.
    Values of this type will NOT be escaped by the template engine.
    """
    pass


def escape_html(value):
    """Escape HTML special characters in a string."""
    if value is None:
        return ''
    value = str(value)
    return (value.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
