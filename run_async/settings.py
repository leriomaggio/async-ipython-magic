"""
Main Configuration Settings
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

JS_ROLE = 'JS'
PY_ROLE = 'PYTHON'

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 5678

# Separator String for WebSocket connections
CONNECTION_ID_SEP = '---'

LIGHT_HTML_OUTPUT_CELL = '''
<pre class={session_id}-waiting></pre>
<pre class="{session_id}-output" style="display: none"></pre>
'''

# Not Yet Used
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

EXEC_OUTPUT = 'exec_output'

# List of names to be excluded from pickling during the async process
DEFAULT_BLACKLIST = ['__builtin__', '__builtins__', '__doc__',
                     '__loader__', '__name__', '__package__',
                     '__spec__', '_sh', 'exit', 'quit', 'MyMagics',
                     'AsyncRunMagic', 'Magics', 'cmagic', 'magics_class']