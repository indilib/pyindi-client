"""
This file makes the PyIndi directory a Python package.

It imports all contents from the .PyIndi module into the package namespace
for backward compatibility, allowing users to import the library using 'import PyIndi'.
"""
# Import contents of the PyIndi module into the package namespace
# for backward compatibility (allows 'import PyIndi')
from .PyIndi import *
