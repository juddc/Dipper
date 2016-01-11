@echo off

REM Make with -O0:
REM C:\pypy\pypy.exe pypy-source\rpython\bin\rpython -O0 --gc=hybrid dipper.py

REM Make with -O2:
C:\pypy\pypy.exe pypy-source\rpython\bin\rpython dipper.py
