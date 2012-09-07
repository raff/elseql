#!/usr/bin/env python

from requests.defaults import defaults as requests_defaults
from requests.exceptions import ConnectionError

from parser import Parser, ParserException
import rawes
import pprint

class DebugPrinter:
    def write(self, s):
        print s

def main(args):
    progname = args.pop(0)
    debug = False
    es_port = 'localhost:9200'

    while args:
        if args[0][0] == '-':
            arg = args.pop(0)

            if arg.startswith('--port=') or arg.startswith('--host='):
                es_port = arg[7:]

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

    try:
        request = Parser.parse(query)
    except ParserException, err:
        print err.pstr
        print " "*err.loc + "^\n"
        print "ERROR: %s" % err
        return 1

    if debug:
        requests_defaults['verbose'] = DebugPrinter()

    if request.query:
        data = { 'query': { 'query_string': { 'query': str(request.query) } } }
    else:
        data = { 'query': { 'match_all': {} } } 

    if request.filter:
        data['filter'] = { 'query_string': { 'query': str(request.filter) } }

    if request.facets:
        data['facets'] = { f: { "terms": { "field": f } } for f in request.facets }

    if request.fields:
        fields = request.fields
        if len(fields) == 1:
            if fields[0] == '*':
                # all fields
                pass
            elif fields[0] == 'count(*)':
                # TODO: only get count
                pass
        else:
            data['fields'] = [x for x in request.fields]

    if request.order:
        data['sort'] = [{x[0]:x[1]} for x in request.order]

    if request.limit:
        if len(request.limit) > 1:
            data['from'] = request.limit.pop(0)

        data['size'] = request.limit[0]
    else:
        data['size'] = 100

    if debug or not es_port:
        print "REQUEST: ", pprint.pformat(data)

    if es_port:
        try:
            es  = rawes.Elastic(es_port)
            result = es.get(request.index + '/_search', data=data)
        except ConnectionError, err:
            print "cannot connect to", es_port
            print err
            return

        if result['hits']['hits']:
            if 'fields' in data:
                fields = data['fields']

                print fields

                for _ in result['hits']['hits']:
                    print [_.get(x) or _['fields'].get(x) for x in fields]
            else:
                print result['hits']['hits'][0]['_source'].keys()

                for _ in result['hits']['hits']:
                    print _['_source'].values()

        print ""
        print "total: ", result['hits']['total']

        if 'facets' in result:
            for facet in result['facets']:
                print ""
                print facet, 'count'

                for _ in result['facets'][facet]['terms']:
                    print _['term'], _['count']

    return 0

def run_command():
    import sys
    main(sys.argv)

if __name__ == "__main__":
    run_command()
