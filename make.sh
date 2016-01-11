#!/bin/bash

# Make with -O0:
# pypy pypy-source\rpython\bin\rpython -O0 --gc=hybrid dipper.py

# Make with -O2:
pypy pypy-source\rpython\bin\rpython dipper.py
