#!/usr/bin/env python
# Copyright (c) 2012 Raffaele Sena https://github.com/raff
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS

#
# A SQL-like command line tool to query ElasticSearch
#
from __future__ import print_function

import sys

try:
    import readline
    assert readline
except ImportError:
    try:
        import pyreadline as readline
        assert readline
    except ImportError:
        readline = None
else:
    import rlcompleter
    assert rlcompleter

    if(sys.platform == 'darwin') and 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    # readline.parse_and_bind("tab: complete")

import os
import os.path
import shlex
import traceback

if False:
    from pprint import pprint
else:
    import json

    def pprint(obj):
        print(json.dumps(obj, indent=2))

from cmd2 import Cmd
from search import ElseSearch, DEFAULT_PORT
from version import __version__

HISTORY_FILE = ".elseql_history"


class DebugPrinter:
    def write(self, s):
        print(s)


class ElseShell(Cmd):

    prompt = "elseql> "
    port = DEFAULT_PORT
    creds = None
    debug = False
    query = False

    def __init__(self, port, debug):
        Cmd.__init__(self)

        self.settable.update({
            "prompt": "Set command prompt",
            "port": "Set service [host:]port",
            "creds": "Set credentials (user:password)",
            "debug": "Set debug mode",
            "query": "Display query before results"
        })

        if readline:
            path = os.path.join(os.environ.get('HOME', ''), HISTORY_FILE)
            self.history_file = os.path.abspath(path)
        else:
            self.history_file = None

        self.debug = debug
        self.port = port
        self.init_search()

    def init_search(self):
        self.search = ElseSearch(self.port, self.debug)

        if self.search.host:
            print("connected to", self.search.host)
        else:
            print("not connected")

    def _onchange_port(self, old=None, new=None):
        self.port = new
        self.init_search()

    def _onchange_creds(self, old=None, new=None):
        print("change creds to", new)

        self.creds = new.split(":", 1)
        print("creds:", self.creds)
        self.init_search()

    def _onchange_debug(self, old=None, new=None):
        self.debug = new
        self.search.debug = self.debug

    def _onchange_query(self, old=None, new=None):
        self.query = new
        self.search.print_query = self.query

    def getargs(self, line):
        return shlex.split(str(line.decode('string-escape')))

    def get_boolean(self, arg):
        return arg and [v for v in ['t', 'y', 'on', '1'] if arg.startswith(v)] != []

    def do_version(self, line):
        print()
        print("elseql %s - you know, for query" % __version__)
        print("es version:", self.search.get_version())
        print()

    def do_keywords(self, line):
        print(self.search.get_keywords())

    def do_mapping(self, line):
        "mapping [index-name]"
        mapping = self.search.get_mapping()

        if line == "--list":
            for k in mapping:
                print(k)
        elif line:
            pprint(mapping[line])
        else:
            pprint(mapping)

    def do_select(self, line):
        self.search.search('select ' + line)

    def do_explain(self, line):
        self.search.search(line, explain=True)

    def do_validate(self, line):
        self.search.search(line, validate=True)

    def do_EOF(self, line):
        "Exit shell"
        return True

    def do_shell(self, line):
        "Shell"
        os.system(line)

    #
    # aliases
    #
    do_describe = do_mapping

    #
    # override cmd
    #

    def emptyline(self):
        pass

    def onecmd(self, s):
        try:
            return Cmd.onecmd(self, s)
        except NotImplementedError as e:
            print(e.message)
        except:
            traceback.print_exc()
        return False

    def default(self, line):
        line = line.strip()
        if line and line[0] in ['#', ';']:
            return False
        else:
            return Cmd.default(self, line)

    def completedefault(self, test, line, beginidx, endidx):
        list = []

        for k in self.search.get_keywords():
            if k.startswith(test):
                list.append(k)

        return list

    def preloop(self):
        if self.history_file and os.path.exists(self.history_file):
            try:
                readline.read_history_file(self.history_file)
            except:
                print("can't read history file")

    def postloop(self):
        if self.history_file:
            readline.set_history_length(100)
            readline.write_history_file(self.history_file)

        print("Goodbye!")


def run_command():
    import sys

    args = sys.argv
    args.pop(0)  # drop progname
    debug = False

    port = DEFAULT_PORT

    while args:
        if args[0][0] == '-':
            arg = args.pop(0)

            if arg.startswith('--port=') or arg.startswith('--host='):
                port = arg[7:]

            elif arg == '--debug':
                debug = True

            elif arg == '--':
                break

            else:
                print("invalid argument ", arg)
                return 1
        else:
            break

    ElseShell(port, debug).cmdloop()


if __name__ == "__main__":
    run_command()
