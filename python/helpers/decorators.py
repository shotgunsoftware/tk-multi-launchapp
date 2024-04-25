import html


def escape_html(field_name):
    """
    Decorator that escapes HTML special characters from a
    specific argument before calling the decorated function.

    :param field_name: Str with message.

    :returns: decorated function.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            processed_args = list(args)
            if field_name in kwargs:
                kwargs[field_name] = html.escape(kwargs[field_name])
            return func(*processed_args, **kwargs)

        return wrapper

    return decorator
