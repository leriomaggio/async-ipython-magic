"""
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

JS_ROLE = 'JS'
PY_ROLE = 'PYTHON'

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 5678

def connection_string(web_socket=True, extra=''):
    if web_socket:
        protocol = 'ws'
    else:
        protocol = 'http'
    return '{proto}://{server}:{port}/{extra}'.format(proto=protocol, server=SERVER_ADDR,
                                                     port= SERVER_PORT, extra=extra)

CONNECTION_ID_SEP = '---'

def format_ws_connection_id(role_name, session_id):
    """
    Format and return a (likely) unique string
     to be fed to the Websocket server in the
     url. This string will be used to uniquely
     identify the opened connection.
     See `run_server.ConnectionHandler` for further
     details.

    Parameters
    ----------
    role_name : str
        The name of the role of the client trying to connect
        to the WebSocket
    session_id : str
        The uniquely defined `uuid` generated for the
        connecting client.

    Returns
    -------
    ws_conn_id : str
        String representing the connection ID to be
        fed to the WebSocket server (url)
    """

    return "{0}{1}{2}".format(role_name, CONNECTION_ID_SEP, session_id)


def parse_ws_connection_id(connection_id):
    """
    Get and return the role name and the
    session id associated to the input connection id.

    Parameters
    ----------
    connection_id : str
        The connection ID formatted according to the
        `format_ws_connection_id` function.

    Returns
    -------
    _connection_id : str
        The name of the role of the connected client associated to the connection ID
        (namely, "JS" or "PY")
    session_id : str
        The session id associated to the client at connection time.

    Note
    ----
    This function is the counterpart of the `format_ws_connection_id` function.
    This function decompose a connection id, while the former composes it.
    """

    role_name, session_id = connection_id.split(CONNECTION_ID_SEP)
    return role_name, session_id