try:
    from test.common import *
except ImportError:
    from .common import *


class TestWraptBox:

    @pytest.mark.parametrize('wrapped', python_example_objects)
    def test_box_object_generic(self, wrapped):
        b = WraptBox(wrapped)
        assert b == wrapped
        assert not (b is wrapped)
        assert isinstance(b, WraptBox)
        assert isinstance(b, type(wrapped))
        b.box_key = 'secret_word'
        assert b.box_key == 'secret_word'
        assert 'box_key' in b.__dict__
        assert isinstance(b.__dict__, Box)
        assert b.__dict__ != getattr(b.__wrapped__, '__dict__', None)
        with pytest.raises(AttributeError):
            b.foo
        if hasattr(b.__wrapped__, 'b'):
            b.b = 1
            assert b.__wrapped__.b == 1

    @pytest.mark.parametrize('wrapped', python_example_objects)
    def test_box_object_deletion(self, wrapped):
        b = WraptBox(wrapped)
        with pytest.raises(TypeError):
            b.__dict__ = 0
        del b.__dict__
        assert b.__dict__ == getattr(b.__wrapped__, '__dict__', {})
        with pytest.raises(AttributeError):
            del b.foo
        if hasattr(b.__wrapped__, 'a'):
            del b.a
        if not hasattr(b.__wrapped__, 'b'):
            with pytest.raises(AttributeError):
                del b.b

    def test_box_object_attributes(self):
        b = WraptBox(test_dict, **movie_data)
        assert b == test_dict
        assert not (b is test_dict)
        assert b.__dict__ == movie_data
        assert isinstance(b.__dict__, Box)
        assert b.__dict__ != getattr(b.__wrapped__, '__dict__', None)
        for k, v in movie_data.items():
            assert getattr(b, k) == v
            tagged = k + '_b'
            setattr(b, tagged, [v])
            assert getattr(b, tagged) == [v]
            setattr(b, k, getattr(b, tagged))
            assert getattr(b, k) == [v]
        for k, v in test_dict.items():
            assert k in b
            assert b[k] == v

    def test_box_object_call(self):
        def f(*args, **kwargs):
            return args, kwargs

        b = WraptBox(f)
        assert b(list(test_dict),
                 **movie_data) == f(list(test_dict), **movie_data)

    def test_box_object_double_args(self):
        with pytest.raises(TypeError):
            WraptBox(function_example,
                      zip([1, 2, 3], [4, 5, 6]),
                      **movie_data)
