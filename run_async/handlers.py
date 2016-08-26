"""Collection of handler classes (dictionary-like objects)
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

from collections import defaultdict

# from queue import Queue
from multiprocessing import SimpleQueue
try:
    from tornado.websocket import WebSocketHandler
except ImportError:
    pass

from .settings import JS_ROLE
from .utils import format_ws_connection_id


class Handler():
    """Container object for data management. The handler contains
    a dictionary whose default type is determined according to the
    class provided in the constructor"""

    def __init__(self, factory=None):
        if factory is None:
            factory = str  # Default type of data
        self._data = defaultdict(factory)

    def add(self, key, value):
        self._data[key] = value

    def remove(self, key):
        _ = self._data.pop(key, None)

    def get(self, key):
        return self._data.get(key, None)

    def __contains__(self, key):
        return key in self._data

    @property
    def entries(self):
        return list(self._data.keys())


class WebSocketConnectionHandler(Handler):
    """Handler for `tornado.websocket.WebSocketHandler` connections.

    Entries' keys are the _connection_id[s], namely
    <JS_ROLE | PY_ROLE>---<session_id>
    """

    def __init__(self):
        super(WebSocketConnectionHandler, self).__init__(
            factory=WebSocketHandler)


class ResultCache(Handler):
    """Handler for caching execution results,
    namely JSON (string) output.

    Entries' keys are the (clients) _connection_id[s], namely
    <JS_ROLE>---<session_id>
    """

    def __init__(self):
        super(ResultCache, self).__init__(factory=str)

    def add(self, session_id, value):
        cache_id = format_ws_connection_id(JS_ROLE, session_id)
        super(ResultCache, self).add(cache_id, value)


class ExecutionHandler(Handler):
    """Handler to store the execution queues in order to
    make clients to wait on correct thread queues.
    Entries' keys are the session_id[s], namely "one queue per session_id".
    """

    def __init__(self):
        super(ExecutionHandler, self).__init__(factory=SimpleQueue)

