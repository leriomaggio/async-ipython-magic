"""
"""
# Author: Valerio Maggio <valeriomaggio@gmail.com>
# Copyright (c) 2015 Valerio Maggio <valeriomaggio@gmail.com>
# License: BSD 3 clause

from IPython.utils.coloransi import TermColors, color_templates


COLORS = [color[1] for color in color_templates]


def strip_ansi_color(text):
    """
    Removes ANSI colors from the text

    Parameters
    ----------
    text : str
        The input text string to process

    Returns
    -------
    str : the plain text with all ANSI colors stripped.

    """
    text = text.replace(TermColors.Normal, TermColors.NoColor)
    for color in COLORS:
        text = text.replace(TermColors._base % (color), TermColors.NoColor)
    return text