import os
from rpython.rlib.objectmodel import we_are_translated


if we_are_translated():
    from rpython.rlib.streamio import open_file_as_stream

    def readall(filename):
        if not file_exists(filename):
            raise IOError(filename)
        # must catch WindowsError here or it won't compile for some reason
        try:
            fp = open_file_as_stream(filename)
            data = fp.readall()
            fp.close()
            return data
        except WindowsError as e:
            return ""

else:
    def readall(filename):
        if not file_exists(filename):
            raise IOError(filename)
        fp = open(filename, 'r')
        data = fp.read()
        fp.close()
        return data


def file_exists(path):
    try:
        return os.path.exists(path)
    except WindowsError as e:
        return False


class Stream(object):
    """
    Class that emulates the standard Python sys.stdout/in/err only using
    the ``os`` module.

    http://kirbyfan64.github.io/posts/the-magic-of-rpython.html
    """
    STDIN = 0
    STDOUT = 1
    STDERR = 2

    def __init__(self, stream):
        self.stream = stream

    @staticmethod
    def open(filename, fmtstr):
        if fmtstr == 'r':
            flags = os.O_RDONLY
        elif fmtstr == 'w':
            flags = os.O_WRONLY
        else:
            raise ValueError("Invalid file open flag '%s'" % fmtstr)

        #if we_are_translated():
        #    return Stream(rposix.open(filename, flags, 0666))
        #else:
        return Stream(os.open(filename, flags, 0666))

    def close(self):
        os.close(self.stream)

    def write(self, val):
        os.write(self.stream, val)

    def read(self):
        res = ""
        while True:
            buf = os.read(self.stream, 16)
            if not buf:
                return res
            else:
                res += buf
        return os.read(self.stream, numbytes)

    def readline(self):
        res = ""
        while True:
            buf = os.read(self.stream, 16)
            if not buf:
                return res
            res += buf
            if res[-1] == "\n":
                return res[:-1]
        return res

    def readlines(self):
        res = []
        cur = ''
        while True:
            buf = os.read(self.stream, 16)
            if not buf:
                return res
            cur += buf
            if cur[-1] == '\n':
                res.append(cur[:-1])
                cur = ''
