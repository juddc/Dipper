import basicio


def _error_sourceview(filename, lineno, colno, prefix="    "):
    sourceview = ["", "", "", ""]

    if filename != "":
        lines = basicio.readall(filename).split("\n")

        i = 0
        for line in lines:
            if i == lineno - 1:
                sourceview[0] = "%s%s: %s" % (prefix, i + 1, line.rstrip("\n"))
            elif i == lineno:
                sourceview[1] = "%s%s: %s" % (prefix, i + 1, line.rstrip("\n"))
            elif i == lineno + 1:
                # skip sourceview[2]
                sourceview[3] = "%s%s: %s" % (prefix, i + 1, line.rstrip("\n"))
            i += 1
            # break if we're past the important bits:
            if i > lineno + 1:
                break

    if colno > -1:
        # make sourceview[2] an arrow pointing to the right column
        pointer = [" "] * (colno + 1)
        for col in range(colno):
            pointer[col] = "-"
        pointer[colno] = "^"
        sourceview[2] = "%s   %s" % (prefix, "".join(pointer))

    return sourceview


def error_message(filename, sourcepos, excname="Exception", message=""):
    assert isinstance(sourcepos, tuple) and len(sourcepos) == 2
    lineno, colno = sourcepos
    
    lines = ["Error in file %s line %s, col %s:" % (filename, lineno + 1, colno + 1)]

    if lineno > -1:
        for line in _error_sourceview(filename, lineno, colno, prefix="    "):
            lines.append(line)

    if len(message) == 0:
        lines.append(excname)
    else:
        lines.append("%s: %s" % (excname, message))
    return "\n".join(lines)


def error_from_exception(filename, sourcepos, exc):
    excname = exc.__class__.__name__
    return error_message(filename, sourcepos, excname=excname, message=str(exc))
