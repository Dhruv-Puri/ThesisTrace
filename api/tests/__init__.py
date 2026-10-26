"""Standard-library test suite for Paper2Reality.

Run from the repository root:

    python -B -m unittest discover -s api/tests -t . -v

The suite deliberately avoids third-party packages so it can run on any machine
without installing anything.  Model-backed paths are exercised inside Docker.
"""
