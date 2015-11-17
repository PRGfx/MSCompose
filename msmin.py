#!/usr/bin/python
#
# Compress ManiaScript by erasing unnecessary whitespaces and comments
# 
# original author: Marcel <marcel@mania-community.de>
# ported from php: https://github.com/BluePsyduck/ManiaScript/blob/master/src/ManiaScript/Compressor.php

import sys
import logging

code = "";
codemin = "";
codelen = 0;
cursor = 0;
whitespaces = ["\n", "\r", "\t", ' ']
ignoreFollowingWhitespace = [' ', "\n", "\t", "\r", '[', '(', '{', '}', ')', ']', ',', ':', ';', '"', '=', '<', '>',
                             '|', '&', '-', '+', '*', '/', '%', '^', '!']
inputfile = "";
outputfile = "";


def usage():
    print ("usage: python msmin.py <inputfile> [<outputfile>]")


def getCode():
    global inputfile, codelen, code
    with open(inputfile, "r") as inp:
        code = inp.read()
        codelen = len(code)


def read():
    global code, codelen, cursor, codemin, whitespaces
    while cursor < codelen:
        position = cursor
        curchar = code[cursor]
        if curchar in whitespaces:
            readWhitespace()
        else:
            if curchar == '/':
                readSlash()
            elif curchar == '#':
                readDirective()
            elif curchar == '"':
                readString()
        if position == cursor:
            codemin += curchar
            cursor += 1


def readSlash():
    global code, codelen, cursor
    if cursor + 1 < codelen:
        nextchar = code[cursor + 1]
        if nextchar == '/':
            skipUntil("\n")
        elif nextchar == '*':
            skipUntil("*/")


def readDirective():
    global cursor
    copyUntil("\n")
    cursor += 1


def findPos(delimiter):
    global code, cursor, codelen
    x = code.find(delimiter, cursor)
    if x < 0:
        return codelen
    return x


def copyUntil(delimiter):
    global code, cursor, codemin
    newpos = findPos(delimiter)
    codemin += code[cursor:newpos]
    cursor = newpos


def skipUntil(delimiter):
    global cursor
    cursor = findPos(delimiter) + len(delimiter)


def readWhitespace():
    global codemin
    skipWhitespace()
    if isWhitespaceRequired():
        codemin += " "


def skipWhitespace():
    global cursor, codelen, code, whitespaces
    while cursor < codelen and code[cursor] in whitespaces:
        cursor += 1


def isWhitespaceRequired():
    result = False
    global cursor, codelen, code, codemin, ignoreFollowingWhitespace
    if len(codemin) > 0 and cursor < codelen:
        clen = len(codemin)
        lastchar = codemin[-1]
        nextchar = code[cursor]
        if lastchar == '}' and nextchar == '}' and clen >= 2:
            result = codemin[-2] == '}'
        else:
            result = not (lastchar in ignoreFollowingWhitespace or nextchar in ignoreFollowingWhitespace)
    return result


def readString():
    global cursor, code, codemin, codelen
    start = cursor
    cursor += 1
    while cursor < codelen:
        curchar = code[cursor]
        if curchar == '\\':
            cursor += 2
        elif curchar == '"':
            break
        else:
            cursor += 1
    cursor += 1
    codemin += code[start:cursor]


def save():
    global codemin, codelen, outputfile
    with open(outputfile, "w") as outp:
        outp.write(codemin)
    logging.info("Compressed from %s chars to %s into %s" % (str(codelen), str(len(codemin)), outputfile))


def reset():
    global cursor, code, codemin, codelen
    code = ""
    codemin = ""
    cursor = 0
    codelen = 0


def process(data):
    global code, codemin, codelen
    reset()
    code = data
    codelen = len(code)
    read()
    logging.info("Compressed from %s chars to %s" % (str(codelen), str(len(codemin))))
    return codemin

def main(args):
    global inputfile, outputfile
    reset()
    if len(args) < 1:
        usage()
        sys.exit(1)
    else:
        inputfile = args[0]
        if len(args) >= 2:
            outputfile = args[1]
        else:
            x = inputfile.split('.')
            if (len(x) > 1):
                ext = x.pop()
                x.append("min")
                x.append(ext)
                outputfile = ".".join(x)
            else:
                outputfile = inputfile + "_min"
    getCode()
    read()
    save()


if __name__ == "__main__":
    main(sys.argv[1:])
