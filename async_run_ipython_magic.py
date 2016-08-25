"""
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

from run_async.async_run_magic import AsyncRunMagic

# from IPython.core.magic import register_cell_magic
# async_run = register_cell_magic(async_run)

# -----------------------------
# Register the new Class Magic
# -----------------------------

# noinspection PyUnresolvedReferences
ip = get_ipython()
ip.register_magics(AsyncRunMagic)