#!/bin/bash

export PYTHONPATH="./pypy-source"

# Make with -O0:
# pypy pypy-source\rpython\bin\rpython -O0 --gc=hybrid dipper.py

# Make with -O2:
pypy pypy-source\rpython\bin\rpython dipper.py
