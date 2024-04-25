import html


def escape_html(field_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            processed_args = list(args)
            if field_name in kwargs:
                kwargs[field_name] = html.escape(kwargs[field_name])
            return func(*processed_args, **kwargs)
        return wrapper
    return decorator
