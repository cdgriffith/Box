import wrapt

from box import Box


class WraptBox(wrapt.ObjectProxy):
    """
    Wrapper for any Python object with a Box as __dict__.

    Simple Usage:

    import requests
    url = 'https://raw.githubusercontent.com/cdgriffith/Box/master/box.py'
    session = WraptBox(requests.Session())
    session.source_code = session.get(url).text

    :param wrapped: Wrapped Object.
    :param box_class: Custom internal Box class
    :param args: Arguments to fill Box
    :param kwargs: Keyword arguments to fill Box
    """

    def __init__(self, wrapped=None, *args, **kwargs):
        """Initialize Box Object with __dict__ as a Box."""
        super(WraptBox, self).__init__(wrapped)
        box_class = kwargs.pop('box_class', Box)
        try:
            base_dict = super(WraptBox, self).__getattr__('__dict__')
            if args:
                raise TypeError('Cannot pass dictionary arguments when '
                                'internal object has __dict__ attributes. '
                                'Pass arguments by keyword instead.')
            box = box_class(base_dict, **kwargs)
        except AttributeError:
            box = box_class(*args, **kwargs)
        super(WraptBox, self).__setattr__('__dict__', box)

    def __call__(self, *args, **kwargs):
        """Call Method for Callable Objects."""
        return self.__wrapped__(*args, **kwargs)

    def __getattr__(self, name):
        """Get Attribute from Wrapped Object or from Box."""
        try:
            return super(WraptBox, self).__getattr__(name)
        except AttributeError as error:
            try:
                return self.__dict__[name]
            except KeyError:
                raise error

    def __setattr__(self, name, value):
        """Set Attribute in Wrapped Object or Box."""
        if name == '__dict__':
            raise TypeError('cannot set __dict__')
        elif hasattr(self.__wrapped__, name):
            setattr(self.__wrapped__, name, value)
        else:
            self.__dict__[name] = value

    def __delattr__(self, name):
        """Delete Attribute in Wrapped Object or Box."""
        if name == '__dict__':
            super(WraptBox, self).__setattr__(
                '__dict__',
                getattr(self.__wrapped__, '__dict__', {})
            )
        else:
            try:
                delattr(self.__wrapped__, name)
            except AttributeError as error:
                try:
                    del self.__dict__[name]
                except KeyError:
                    raise error

