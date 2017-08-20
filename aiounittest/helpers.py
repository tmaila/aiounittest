import asyncio
import functools


def futurized(o):
    ''' Makes the given object to be awaitable.

    :param any o: Object to wrap
    :return: awaitable that resolves to provided object
    :rtype: asyncio.Future

    Anything passed to :code:`futurized` is wrapped with :code:`asyncio.Future`.
    This makes it awaitable (can be run with :code:`await` or `yield from`) as
    a result of await it returns the original object.

    If provided object is a Exception (or its sublcass) then resolvin `Future` will raise it.

    .. code-block:: python

        fut = aiounittest.futurized('SOME TEXT')
        ret = await fut
        print(ret)  # prints SOME TEXT

        fut = aiounittest.futurized(Exception('Dummy error'))
        ret = await fut  # will raise the exception "dummy error"


    The main goal is to use is with :code:`unittest.mock.Mock` (or :code:`MagicMock`) to
    be able to mock awaitable functions (coroutines).


    Consider the below code

    .. code-block:: python

            from asyncio import sleep

            async def add(x, y):
                await sleep(666)
                return x + y

    You rather don't want to wait 666 seconds, got to mock that.

    .. code-block:: python

            from aiounittest import futurized, AsyncTestCase
            from unittest.mock import Mock, patch

            import dummy_math

            class MyAddTest(AsyncTestCase):

                async def test_add(self):
                    mock_sleep = Mock(return_value=futurized('whatever'))
                    patch('dummy_math.sleep', mock_sleep).start()
                    ret = await dummy_math.add(5, 6)
                    self.assertEqual(ret, 11)
                    mock_sleep.assert_called_once_with(666)

                async def test_fail(self):
                    mock_sleep = Mock(return_value=futurized(Exception('whatever')))
                    patch('dummy_math.sleep', mock_sleep).start()
                    with self.assertRaises(Exception) as e:
                        await dummy_math.add(5, 6)
                    mock_sleep.assert_called_once_with(666)

    '''
    f = asyncio.Future()
    if isinstance(o, Exception):
        f.set_exception(o)
    else:
        f.set_result(o)
    return f


def run_sync(func=None, loop=None):
    ''' Run synchonously the given function (coroutine)

    :param callable func: function to run (mostly coroutine)
    :param ioloop loop: event loop to use to run `func`
    :type loop: event loop of None

    By default the brand new event loop will be created (old closed). After completion, the loop will be closed and then recreated, set as default,
    leaving asyncio clean.

    **Note**: :code:`aiounittest.async_test` is an alias of :code:`aiounittest.helpers.run_sync`

    This function enables you to use it like, `pytest.mark.asyncio` (implemetation differs),
    but could be used with :code:`unittest.TestCase` class

    .. code-block:: python

            import asyncio
            import unittest
            from aiounittest import async_test

            async def add(x, y):
                await asyncio.sleep(0.1)
                return x + y

            class MyAsyncTestDecorator(unittest.TestCase):

                @async_test
                async def test_async_add(self):
                    ret = await add(5, 6)
                    self.assertEqual(ret, 11)


    .. note::

        If the loop is provided, it  won't be closed. It's up to you.

    This function is also used internally by :code:`aiounittest.AsyncTestCase` to run coroutines.

    '''
    def get_brand_new_default_event_loop():
        old_loop = asyncio.get_event_loop()
        if not old_loop.is_closed():
            old_loop.close()
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal loop
            use_default_event_loop = loop is None
            if use_default_event_loop:
                loop = get_brand_new_default_event_loop()
            try:
                ret = f(*args, **kwargs)
                try:
                    future = asyncio.ensure_future(ret, loop=loop)
                except TypeError:
                    # Using `try/except` rather than iscoroutine due to support of 3.4
                    pass
                else:
                    return loop.run_until_complete(future)
            finally:
                if use_default_event_loop:
                    # clean up
                    loop.close()
                    del loop
                    # again set a new (unstopped) event loop
                    get_brand_new_default_event_loop()

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


async_test = run_sync
