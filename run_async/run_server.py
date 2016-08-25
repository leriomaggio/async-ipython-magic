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
from multiprocessing import SimpleQueue
from multiprocessing import Process as mp_Process
from concurrent.futures import ProcessPoolExecutor
from threading import Thread
from multiprocessing import Process
import logging

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
from run_async.handlers import (WebSocketConnectionHandler, ResultCache, ExecutionHandler)
from run_async.settings import JS_ROLE, PY_ROLE
from run_async.settings import parse_ws_connection_id, format_ws_connection_id


class CustomInteractiveShell(InteractiveShell):
    """"""

    def __init__(self, *args, **kwargs):
        super(CustomInteractiveShell, self).__init__(*args, **kwargs)

    def _showtraceback(self, etype, evalue, stb):
        """Actually show a traceback.

        Subclasses may override this method to put the traceback on a different
        place, like a side channel.
        """
        # self.InteractiveTB.plain()
        # self.InteractiveTB.call_pdb = False
        # self.InteractiveTB.set_colors('NoColor')
        # text = '\n'.join(stb)

        # print(highlight(text, self.lexer, self.formatter))
        print(self.InteractiveTB.stb2text(stb))


def execute_cell(raw_cell, current_ns):
    """
    """

    shell = CustomInteractiveShell()
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
        exec_result = shell.run_cell(raw_cell,
                                     silent=True,
                                     shell_futures=False)

    # Update Namespace
    updated_namespace = dict()
    updated_namespace.setdefault('import_modules', list())
    for k, v in shell.user_ns.items():
        try:
            # _ = json.dumps({k:v})
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
    """

    def __init__(self, application, request, **kwargs):
        super(AsyncRunHandler, self).__init__(application,
                                              request, **kwargs)
        self._session_id = ''
        self._code_to_run = None
        self._user_ns = None
        self.pool_executor = ProcessPoolExecutor()

    # noinspection PyMethodOverriding
    def initialize(self, connection_handler, result_cache, job_queues, io_loop):
        """Initialize the WebsocketHandler injecting proper handlers
        instanties.
        These handlers will be used to store reference to client connections,
        to cache execution results, and to manage a system of output queues.
        In more details:

        TODO:
        """
        self._connection_handler = connection_handler
        self._execution_cache = result_cache
        self._job_queues = job_queues
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

        # ADD Job Queue
        if not session_id in self._job_queues:
            self._job_queues.add(session_id, SimpleQueue())

    # def do_work_in_queue(self):
    #     """
    #     """
    #
    #     # with ProcessPoolExecutor(max_workers=1) as executor:
    #     #     # future = executor.submit(run_cell_in_kernel,
    #     #     future = executor.submit(execute_cell,
    #     #                              self._code_to_run,
    #     #                              self._user_ns,
    #     #                              )
    #     #     output, namespace = future.result()
    #     #     # self._process_exec_queue.put((output, namespace))
    #     #     # output, namespace = self._process_exec_queue.get()

    # def store_output_from_queue(self):
    #     """
    #     """
    #     output, namespace = self._process_exec_queue.get()
    #     data = {'session_id': self._session_id,
    #             'output': output}
    #     jsonified = json.dumps(data)
    #
    #     # ADD Cache Result
    #     # print('Caching results for ', self.cache_id)
    #     self._execution_cache.add(self.cache_id, jsonified)
    #
    #     # GET Job Queue
    #     # NOTE: One Job Queue per Session ID (to avoid conflicts)
    #     job_queue = self._job_queues.get(self._session_id)
    #     if job_queue is not None:
    #         job_queue.put(jsonified)
    #     else:
    #         print("NO JOB QUEUE for current Session: ", self._session_id)
    #
    #     # Send to client the updated namespace
    #     ws_conn = self._connection_handler.get(self._connection_id)
    #     if ws_conn:
    #         # Add Execution output to allow for *Output History UPDATE*
    #         message = {'exec_output': output}
    #         message.update(namespace)
    #         bin_message = pickle.dumps(message)
    #         ws_conn.write_message(bin_message, binary=True)
    #     else:
    #         print("No Connection found for ", self._connection_id)

    def process_work_completed(self, future):
        """

        Parameters
        ----------
        future

        Returns
        -------

        """

        print('Future Completed')

        # Get Execution results
        output, namespace = future.result()

        # Post-execution processing
        data = {'session_id': self._session_id,
                'output': output}

        # FIXME: This does not work if the output includes Images
        # TODO: Try using pickle here, instead of json
        jsonified = json.dumps(data)

        # ADD Cache Result
        # print('Caching results for ', self.cache_id)
        self._execution_cache.add(self._session_id, jsonified)

        # GET Job Queue
        # NOTE: One Job Queue per Session ID (to avoid conflicts)
        job_queue = self._job_queues.get(self._session_id)
        if job_queue:
            job_queue.put(jsonified)
        else:
            print("NO JOB QUEUE for current Session: ", self._session_id)

        # Get WebSocket Connection of the client to receive updates in
        # the namespace of the cell
        ws_conn = self._connection_handler.get(self._connection_id)
        if ws_conn:
            # Send to the client the updated namespace
            # Add Execution output to allow for *Output History UPDATE*
            message = {'exec_output': output}
            message.update(namespace)
            bin_message = pickle.dumps(message)
            ws_conn.write_message(bin_message, binary=True)
        else:
            print("No Connection found for ", self._connection_id)

    def run(self):
        """
        """
        # Worker
        # worker = Thread(target=self.do_work_in_queue)
        # worker.daemon = True
        # worker.start()

        # # Publisher
        # publisher = Thread(target=self.store_output_from_queue)
        # publisher.daemon = True
        # publisher.start()

        with ProcessPoolExecutor() as executor:
            future = executor.submit(execute_cell, self._code_to_run, self._user_ns)
            # self._ioloop.add_future(future, self.process_work_completed)
            self.process_work_completed(future)


        # future = self.pool_executor.submit(execute_cell, self._code_to_run, self._user_ns)
        # self._ioloop.add_future(future, self.process_work_completed)


        #     worker = mp_Process(target=execute_cell, args=(self._code_to_run, self._user_ns,
        #                                                    self._session_id, job_queue,
        #                                                    self._execution_cache, ws_conn,))
        #     worker.start()

    def on_message(self, message):
        """
        """
        try:
            data = json.loads(message)
        except TypeError:
            # Binary Message
            data = pickle.loads(message)

        # print('Received Data: ', data)
        connection_id = data.get('connection_id', '')
        role_name, _ = parse_ws_connection_id(connection_id)

        if role_name == JS_ROLE:
            # GET Cache Result
            json_data = self._execution_cache.get(connection_id)

            if json_data is None:
                # GET Job Queue
                job_queue = self._job_queues.get(self._session_id)
                json_data = job_queue.get()  # WAIT for task to complete
            else:
                print('Getting data from cache!!')

            # print('json_data: ', json_data)

            # GET WebSocketConnection
            ws_conn = self._connection_handler.get(connection_id)
            if ws_conn:
                ws_conn.write_message(json_data)  # JS Client
                # REMOVE Job Queue
                self._job_queues.remove(self._session_id)
            else:
                print('No connection stored for ', role_name)

        elif role_name == PY_ROLE:  # parse the code to run
            if 'nb_code_to_run_async' in data:
                self._code_to_run = data['nb_code_to_run_async']
            else:  # namespace
                self._user_ns = data

            if self._code_to_run and self._user_ns:
                # Start the execution of the cell
                print("Starting Execution")
                t = Thread(target=self.run)
                t.start()
                # self.run()
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


class AsyncRunServer(Process):

    def __init__(self):
        super(AsyncRunServer, self).__init__()
        self.io_loop = None
        self.http_server = None

    def run(self):
        """

        Returns
        -------

        """
        # logging.basicConfig(filename='runserver.log',level=logging.DEBUG)

        IOLoop.clear_current()
        IOLoop.clear_instance()
        self.io_loop = IOLoop.instance()

        ws_connection_handler = WebSocketConnectionHandler()
        execution_handler = ExecutionHandler()
        results_cache = ResultCache()
        tornado_app = Application(handlers=[
            (r"/ws/(.*)", AsyncRunHandler, {'connection_handler': ws_connection_handler,
                                            'result_cache': results_cache,
                                            'job_queues': execution_handler,
                                            'io_loop': self.io_loop,
                                            }),
            (r"/ping", PingRequestHandler)])
        self.http_server = HTTPServer(tornado_app)
        try:
            self.http_server.listen(5678)
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

