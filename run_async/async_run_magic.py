"""IPython Magic to run cells asynchronously
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

from __future__ import print_function  # Python 2 compatibility
import json
from pickle import dumps as pickle_dumps
from pickle import loads as pickle_loads
from pickle import PickleError
from uuid import uuid4
from urllib.request import URLError, urlopen

try:
    from tornado.websocket import websocket_connect
except ImportError:
    pass

from os import kill as os_kill
from signal import SIGINT as signal_SIGINT

from importlib import import_module
from inspect import ismodule as inspect_ismodule

from .settings import JS_ROLE, PY_ROLE
from .settings import format_ws_connection_id
from .settings import connection_string

from IPython.display import HTML
from IPython.core.magic import (Magics, magics_class, line_magic,
                                line_cell_magic)

from run_async.run_server import AsyncRunServer
from threading import Thread

from .utils import strip_ansi_color


# -------
# Globals
# -------

LIGHT_HTML_OUTPUT_CELL = '''
<pre class={session_id}-waiting></pre>
<pre class="{session_id}-output" style="display: none"></pre>
'''

CSS_CODE = '''

<style type="text/css">
    .hll { background-color: #ffffcc }
    .c { color: #408080; font-style: italic } /* Comment */
    .err { border: 1px solid #FF0000 } /* Error */
    .k { color: #008000; font-weight: bold } /* Keyword */
    .o { color: #666666 } /* Operator */
    .cm { color: #408080; font-style: italic } /* Comment.Multiline */
    .cp { color: #BC7A00 } /* Comment.Preproc */
    .c1 { color: #408080; font-style: italic } /* Comment.Single */
    .cs { color: #408080; font-style: italic } /* Comment.Special */
    .gd { color: #A00000 } /* Generic.Deleted */
    .ge { font-style: italic } /* Generic.Emph */
    .gr { color: #FF0000 } /* Generic.Error */
    .gh { color: #000080; font-weight: bold } /* Generic.Heading */
    .gi { color: #00A000 } /* Generic.Inserted */
    .go { color: #888888 } /* Generic.Output */
    .gp { color: #000080; font-weight: bold } /* Generic.Prompt */
    .gs { font-weight: bold } /* Generic.Strong */
    .gu { color: #800080; font-weight: bold } /* Generic.Subheading */
    .gt { color: #0044DD } /* Generic.Traceback */
    .kc { color: #008000; font-weight: bold } /* Keyword.Constant */
    .kd { color: #008000; font-weight: bold } /* Keyword.Declaration */
    .kn { color: #008000; font-weight: bold } /* Keyword.Namespace */
    .kp { color: #008000 } /* Keyword.Pseudo */
    .kr { color: #008000; font-weight: bold } /* Keyword.Reserved */
    .kt { color: #B00040 } /* Keyword.Type */
    .m { color: #666666 } /* Literal.Number */
    .s { color: #BA2121 } /* Literal.String */
    .na { color: #7D9029 } /* Name.Attribute */
    .nb { color: #008000 } /* Name.Builtin */
    .nc { color: #0000FF; font-weight: bold } /* Name.Class */
    .no { color: #880000 } /* Name.Constant */
    .nd { color: #AA22FF } /* Name.Decorator */
    .ni { color: #999999; font-weight: bold } /* Name.Entity */
    .ne { color: #D2413A; font-weight: bold } /* Name.Exception */
    .nf { color: #0000FF } /* Name.Function */
    .nl { color: #A0A000 } /* Name.Label */
    .nn { color: #0000FF; font-weight: bold } /* Name.Namespace */
    .nt { color: #008000; font-weight: bold } /* Name.Tag */
    .nv { color: #19177C } /* Name.Variable */
    .ow { color: #AA22FF; font-weight: bold } /* Operator.Word */
    .w { color: #bbbbbb } /* Text.Whitespace */
    .mb { color: #666666 } /* Literal.Number.Bin */
    .mf { color: #666666 } /* Literal.Number.Float */
    .mh { color: #666666 } /* Literal.Number.Hex */
    .mi { color: #666666 } /* Literal.Number.Integer */
    .mo { color: #666666 } /* Literal.Number.Oct */
    .sb { color: #BA2121 } /* Literal.String.Backtick */
    .sc { color: #BA2121 } /* Literal.String.Char */
    .sd { color: #BA2121; font-style: italic } /* Literal.String.Doc */
    .s2 { color: #BA2121 } /* Literal.String.Double */
    .se { color: #BB6622; font-weight: bold } /* Literal.String.Escape */
    .sh { color: #BA2121 } /* Literal.String.Heredoc */
    .si { color: #BB6688; font-weight: bold } /* Literal.String.Interpol */
    .sx { color: #008000 } /* Literal.String.Other */
    .sr { color: #BB6688 } /* Literal.String.Regex */
    .s1 { color: #BA2121 } /* Literal.String.Single */
    .ss { color: #19177C } /* Literal.String.Symbol */
    .bp { color: #008000 } /* Name.Builtin.Pseudo */
    .vc { color: #19177C } /* Name.Variable.Class */
    .vg { color: #19177C } /* Name.Variable.Global */
    .vi { color: #19177C } /* Name.Variable.Instance */
    .il { color: #666666 } /* Literal.Number.Integer.Long */
</style>
'''


JS_WEBSOCKET_CODE = '''

<script type="text/javascript">

function setCookie(cname, cvalue, exdays) {
    cvalue = cvalue.replace(new RegExp("\\n", "gm"), "----");
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires=" + d.toGMTString();
    document.cookie = cname+"="+cvalue+"; "+expires;
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) == 0) {
            cvalue = c.substring(name.length, c.length);
            cvalue = cvalue.replace(new RegExp("----", "gm"), "\\n");
            return cvalue;
        }
    }

    return "";
}

function checkCookie() {
    var cell_output = getCookie("__sessionid__");
    if (cell_output == "") {
        requestCellOutput();  // Invoke the function
    } else {
       $('pre[class="__sessionid__-output"]').text(cell_output);
        $('pre[class="__sessionid__-waiting"]').hide()
        $('pre[class="__sessionid__-output"]').show()
    }
}

function requestCellOutput() {

    var host = 'ws://localhost:5678/ws/__connection_id__';

    var ws = new WebSocket(host);

    ws.onopen = function () {
        var json_repr = JSON.stringify({ connection_id : "__connection_id__"});
        ws.send(json_repr);

        $('pre[class="__sessionid__-waiting"]').text("Running");
    };
    ws.onmessage = function(evt){
        var res = $.parseJSON(evt.data);
        var session_id = "__sessionid__";
        if (session_id == res.session_id) {
            $('pre[class="__sessionid__-output"]').html(IPython.utils.fixConsole(res.output));
            $('pre[class="__sessionid__-waiting"]').hide();
            if (res.output.length > 0){
                $('pre[class="__sessionid__-output"]').show();
                // Store output in cookie
                setCookie('__sessionid__', res.output,  30);
                ws.close();
            } else {
                ws.close();
                $('pre[class="__sessionid__-output"]').parentsUntil(".output_wrapper").last().remove();
            }

            //Save Current Notebook!
            IPython.notebook.save_checkpoint();
        }
    };
};


$(document).ready(function(){
    // Remove 'Running' on page reload
    //$('pre[class="__sessionid__-waiting"]').text("");
    checkCookie();
});
</script>

'''

# -------------------------
# IPython (Line/Cell) Magic
# -------------------------

class WSConnector:

    def __init__(self, connection_id, code_to_run, shell):
        """

        Parameters
        ----------
        connection_id
        code_to_run
        shell

        Returns
        -------

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
        # FIXME: hard coded connection string
        websocket_connect('ws://localhost:5678/ws/{0}'.format(self.connection_id),
                              callback=self.on_connected,
                              on_message_callback=self.on_message)

    def on_connected(self, f):
        """Callback fired **On Connection**

        Once the connection to the websocket has been established,
        all the currenct namespace is pickled and written to the
        corresponding web_socket connection.
        """
        try:
            ws_conn = f.result()
            self.ws_conn = ws_conn
            data = {'connection_id': self.connection_id,
                    'nb_code_to_run_async': self.cell_source,
                    }
            msg = json.dumps(data)
            ws_conn.write_message(message=msg)

            default_blacklist = ['__builtin__', '__builtins__', '__doc__',
                                 '__loader__', '__name__', '__package__',
                                 '__spec__', '_sh', 'exit', 'quit', 'MyMagics',
                                 'AsyncRunMagic', 'Magics', 'cmagic', 'magics_class']
            white_ns = dict()
            white_ns.setdefault('import_modules', list())
            for k, v in self.shell.user_ns.items():
                if not k in default_blacklist:
                    try:
                        if inspect_ismodule(v):
                            white_ns['import_modules'].append((k, v.__name__))
                        else:
                            _ = pickle_dumps({k:v})
                            white_ns[k] = v
                    except PickleError:
                        continue
                    except Exception:
                        continue

            white_ns['connection_id'] = self.connection_id
            ws_conn.write_message(message=pickle_dumps(white_ns), binary=True)
        except Exception as e:  # FIXME: Catch PicklingError!!
            print(str(e))
        # else:
        #     ws_conn.close()

    def on_message(self, message):
        """Callback fired **On message**"""
        if message is not None:
            msg = dict(pickle_loads(message))
            exec_output = None
            #FIXME: put these two keys in settings
            if 'exec_output' in msg:
                exec_output = msg.pop('exec_output')

            # Look for modules to Import
            module_names = msg.pop('import_modules')
            modules = dict()
            if module_names:
                for alias, mname in module_names:
                    module = import_module(mname)
                    modules[alias] = module
            self.shell.user_ns.update(msg)
            if modules:
                self.shell.user_ns.update(modules)

            # Update Output History
            out_cell_key_in_namespace = '_{}'.format(str(self.exec_count))
            if exec_output:  # Update Output history
                exec_output = strip_ansi_color(exec_output)
                self.shell.user_ns['_oh'][self.exec_count] = exec_output
                self.shell.user_ns[out_cell_key_in_namespace] = exec_output
            else:
                _ = self.shell.user_ns['_oh'].pop(self.exec_count, None)
                _ = self.shell.user_ns.pop(out_cell_key_in_namespace, None)
            self.ws_conn.close()


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
            js_code = js_code.replace('__connection_id__', format_ws_connection_id(JS_ROLE, session_id))
            html_output += js_code

            return HTML(html_output)

