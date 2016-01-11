## Dipper

A toy programming language using the RPython toolchain

Dipper looks like a weird hybrid of Python and Rust, with static typing and optional type specifiers.

```
fn fib(n : int) {
	if n < 2 {
		return n
	}
	return fib(n - 2) + fib(n - 1)
}

fn main(argv) {
  print "Hello World"
  print fib(4)
  return 0
}
```

## Compiling Dipper

You don't actually have to build the Dipper interpreter to try it out. Dipper is written
in RPython, which is a subset of Python 2, which means you can run it with any Python 2
interpreter such as PyPy 4 or CPython 2.7.

Dipper depends on several libraries included with RPython, so you'll need to download
the PyPy source and place it into the `pypy-source` directory whether you're compiling
to native code or not. There are no other dependencies.

Simple hello-world example:

`pypy dipper.py ./code/simple.dip`

To get a huge speed boost, you can compile the whole dipper codebase to native code
using RPython from the PyPy project.

First, download the PyPy source (tested with version 4.0.1) and place it in the
`pypy-source` directory.

> #### Using Visual Studio 2013?
> If you want to compile with Visual Studio 2013, you'll need to make a small change to
> `pypy-source/rpython/translator/platform/windows.py` in the function `find_msvc_env`.
> Where it says `for vsver in (100, 90, 80, ...`, add the value `120` to that tuple.
> That will allow RPython to find Visual Studio 2013. Visual Studio 2015 will not work
> and is not supported until the PyPy project decides to support it.

Next, you'll need either PyPy 4 or CPython 2.7 installed. The build scripts make.cmd
and make.sh look for PyPy but you can change these to look for CPython if you'd like.

Now, just run `make.cmd` or `make.sh` and it should produce an executable called `dipper-c`.

Then you can run the hello-world example using the native code version:

`./dipper-c ./code/simple.dip`
