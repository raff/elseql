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

def _csval(v):
    if not v:
        return ''

    if not isinstance(v, basestring):
        return str(v)

    if v.isalnum():
        return v

    return '"%s"' % v.replace('"', '""')

def _csvline(l):
    return ",".join([_csval(v) for v in l])

class ElseSearch(object):

    def __init__(self, port=None, debug=False):
        self.debug = debug

        if debug:
            requests_defaults['verbose'] = DebugPrinter()

        self.es = None

        if port:
            try:
                self.es = rawes.Elastic(port)
                self.get_mapping()
            except ConnectionError, err:
                print "cannot connect to", port
                print err

        if not self.es:
            self.debug = True

    def get_mapping(self):
        try:
            self.mapping = self.es.get("_mapping")
            self.keywords = []
        except ConnectionError, err:
            print "cannot connect to", self.es.url
            print err

    def get_keywords(self):
        if self.keywords:
            return self.keywords

        keywords = ['facets', 'filter', 'from', 'where', 'in', 'between', 'like', 'order by', 'limit', 'and', 'or', 'not']

        if not self.mapping:
            return sorted(keywords)

        def add_properties(plist, doc):
            if 'properties' in doc:
                props = doc['properties']

                for p in props:
                    plist.append(p)  # property name
                    add_properties(plist, props[p])

        keywords.extend(['_score', '_all'])

        for i in self.mapping:
            keywords.append(i)  # index name

            index = self.mapping[i]

            for t in index:
                keywords.append(t)  # document type

                document = index[t]

                if '_source' in document:
                    source = document['_source']
                    if not 'enabled' in source or source['enabled']:
                        keywords.append('_source')  # _source is enabled by default

                add_properties(keywords, document)

        self.keywords = sorted(set(keywords))
        return self.keywords

    def search(self, query, explain=False):
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

        if explain:
            data['explain'] = True

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
                    data['fields'] = [fields[0]]
            else:
                data['fields'] = [x for x in fields]

        if request.order:
            data['sort'] = [{x[0]:x[1]} for x in request.order]

        if request.limit:
            if len(request.limit) > 1:
                data['from'] = request.limit.pop(0)

            data['size'] = request.limit[0]

        if self.debug:
            print "REQUEST: ", pprint.pformat(data)

        if self.es:
            try:
                result = self.es.get(request.index + '/_search', data=data)
            except ConnectionError, err:
                print "cannot connect to", self.es.url
                print err
                return

            #print result

            if 'hits' in result:
                if 'fields' in data:
                    fields = data['fields']

                    print _csvline(fields)

                    for _ in result['hits']['hits']:
                        print _csvline([_.get(x) or _['fields'].get(x) for x in fields])
                else:
                    if result['hits']['hits']:
                        print _csvline(result['hits']['hits'][0]['_source'].keys())

                    for _ in result['hits']['hits']:
                        print _csvline([_csval(x) for x in _['_source'].values()])

                print ""
                print "total: ", result['hits']['total']

            if 'facets' in result:
                for facet in result['facets']:
                    print ""
                    print "%s,count" % _csval(facet)

                    for _ in result['facets'][facet]['terms']:
                        t = _['term']
                        c = _['count']
                        print "%s,%s" % (_csval(t), c)
