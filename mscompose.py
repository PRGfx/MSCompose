#!/usr/bin/python
#
# Compose multiple ManiaScript files into one by regarding the order or
# constraints, functions etc. according to a given configuration file.

import sys
import os
import msmin
import json
import hashlib
import pickle
from functools import reduce
import logging

enableCaching = True


def usage():
    print("Usage: python mscompose.py <settings file>")


def enum(**enums):
    return type('Enum', (), enums)


def get_default_config():
    """Returns the default buildtarget config.

    Used if the default config is needed as base for modifications.

    Returs:
        A dict with the configuration name 'default'.
    """
    return {
        "default": {
            "asXML": False,
            "compress": False,
            "files": [],
            "outputfile": "Default.Script.txt",
            "xmlfile": "",
            "active": True
        }
    }


def merge_config(config):
    """Merges given keys into the default config.

    Returns:
        A dict of the default config with given keys overriding the 
        default ones.
    """
    default = get_default_config()
    for key in default["default"]:
        if key not in config:
            config[key] = default["default"][key]
    return config


class Cache(object):
    """Cache for parsed script files.

    The standard cache directory is called .mscompose.
    The files in the cache are named as md5 hash of the source files with
    their relative paths.
    Cached files are rendered invalid if their source files' change date
    is newer than the cached files' change date.

    Attributes:
        global enableCaching: Enables or disables caching.
        basedir: The project directory.
        path: The complete path to the cache directory.

    """
    cache_dir = '.mscompose'

    def __init__(self, basedir):
        self.basedir = basedir
        self.path = os.path.join(basedir, self.cache_dir)
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def _get_filename(self, filename):
        m = hashlib.md5()
        m.update(filename.encode('utf-8'))
        return m.hexdigest()

    def put(self, filename, data):
        """Stores data for a given filename in the cache."""
        fn = self._get_filename(filename)
        pickle.dump(data, open(os.path.abspath(os.path.join(self.path, fn)), "wb"))

    def get(self, filename, source_changed):
        """Gets data for a give filename from the cache.

        Args:
            filename: The filename to get from cache.
            source_changed: The filechange timestamp of the source file.

        Returns:
            None if no valid entry has been found in the cache or the cached data.
        """
        if not enableCaching:
            return None
        fn = self._get_filename(filename)
        fp = os.path.join(self.path, fn)
        if not os.path.isfile(fp):
            return None
        if os.path.getmtime(fp) < source_changed:
            return None
        return pickle.load(open(fp, "rb"))

    def clear(self):
        """Clears all files from the cache."""
        for f in os.listdir(self.path):
            fp = os.path.join(self.path, f)
            try:
                if os.path.isfile(fp):
                    os.unlink(fp)
            except Exception:
                pass


ParserState = enum(Beginning=0, Base=1, Constraint=2, Function=3, FunctionStart=4, LabelInsert=5, MultilineComment=6, Main=7)


class MSFunction(object):
    """A ManiaScript function.

    Attributes:
        fntype: The return type of the ManiaScript function.
        name: The name of the ManiaScript function.
        args: The argument string of the function (everything inside the parenthesis).
        body: The body of the function (the content in curly braces).
    """

    def __init__(self, fntype, name, args, body):
        """Inits a ManiaScript function."""
        self.fntype = fntype
        self.name = name
        self.args = args
        self.body = body

    def __str__(self):
        return self.fntype + " " + self.name + "(" + self.args + ") {" + self.body + "}\n"


class MSLabel(object):
    """A ManiaScript label. (Insertion block)

    Attributes:
        name: The name of the label. (***<name>***)
        code: The code of the label. (***<name>******<code>***)
    """
    def __init__(self, labelName, labelCode):
        self.name = labelName
        self.code = labelCode

    def __str__(self):
        return "***" + self.name + "***\n***\n" + self.code.strip() + "\n***\n\n"


class MSComposer(object):
    """Combines multiple ManiaScript files' sources.

    The code is interpreted as global variables, functions, labels and constraints.
    The parsed data is cached - if enabled - and finally reordered grouping the
    named fields to avoid syntax errors.

    Attributes:
        buildconfig: A buildconfig dict, see get_default_config().
        root_dir: The project's root directory.
        result: The resulting code as string.
        constraints: A list with all constraints.
        global_vars: A list with all global variables.
        functions: A list with all functions.
        labels: A list with all labels.
        cache: A reference to the cache.
    """
    def __init__(self, buildconfig, root_dir):
        self.buildconfig = buildconfig
        self.root_dir = root_dir
        self.result = ""
        self.constraints = []
        self.global_vars = []
        self.functions = []
        self.labels = []
        self.mainBody = ""
        self.cache = Cache(root_dir)

    def save(self):
        """Saves the result code according to the buildconfig data."""
        output_file = os.path.abspath((os.path.join(self.root_dir, self.buildconfig["outputfile"])))
        if not self.buildconfig["outputfile"]:
            logging.error('No outputfile was specified!')
            return
        if self.buildconfig["compress"]:
            self.result = msmin.process(self.result)
        with open(output_file, "w") as outp:
            outp.write(self.result)
        logging.debug("Saved Script file '%s'" % self.buildconfig["outputfile"])
        if self.buildconfig["asXML"]:
            xml_output_file = os.path.abspath((os.path.join(self.root_dir, self.buildconfig["xmlfile"])))
            if not self.buildconfig["xmlfile"]:
                logging.error('No outputfile for xml output was specified!')
                return
            xmlout = '<?xml version="1.0"?>\n<script><![CDATA['
            with open(output_file) as code:
                xmlout += code.read()
            xmlout += ']]></script>'
            with open(xml_output_file, "w") as outp:
                outp.write(xmlout)
            logging.debug("Saved XML file '%s'" % self.buildconfig["xmlfile"])

    def _parse(self, code):
        globalVars = []
        functions = []
        labels = []
        constraints = []

        state = ParserState.Beginning
        stack = 0
        string3Stack = 0
        isString = False
        isString3 = False
        fnState = 0
        i = 0
        currentFn = {}
        mainBody = "";
        while i < len(code):
            c = code[i]
            if state == ParserState.Beginning:
                if c == '#':
                    start = i
                    while c != '\n' and code[i:i + 1] != '//' and i < len(code):
                        i += 1
                        c = code[i]
                    constraints.append(code[start:i + 1].strip())
                else:
                    if c.strip() != '':
                        state = ParserState.Base
            if state == ParserState.Base:
                if c == 'd':
                    start = i
                    while c != ';' and i < len(code):
                        i += 1
                        c = code[i]
                    globalVars.append(code[start:i + 1])
                elif c.isupper():
                    i -= 2
                    state = ParserState.FunctionStart
                elif code[i:i + 3] == '***':
                    state = ParserState.LabelInsert
                    i += 2
                elif code[i:i + 2] == '/*':
                    state = ParserState.MultilineComment
                    i += 1
                elif code[i:i + 4] == 'main':
                    state = ParserState.Main
                    i += 5
            elif state == ParserState.MultilineComment:
                while i < len(code) and code[i:i + 2] != "*/":
                    i += 1
                state = ParserState.Base
            elif state == ParserState.LabelInsert:
                start = i
                while code[i:i + 3] != '***' and i < len(code):
                    i += 1
                labelName = code[start:i].strip()
                i += 1
                while code[i:i + 3] != '***' and i < len(code):
                    i += 1
                i += 3
                start = i
                while i < len(code):
                    c = code[i]
                    if c == '"':
                        string3Stack += 1
                        if not isString3:
                            isString3 = string3Stack >= 3
                        else:
                            isString3 = string3Stack < 3
                        isString = isString3 or (string3Stack == 1 and not isString)
                    if not isString and code[i:i + 3] == '***':
                        break
                    i += 1
                # labels[labelName] = code[start:i]
                labels.append(MSLabel(labelName, code[start:i]))
                state = ParserState.Base
            elif state == ParserState.FunctionStart:
                isString = False
                isString3 = False
                fnState = 0
                stack = 0
                string3Stack = 0
                currentFn = {"type": "", "name": "", "args": "", "body": ""}
                state = ParserState.Function
            elif state == ParserState.Function:
                if fnState == 0:  # Type
                    if c.isspace():
                        fnState += 1
                    else:
                        currentFn["type"] += c
                elif fnState == 1:  # Name
                    if c == '(':
                        fnState += 1
                    else:
                        currentFn["name"] += c
                elif fnState == 2:  # Arguments
                    if c == ')':
                        fnState += 1
                    else:
                        currentFn["args"] += c
                elif fnState == 3:  # Arguments End
                    if c == '{':
                        fnState += 1
                elif fnState == 4:
                    if c == '"':
                        string3Stack += 1
                        if not isString3:
                            isString3 = string3Stack >= 3
                        else:
                            isString3 = string3Stack < 3
                        isString = isString3 or (string3Stack == 1 and not isString)
                    else:
                        string3Stack = 0
                        if not isString:
                            if c == '{':
                                stack += 1
                            if c == '}':
                                stack -= 1
                    if stack < 0:
                        fn = MSFunction(currentFn["type"], currentFn["name"], currentFn["args"], currentFn["body"])
                        functions.append(fn)
                        state = ParserState.Base
                    else:
                        currentFn["body"] += c
            # TODO: Might need changes to capture only the body itself without enclosing braces
            elif state == ParserState.Main:
                isString = False
                isString3 = False
                stack = 1
                string3Stack = 0
                if c == '"':
                    string3Stack += 1
                    if not isString3:
                        isString3 = string3Stack >= 3
                    else:
                        isString3 = string3Stack < 3
                    isString = isString3 or (string3Stack == 1 and not isString)
                else:
                    string3Stack = 0
                    if not isString:
                        if c == '{':
                            stack += 1
                        if c == '}':
                            stack -= 1
                if stack < 0:
                    state = ParserState.Base
                else:
                    mainBody += c
            i += 1
        return globalVars, functions, labels, constraints, mainBody

    def process(self):
        """Kicks of the processing of all files mentioned in the buildconfig.

        In the end saves the result.
        """
        for f in self.buildconfig["files"]:
            source = os.path.abspath(os.path.join(self.root_dir, f))
            if not os.path.isfile(source):
                logging.warn("File '%s' does not exist" % f)
                continue
            cache_data = self.cache.get(source, os.path.getmtime(source))
            if cache_data is None:
                with open(source) as content:
                    sourcecode = content.readlines()
                line_count = 0
                code_string = "".join(sourcecode[max(0, line_count - 1):])
                (globalVars, functions, labels, constraints, mainBody) = self._parse(code_string)
                self.cache.put(source, (globalVars, functions, labels, constraints))
                logging.debug("%s... done" % f)
            else:
                logging.debug("%s found in cache" % f)
                try:
                    (globalVars, functions, labels, constraints, mainBody) = cache_data                    
                except Exception:
                    self.cache.clear()
                    self.process()
                    return
            self.global_vars += [x for x in globalVars if x]
            self.functions += functions
            self.labels += labels
            self.constraints += constraints
            # TOOD: Will break ManiaScript syntax for multiple mainBody matches
            self.mainBody += mainBody.strip()[1:-1]

        self.constraints.sort()
        # self.global_vars.sort(key=lambda s: s.split()[2])
        _seen = set()
        _seen_add = _seen.add
        constraint_list = [c for c in self.constraints if c.startswith('#Include') and not (c in _seen or _seen_add(c))] \
                          + [c for c in self.constraints if not c.startswith('#Include')]
        self.constraints = constraint_list
        self.result = "\n".join(self.constraints) + "\n"
        self.result += "\n".join(self.global_vars) + "\n"
        self.result += reduce(lambda o, e: o + str(e), self.labels, "")
        self.result += reduce(lambda o, e: o + str(e), self.functions, "")
        # print(self.mainBody)
        # mainBodies = filter(None, self.mainBody)
        if self.mainBody:
            self.result += "main() {\n" + self.mainBody + "}"
        self.save()


def main(args):
    if len(args) < 1:
        usage()
        sys.exit(1)
    if not os.path.isfile(args[0]):
        print("Config file not found!")
        sys.exit(1)
    cfg = os.path.abspath(args[0])
    with open(cfg) as cfgf:
        configs = json.loads(cfgf.read())
    if len(args) > 1:
        build_config = configs[args[1]]
        build_config = merge_config(build_config)
        if not build_config["active"]:
            logging.info("Build config '%s' skipped (Inactive)" % build_config)
            return
        logging.info("Processing build config '%s'" % build_config)
        composer = MSComposer(build_config, os.path.dirname(cfg))
        composer.process()
    else:
        for key, build_config in configs.items():
            build_config = merge_config(build_config)
            if not build_config["active"]:
                logging.info("Build config '%s' skipped (Inactive)" % build_config)
                continue
            logging.info("Processing build config '%s'" % build_config)
            composer = MSComposer(build_config, os.path.dirname(cfg))
            composer.process()
    logging.info("Processing complete!")


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] %(message)s')
    main(sys.argv[1:])
