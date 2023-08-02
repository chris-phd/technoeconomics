#!/usr/bin/env python3

import sys
import os

try:
    from technoeconomics.system import System, Device, Flow
    from technoeconomics.utils import *
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.system import System, Device, Flow
    from technoeconomics.utils import *

def main():
    print("technoeconomics.low_emission_steel")

if __name__ == '__main__':
    main()