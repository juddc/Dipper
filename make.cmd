@echo off

SET PYTHONPATH=%PYTHONPATH%:.\pypy-source

REM Make with -O0:
REM pypy pypy-source\rpython\bin\rpython -O0 --gc=hybrid dipper.py

REM Make with -O2:
pypy pypy-source\rpython\bin\rpython dipper.py
