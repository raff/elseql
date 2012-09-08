#!/usr/bin/env python

from requests.defaults import defaults as requests_defaults
from requests.exceptions import ConnectionError

from parser import ElseParser, ElseParserException
import rawes
import pprint

class DebugPrinter:
    def write(self, s):
        print s

DEFAULT_PORT='localhost:9200'

class ElseSearch(object):

    def __init__(self, port=None, debug=False):
        self.debug = debug

        if debug:
            requests_defaults['verbose'] = DebugPrinter()

        self.es = None

        if port:
            try:
                self.es = rawes.Elastic(port)
            except ConnectionError, err:
                print "cannot connect to", port
                print err
                return

        if not self.es:
            self.debug = True

    def search(self, query):
        try:
            request = ElseParser.parse(query)
        except ElseParserException, err:
            print err.pstr
            print " "*err.loc + "^\n"
            print "ERROR: %s" % err
            return 1

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

        if self.debug:
            print "REQUEST: ", pprint.pformat(data)

        if self.es:
            try:
                result = self.es.get(request.index + '/_search', data=data)
            except ConnectionError, err:
                print "cannot connect to", self.es.url
                print err
                return

            if 'hits' in result:
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
