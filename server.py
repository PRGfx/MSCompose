#!/usr/bin/env python3
#
# Provides an interface for creating config files for the mscompose module.

import datetime
import threading
import webbrowser
import sys
import pprint
import getopt
from http.server import HTTPServer as http_server
from http.server import SimpleHTTPRequestHandler as http_handler
import re
import os
import urllib.parse as urlparse
import subprocess
import platform
import json
import mscompose
import logging

FILE = 'index.html'
PORT = 4652
CONFIGFILE = "mscompose.cfg"
PROJECTS_FILE = 'projects.json'
logfile = ''

project_path = os.path.dirname(os.path.realpath(__file__))


def open_folder(path):
    """
    Opens a specified directory on the host.
    """
    path = str(path.replace('\\\\', '\\'))[2:-1]
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def get_config(path):
    """Reads and interprets the configfile in the given path.

    Args:
        path: The path to look in for the configfile.

    Raises:
        IOError: It is assumed that the file exists as this is an internal
            method.
    """
    cfg = os.path.join(path, CONFIGFILE)
    with open(cfg) as f:
        res = json.load(f)
    return res

def load_config(path):
    """Generates a json response containing a specified config file.

    Args:
        path: The path to look in for the configfile.

    Returns:
        "false" if the path is invalid.
        "null" if no config file was found.
        JSON encoded config file if found.
    """
    if not os.path.isdir(path):
        return "false"
    cfg = os.path.join(path, CONFIGFILE)
    if os.path.isfile(cfg):
        with open(cfg) as f:
            res = f.read()
        return res
    else:
        return "null"


def create_config(path):
    """Stores the defaultconfig in a new configfile in the given path.

    Overwrites exisiting config files.

    Args:
        path: The path to cretae the config file in.
    """
    path = str(path.replace('\\\\', '\\'))[2:-1]
    cfg = os.path.join(path, CONFIGFILE)
    default_config = mscompose.get_default_config()
    empty_config = json.dumps(default_config, sort_keys=True, indent=4, separators=(',', ': '))
    f = open(cfg, 'w')
    f.write(empty_config)
    f.close()


def get_projects():
    """Returns the content of the file listing the projects

    Returns: JSON array with projects as {name: ..., path: ...}
    """
    if not os.path.isfile(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'w') as f:
            f.write('[]')
    with open(PROJECTS_FILE) as f:
        projects_list = f.read()
    if not projects_list:
        return '[]'
    return projects_list


def set_projects(data):
    """Saves the list of existing projects.

    Args:
        data: The JSON encoded list of existing projects.
    """
    data = data.replace('\\\\', '\\')
    with open(PROJECTS_FILE, 'w') as f:
        f.write(data)


def path_to_dict(path):
    """Creates a JSON string for the file tree in the given path.

    Args:
        path: The path to build a tree from.
    """
    d = {'name': os.path.basename(path)}
    if os.path.isdir(path):
        d['type'] = "directory"
        d['children'] = [path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]
    else:
        d['type'] = "file"
    return d


def list_files(path):
    """Dumps a JSON list of all files in a given path."""
    return json.dumps([path_to_dict(path)])


def save_config(path, data):
    """Stores buildconfigs in a config file in the given path.

    Args:
        path: The config file's root path.
        data: A JSON string containing the new config.
    """
    json_data = json.loads(data)
    with open(os.path.abspath(os.path.join(path, CONFIGFILE)), 'w') as f:
        f.write(json.dumps(json_data, sort_keys=True, indent=4, separators=(',', ': ')))


def get_htmllog():
    """Returns the html-formatted log."""
    message = ''
    icons = {'WARNING': 'exclamation', 'ERROR': 'exclamation-triangle', 'INFO': 'info', 'DEBUG': 'wrench'}
    with open(logfile) as log:
        lines = log.readlines()
        for line in lines:
            data = line.split('::')
            time = data[1].split(' ')
            message += '<div class="logentry %s"><span class="fa fa-%s"></span><span class="date">%s</span>%s</div>' % (data[0].lower(), icons[data[0]], time[1], data[2])
    return message

class MyRequestHandler(http_handler):
    """Handles incoming requests to the sever."""

    def do_POST(self):
        """Handles post requests."""
        try:
            length = int(self.headers.getheader('content-length'))
        except AttributeError:
            length = int(self.headers.get('content-length'))
        data_string = str(self.rfile.read(length))
        parsed_params = urlparse.urlparse(self.path)
        queryParsed = urlparse.parse_qs(parsed_params.query)
        result = ""
        # TODO: why does data_string work here, but not below
        if parsed_params.path == "/open_path":
            open_folder(data_string)
        elif parsed_params.path == "/create_config":
            create_config(data_string)
        elif parsed_params.path == "/save_config":
            save_config(queryParsed["path"][0], data_string[2:-1])
        elif parsed_params.path == "/clear_cache":
            cache = mscompose.Cache(queryParsed["path"][0])
            cache.clear()
            logging.info("Cache cleared.")
        elif parsed_params.path == "/build":
            data = urlparse.parse_qs(data_string[2:-1])
            path = os.path.abspath(data["path"][0])
            configs = get_config(path)
            composer = mscompose.MSComposer(configs[data["target"][0]], path)
            composer.process()
        elif parsed_params.path == "/save_projects":
            set_projects(data_string[2:-1])
        # TODO: implement shutdown functionality
        # elif parsed_params.path == "/shutdown":
        #     self.send_response(200)
        #     self.end_headers()
        #     sys.exit(-1)
        self.send_response(200)
        self.end_headers()
        try:
            self.wfile.write(result)
        except TypeError:
            self.wfile.write(bytes(result, 'UTF-8'))

    def do_GET(self):
        """Handles get requests."""
        self.send_response(200)
        parsed_params = urlparse.urlparse(self.path)
        query_parsed = urlparse.parse_qs(parsed_params.query)
        if parsed_params.path == "/validate_path":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            message = "true" if os.path.exists(query_parsed["path"][0]) else "false"
        elif parsed_params.path == "/load_config":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            message = load_config(query_parsed["path"][0])
        elif parsed_params.path == "/tree":
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            message = open('treeview.html').read()
        elif parsed_params.path == "/list_files":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            message = list_files(query_parsed["path"][0])
        elif parsed_params.path == "/get_projects":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            message = get_projects()
        elif parsed_params.path == "/log":
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            message = get_htmllog()
        elif parsed_params.path == "/get_default_config":
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            message = json.dumps(mscompose.get_default_config())
        elif os.path.isfile(parsed_params.path[1:]):
            self.end_headers()
            with open(parsed_params.path[1:], encoding='UTF-8', errors="replace") as f:
                message = f.read().encode("UTF-8")
        elif parsed_params.path.endswith(".css"):
            self.send_header('Content-Type', 'text/css')
            self.end_headers()
            message = open(parsed_params.path[1:]).read()
        elif parsed_params.path.endswith(".js"):
            self.send_header('Content-Type', 'text/javascript')
            self.end_headers()
            message = open(parsed_params.path[1:]).read()
        else:
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            message = open(FILE).read()
        try:
            self.wfile.write(bytes(message, 'UTF-8'))
        except TypeError:
            self.wfile.write(message)
        return


def open_browser():
    """Start a browser after waiting for half a second."""

    def _open_browser():
        webbrowser.open('http://localhost:%s/' % PORT)

    thread = threading.Timer(0.5, _open_browser)
    thread.start()


def start_server():
    """Start the server."""
    server_address = ("", PORT)
    print('Starting server')
    try:
        server = http_server(server_address, MyRequestHandler)
        server.serve_forever()
    except Exception as e:
        print(e)

def usage():
    print('server.py [options]')
    print('options:')
    print('-h          Display this help')
    print('-p --port   Specify a port for the server')
    print('--open      Open a browser window')

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    logging.getLogger('requests').setLevel(logging.WARNING)
    logfile = 'logs/' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.log'
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(levelname)s::%(asctime)s::%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    isset_open = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:", ["port=", "open"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ('-p', '--port'):
            PORT = arg
        elif opt == '--open':
            isset_open = True
    try:
        if isset_open:
            open_browser()
        start_server()
    except KeyboardInterrupt:
        print("Server stopped...exiting")
    except Exception as e:
        print(e)
        print("Shutting down server...")
    sys.exit(0)
