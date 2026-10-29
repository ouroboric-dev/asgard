"""The component recipes of the token contract, in one file (recipes.css) that the reference and the playground both read."""
import os


def css():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes.css"), encoding="utf-8") as fh:
        return fh.read()
