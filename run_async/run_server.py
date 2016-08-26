"""
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

# Tornado Import
try:
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    from tornado.web import Application, RequestHandler
    from tornado.websocket import WebSocketHandler
except ImportError:
    WebSocketHandler = RequestHandler = Application = object

# Execution
from multiprocessing import Process as mp_Process
# -- Python2 Compatibility WARNING
# Python 2 requires **futures**
# https://github.com/agronholm/pythonfutures
from concurrent.futures import ProcessPoolExecutor
from threading import Thread

# Shell Namespace restoring
from inspect import ismodule as inspect_ismodule
from importlib import import_module

# Messaging
import json
import pickle

# IPython
from IPython.utils.io import capture_output
from IPython.core.interactiveshell import InteractiveShell

# Handlers and Utils
from .handlers import (WebSocketConnectionHandler, ResultCache,
                       ExecutionHandler)
from .settings import JS_ROLE, PY_ROLE, SERVER_PORT, SERVER_ADDR
from .utils import parse_ws_connection_id


def execute_cell(raw_cell, current_ns):
    """
    Perform the execution of the async cell
    """
    # Create a new InteractiveShell
    shell = InteractiveShell()
    # Disable Debugger
    shell.call_pdb = False
    shell.pdb = False

    # Process and Inject in the Namespace imported modules
    module_names = current_ns.pop('import_modules')
    modules = {}
    if module_names:
        for alias, mname in module_names:
            module = import_module(mname)
            modules[alias] = module
    shell.user_ns.update(current_ns)
    if modules:
        shell.user_ns.update(modules)

    output = ''
    with capture_output() as io:
        _ = shell.run_cell(raw_cell,silent=True,
                           shell_futures=False)

    # Update Namespace
    updated_namespace = dict()
    updated_namespace.setdefault('import_modules', list())
    for k, v in shell.user_ns.items():
        try:
            if inspect_ismodule(v):
                updated_namespace['import_modules'].append((k, v.__name__))
            else:
                _ = pickle.dumps({k:v})
                updated_namespace[k] = v
        except TypeError:
            continue
        except pickle.PicklingError:
            continue
        except AttributeError:
            continue

    # if not output:
    output += io.stdout
    return output, updated_namespace

class AsyncRunHandler(WebSocketHandler):
    """
    Tornado WebSocket Handlers.
    This class is responsible to handle the
    actual communication occuring on the
    web socket between the (JS) client and
    (PY) server.
    """

    def __init__(self, application, request, **kwargs):
        super(AsyncRunHandler, self).__init__(application,
                                              request, **kwargs)
        self._session_id = ''
        self._code_to_run = None
        self._user_ns = None

    # noinspection PyMethodOverriding
    def initialize(self, connection_handler, result_cache, io_loop):
        """Initialize the WebsocketHandler injecting proper handlers
        instances.
        These handlers will be used to store reference to client connections,
        to cache execution results, and to manage
        a system of output queues, respectively.
        """
        self._connection_handler = connection_handler
        self._execution_cache = result_cache
        self._ioloop = io_loop

    def check_origin(self, origin):
        return True

    def open(self, connection_id):
        """
        """
        print('Connection Opened for: ', connection_id)
        self._connection_id = connection_id
        _, session_id = parse_ws_connection_id(connection_id)
        self._session_id = session_id

        # ADD Websocket Connection
        self._connection_handler.add(connection_id, self)

    def process_work_completed(self, future):
        """
        """
        # This output will go to the server stdout
        # to be removed
        print('Future Completed')

        # Get Execution results
        output, namespace = future.result()  # potentially blocking call

        # Post-execution processing
        data = {'session_id': self._session_id,
                'output': output}

        # ADD Cache Result
        # print('Caching results for ', self.cache_id)
        # FIXME: This does not work if the output includes Images
        # TODO: Try using pickle here, instead of json
        jsonified = json.dumps(data)
        self._execution_cache.add(self._session_id, jsonified)

        # Get WebSocket Connection of the client to receive updates in
        # the namespace of the cell
        ws_conn = self._connection_handler.get(self._connection_id)
        if ws_conn:
            # Send to the client the updated namespace
            # Add Execution output to allow for *Output History UPDATE*
            message = {'exec_output': output}
            message.update(namespace)
            bin_message = pickle.dumps(message)
            # Write again on the web socket so to fire JS Client side.
            ws_conn.write_message(bin_message, binary=True)
        else:
            print("No Connection found for ", self._connection_id)

    def run_async_cell_execution(self):
        with ProcessPoolExecutor() as executor:
            future = executor.submit(execute_cell, self._code_to_run, self._user_ns)
            self._ioloop.add_future(future, self.process_work_completed)
            # self.process_work_completed(future)

    def on_message(self, message):
        """
        Handler method activated every time a new
        message is received on the web socket.
        """
        try:
            data = json.loads(message)
        except TypeError:
            # Binary Message
            data = pickle.loads(message)

        connection_id = data.get('connection_id', '')
        role_name, _ = parse_ws_connection_id(connection_id)

        if role_name == JS_ROLE:
            # GET Cache Result
            json_data = self._execution_cache.get(connection_id)
            # GET WebSocketConnection
            ws_conn = self._connection_handler.get(connection_id)
            if ws_conn and json_data:
                ws_conn.write_message(json_data)  # JS Client
            else:
                print('No connection nor data stored for ', role_name)

        elif role_name == PY_ROLE:  # parse the code to run_async_cell_execution
            if 'nb_code_to_run_async' in data:
                self._code_to_run = data['nb_code_to_run_async']
            else:  # namespace
                self._user_ns = data

            if self._code_to_run and self._user_ns:
                # Start the execution of the cell
                print("Starting Execution")
                # t = Thread(target=self.run_async_cell_execution)
                # t.start()
                self.run_async_cell_execution()
        else:
            print('No Action found for Role: ', role_name)

    def on_close(self):
        # REMOVE WebSocketConnection
        print('Closing Connection for ', self._connection_id)
        self._connection_handler.remove(self._connection_id)


class PingRequestHandler(RequestHandler):
    """Dummy Request Handler used to test
    connectivity to webserver"""
    def get(self):
        self.write("Server is Up'n'Running!")


class AsyncRunServer(mp_Process):
    """The main `multiprocessing.Process` class
    controlling the execution of the
    Asynch Server running.

    This class is in charge to handle
    references to the IO Loop (Tornado Loop
    so far) and the Http Server.
    """

    def __init__(self):
        super(AsyncRunServer, self).__init__()
        self.io_loop = None
        self.http_server = None

    def run(self):
        """
        """
        # logging.basicConfig(filename='runserver.log',level=logging.DEBUG)

        IOLoop.clear_current()
        IOLoop.clear_instance()
        self.io_loop = IOLoop.instance()

        ws_connection_handler = WebSocketConnectionHandler()
        results_cache = ResultCache()
        tornado_app = Application(handlers=[
            (r"/ws/(.*)", AsyncRunHandler, {'connection_handler': ws_connection_handler,
                                            'result_cache': results_cache,
                                            'io_loop': self.io_loop,
                                            }),
            (r"/ping", PingRequestHandler)])
        self.http_server = HTTPServer(tornado_app)
        try:
            self.http_server.listen(port=SERVER_PORT,
                                    address=SERVER_ADDR)
            if not self.io_loop._running:
                print('Running Server Loop')
                self.io_loop.start()
            else:
                print("IOLoop already running")
        except OSError:
            print("Server is already running!")
        except KeyboardInterrupt:
            print('Closing Server Loop')
            self.http_server.close_all_connections()
            self.io_loop.stop()


if __name__ == '__main__':

    server = AsyncRunServer()
    try:
        server.start()
        server.join()
    except KeyboardInterrupt:
        pass

