#!/usr/bin/env python

from parser import ElseParser, ElseParserException
from search import ElseSearch, DEFAULT_PORT
import rawes
import pprint

class DebugPrinter:
    def write(self, s):
        print s

def main(args):
    progname = args.pop(0)
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
                print "invalid argument ", arg
                return 1
        else:
            break

    query = " ".join(args)

    search = ElseSearch(port, debug)
    search.search(query)
    return 0

def run_command():
    import sys
    main(sys.argv)

if __name__ == "__main__":
    run_command()
