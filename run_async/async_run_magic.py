"""IPython Magic to run cells asynchronously
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

from __future__ import print_function  # Python 2 compatibility

import json
from pickle import dumps as pickle_dumps
from pickle import loads as pickle_loads
from pickle import PicklingError
from urllib.request import URLError, urlopen
from uuid import uuid4

try:
    from tornado.websocket import websocket_connect
except ImportError:
    pass

from os import kill as os_kill
from signal import SIGINT as signal_SIGINT

from importlib import import_module
from inspect import ismodule as inspect_ismodule

from .settings import JS_ROLE, PY_ROLE, EXEC_OUTPUT
from .settings import DEFAULT_BLACKLIST
from .settings import JS_WEBSOCKET_CODE, LIGHT_HTML_OUTPUT_CELL
from .utils import (strip_ansi_color,
                    connection_string, format_ws_connection_id)

from IPython.display import HTML
from IPython.core.magic import (Magics, magics_class, line_magic,
                                line_cell_magic)

from .run_server import AsyncRunServer
from threading import Thread


# -------------------------
# IPython (Line/Cell) Magic
# -------------------------

class WSConnector:

    def __init__(self, connection_id, code_to_run, shell):
        """
        Parameters
        ----------
        connection_id: str
            The unique ID of the connection to establish on the websocket.
        code_to_run: str
            The content of the async cell to run
        shell: `IPython.core.interactiveshell.InteractiveShell`
            Instance of the current IPython shell running in the
            notebook.
        """
        self.ws_conn = None
        self.connection_id = connection_id
        self.cell_source = code_to_run
        self.shell = shell
        self.exec_count = shell.execution_count

    def connect(self):
        """
        Creates the connection to the Tornado Web Socket
        """
        # 'ws://localhost:5678/ws/<CONN_ID>'
        conn_string = connection_string(web_socket=True,
                                        extra='ws/{}'.format(self.connection_id))
        websocket_connect(conn_string, callback=self.on_connected,
                          on_message_callback=self.on_message)

    def on_connected(self, f):
        """Callback fired /on_connection/ established.

        Once the connection to the websocket has been established,
        all the currenct namespace is pickled and written to the
        corresponding web_socket connection.
        """
        try:
            ws_conn = f.result()
            self.ws_conn = ws_conn
            data = {'connection_id': self.connection_id,
                    'nb_code_to_run_async': self.cell_source,}
            msg = json.dumps(data)
            ws_conn.write_message(message=msg)
            white_ns = self._pack_namespace()
            ws_conn.write_message(message=pickle_dumps(white_ns), binary=True)
        except PicklingError as e:
            print(str(e))

    def _pack_namespace(self):
        """Collect all the /pickable/ objects from the namespace
        so to pass them to the async execution environment."""
        white_ns = dict()
        white_ns.setdefault('import_modules', list())
        for k, v in self.shell.user_ns.items():
            if not k in DEFAULT_BLACKLIST:
                try:
                    if inspect_ismodule(v):
                        white_ns['import_modules'].append((k, v.__name__))
                    else:
                        _ = pickle_dumps({k: v})
                        white_ns[k] = v
                except PicklingError:
                    continue
                except Exception:
                    continue
        white_ns['connection_id'] = self.connection_id
        return white_ns

    def on_message(self, message):
        """Callback fired /on_message/.

        This hand of the web socket (Python side) will be
        fired whenever the asynch execution is
        completed.
        """
        if message is not None:
            msg = dict(pickle_loads(message))
            exec_output = None
            if EXEC_OUTPUT in msg:
                exec_output = msg.pop(EXEC_OUTPUT)

            # Look for modules to Import
            self._check_modules_import(msg)
            # Update Output History
            self._update_output_history(exec_output)
            self.ws_conn.close()

    def _check_modules_import(self, msg):
        """
        Check if any module has been imported in the
        async cell. If that is the case, import
        modules again in the current shell to make
        them available in the current namespace.

        Parameters
        ----------
        msg : dict
            Message dictionary returned by Async execution
        """
        module_names = msg.pop('import_modules')
        modules = dict()
        if module_names:
            for alias, mname in module_names:
                module = import_module(mname)
                modules[alias] = module
        self.shell.user_ns.update(msg)
        if modules:
            self.shell.user_ns.update(modules)

    def _update_output_history(self, exec_output):
        """Update the Output history in the current
        IPython Shell.

        Parameters
        ----------
        exec_output : str
            Output of the Async execution.
        """
        out_cell_key_in_namespace = '_{}'.format(str(self.exec_count))
        if exec_output:  # Update Output history
            exec_output = strip_ansi_color(exec_output)
            self.shell.user_ns['_oh'][self.exec_count] = exec_output
            self.shell.user_ns[out_cell_key_in_namespace] = exec_output
        else:
            # This is necessary to avoid that `_oh` contains the
            # the `LIGHT_HTML_CODE` as output
            # (which is not even rendered in the notebook)
            _ = self.shell.user_ns['_oh'].pop(self.exec_count, None)
            _ = self.shell.user_ns.pop(out_cell_key_in_namespace, None)


@magics_class
class AsyncRunMagic(Magics):

    def __init__(self, shell, **kwargs):
        super(AsyncRunMagic, self).__init__(shell, **kwargs)
        self._server_process = None

    def _spawn_server_process(self):
        self._server_process.start()
        print('Process Started with PID ', self._server_process.pid)
        self._server_process.join()

    @line_magic
    def async_start_server(self, line):
        if (not self._server_process is None) and (self._server_process.is_alive()):
            print("Cannot Start process twice")
        else:
            self._server_process = AsyncRunServer()
            th_runner = Thread(target=self._spawn_server_process)
            th_runner.start()

    @line_magic
    def async_stop_server(self, line):
        if self._server_process is None or not self._server_process.is_alive():
            print('No Server is Running')
        else:
            print("Killing SIGINT to PID ", self._server_process.pid)
            try:
                os_kill(self._server_process.pid, signal_SIGINT)
            except ProcessLookupError:
                pass
            finally:
                self._server_process = None

    @line_cell_magic
    def async_run(self, line, cell=None):
        """Run code into cell asynchronously

            Usage:\\
              %async_run <source> (cell content)
        """

        if cell is None:
            code_to_run = line
        else:
            code_to_run = cell

        session_id = str(uuid4())
        connection_id = format_ws_connection_id(PY_ROLE, session_id)

        try:
            _ = urlopen(connection_string(web_socket=False, extra='ping'))
        except URLError:
            print("Connection to server refused!", end='  ')
            print("Use %async_run_server first!")
        else:
            connector = WSConnector(connection_id, code_to_run, self.shell)
            connector.connect()

            html_output = LIGHT_HTML_OUTPUT_CELL.format(session_id=session_id)
            js_code = JS_WEBSOCKET_CODE.replace('__sessionid__', session_id)
            js_code = js_code.replace('__connection_id__', format_ws_connection_id(JS_ROLE,
                                                                                   session_id))
            html_output += js_code

            return HTML(html_output)

