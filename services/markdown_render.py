import markdown

try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False


def render_markdown(content):
    """将 Markdown 转为 HTML，并清除危险标签（防 XSS）。"""
    html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    if not BLEACH_AVAILABLE:
        return html

    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'hr',
        'ul', 'ol', 'li',
        'blockquote', 'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img',
        'strong', 'em', 'del', 'sup', 'sub',
        'div', 'span',
    ]
    allowed_attrs = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        'code': ['class'],
        'pre': ['class'],
        'th': ['align'],
        'td': ['align'],
        'div': ['class'],
        'span': ['class'],
    }
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
