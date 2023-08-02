#!/usr/bin/env python3

import sys
import os

# Necessary to import the package from the examples directory if
# the package is not installed via pip
examples_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(examples_dir)
sys.path.insert(0, package_dir)

from technoeconomics.utils import *

def main():
    print("technoeconomics.low_emission_steel")

if __name__ == '__main__':
    main()