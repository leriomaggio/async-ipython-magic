# `%%async_run`: an IPython notebook magic for asynchronous cell execution


## Description (Talk Abstract @EuroScipy 2016) ##

<img src="https://github.com/leriomaggio/deep-learning-keras-euroscipy2016/blob/master/imgs/euroscipy_2016_logo.png" width="50%" />

The IPython `notebook` project is one the preferred tools of data scientists, 
and it is nowadays the bastion for *Reproducible Research*.

In fact, notebooks are now used as in-browser IDE (*Integrated Development Environment*) to implement the whole data analysis process, along with the corresponding documentation. 

However, since this kind of processes usually include heavy-weight computations, 
it may likely happen that execution results get lost if something wrong happens, e.g. the connection to the 
notebook server hangs or an accidental page refresh is issued.

To this end, `[%]%async_run` notebook line/cell magic to the rescue.

In this talk, I would like to talk about some of the technologies I played with since I decided to develop 
this extension.
These technologies include **asynchronous I/O** libraries (e.g. `asyncio`, `tornado.websocket`), 
**`multiprocessing`**,  along with IPython `kernels` and `notebooks`.

During the talk, I would like to discuss pitfalls, failures, and adopted solutions (e.g. *namespace management 
among processes*) , aiming at getting as many feedbacks as possible from the community.

A general introduction to the actual state-of-the-art of the **Jupyter** projects (an libraries) will be 
presented as well, in order to help those who are willing to know some more details about the internals of 
IPython.

### Slides ###

Slides of the talk are available on my 
[SpeakerDeck](https://speakerdeck.com/valeriomaggio/percent-percent-async-run-an-ipython-notebook-extension-for-asynchronous-cell-execution)
profile.

## Enabling the Magic(s)

Enabling the magic is simple as *copying files into a directory*. Open the terminal and:

``` 
cp -R async_run_ipython_magic.py run_async/ ~/.ipython/profile_default/startup/
```

After that, the magic will be enabled by default at the startup of each Jupyter/IPython sessions.

## Requirements ##

The **only** two main requirements for this Magic are `notebook` and `tornado` (which will be
indeed installed by the *jupyter notebook* itself).

### Python 2 Users

So far, this magic works **only** with Python 3.
For example, it relies on the `concurrent.futures` module to allow for the multiprocessing execution.

This module is only available in **Python 3** standard library. For Python 2, you have to `pip install`
the [futures](https://pypi.python.org/pypi/futures)

## Usage ##

Three `[%]%async_*` magics are provided within this package:

* `%async_run_server` : Spawns the `AsyncRunServer` process, which is in charge of handling the async cell execution inside a Tornado `WebApplication` and `IOLoop`.

* `%async_stop_server` : Stops the `AsyncRunServer` running process, if any.

* `[%]%async_run` : Line/Cell Magic to asynchronously execute the content of the line/cell, respectively.

### Examples ###

Please, check out the `examples` folder for examples and hints for usage (so far, very few examples available. More to come!)


### Note: ###

If you want to run the server in a terminal and get the log output, move to the `startup` folder and execute:

- `python -m run_async.run_server`



