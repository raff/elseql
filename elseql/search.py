#!/usr/bin/env python

from __future__ import print_function

from requests.defaults import defaults as requests_defaults
from requests.exceptions import ConnectionError

from parser import ElseParser, ElseParserException
import rawes
import pprint

class DebugPrinter:
    def write(self, s):
        print(s)

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
    try:
        return ",".join([_csval(v).encode("utf-8") for v in l])
    except UnicodeDecodeError:
        raise Exception("UnicodeDecodeError for %s" % l)

class ElseSearch(object):

    def __init__(self, port=None, debug=False):
        self.debug = debug
        self.print_query = False

        #if self.debug:
        #    requests_defaults['verbose'] = DebugPrinter()

        self.es = None
        self.mapping = None
        self.keywords = None
        self.host = None

        if port:
            try:
                self.es = rawes.Elastic(port)
                self.get_mapping()
            except ConnectionError as err:
                print("init: cannot connect to", port)
                print(err)

        if not self.es:
            self.debug = True

    def get_mapping(self):
        if self.mapping:
            return self.mapping

        try:
            self.mapping = self.es.get("_mapping")
            self.keywords = []
            self.host = self.es.url
        except ConnectionError as err:
            print("mapping: cannot connect to", self.es.url)
            print(err)

        return self.mapping

    def get_keywords(self):
        if self.keywords:
            return self.keywords

        keywords = ['facets', 'filter', 'query', 'exist', 'missing', 'script', 
                'from', 'where', 'in', 'between', 'like', 'order by', 'limit', 'and', 'or', 'not']

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

    def search(self, query, explain=False, validate=False):
        try:
            request = ElseParser.parse(query)
        except ElseParserException as err:
            print(err.pstr)
            print(" "*err.loc + "^\n")
            print("ERROR:", err)
            return 1

        params = {}
        data_fields = None

        if request.query:
            data = { 'query': { 'query_string': { 'query': str(request.query), 'default_operator': 'AND' } } }
        else:
            data = { 'query': { 'match_all': {} } } 

        if explain:
            data['explain'] = True

        if request.filter:
            filter = request.filter

            if filter.name == 'query':
                data['filter'] = { 'query': { 'query_string': { 'query': str(filter), 'default_operator': 'AND' } } }
            else:
                data['filter'] = { filter.name: { 'field': str(filter) } }

        if request.facets:
            # data['facets'] = { f: { "terms": { "field": f } } for f in request.facets }  -- not in python 2.6
            data['facets'] = dict((f, { "terms": { "field": f } }) for f in request.facets)

        if request.script:
            data['script_fields'] = { request.script[0]: { "script": request.script[1] } }

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
                    data_fields = data['fields'] = [fields[0]]
            else:
                data_fields = data['fields'] = [x for x in fields]

        if request.order:
            data['sort'] = [{x[0]:x[1]} for x in request.order]

        if request.limit:
            qfrom = None
            qsize = None

            if len(request.limit) > 1:
                qfrom = request.limit.pop(0)

            qsize = request.limit[0]

            if qfrom > 0:
                data['from'] = qfrom
                data['size'] = qsize

            elif qfrom < 0:
                #
                # limit -1, 1000 => scan request, 1000 items at a time
                #
                params.update({'search_type': 'scan', 'scroll': '10m', 'size': qsize})

            else:
                data['size'] = qsize

        if validate:
            command = '/_validate/query' 
            params.update({'pretty': True, 'explain': True})

            # validate doesn't like "query"
            if 'query' in data:
                q = data.pop('query')
                data.update(q)

        #
        # this is actually {index}/{document-id}/_explain
        #
        #elif explain:
        #    command = '/_explain' 
        #    params.update({'pretty': True})

        else:
            command = '/_search'

        command_path = request.index.replace(".", "/") + command

        if self.debug:
            print()
            print("GET", command_path, params or '')
            print("  ", pprint.pformat(data))
            params.update({'pretty': True})

        if self.print_query:
            print()
            print("; ", _csval(query))
            print()

        total = None
        print_fields = True
	do_query = True

        while self.es and do_query:
            try:
                result = self.es.get(command_path, params=params, data=data)
            except ConnectionError as err:
                print("cannot connect to", self.es.url)
                print(err)
                return

            if self.debug:
                print()
                print("RESPONSE:", pprint.pformat(result))
                print()

            if '_scroll_id' in result:
                # scan/scroll request
                params['scroll_id'] = result['_scroll_id']

                if 'search_type' in params:
		    params.pop('search_type')
                    command_path = '_search/scroll'
	    else:
		# done
		do_query = False

            if 'valid' in result:
                if 'explanations' in result:
                    for e in result['explanations']:
                        print()
                        for k,v in e.iteritems():
                            print(k,':',v)
                else:
                    print("valid:", result['valid'])
                return

            if 'error' in result:
                print("ERROR:", result['error'])
                return

            if 'shards' in result and 'failures' in result['_shards']:
                failures = result['_shards']['failures']
                for f in failures: print("ERROR:", f['reason'])
                return

            if 'hits' in result:
            	total = result['hits']['total']

                if data_fields:
                    if print_fields:
                        print_fields = False
                        print(_csvline(data_fields))

                    for _ in result['hits']['hits']:
                        result_fields = _['fields'] if 'fields' in _ else {}
                        print(_csvline([_.get(x) or result_fields.get(x) for x in data_fields]))
                else:
		    if result['hits']['hits']:
                       if print_fields:
                            print_fields = False
                            print(_csvline(result['hits']['hits'][0]['_source'].keys()))
		    else:
			do_query = False

                    for _ in result['hits']['hits']:
                        print(_csvline([_csval(x) for x in _['_source'].values()]))

            if 'facets' in result:
                for facet in result['facets']:
                    print()
                    print("%s,count" % _csval(facet))

                    for _ in result['facets'][facet]['terms']:
                        t = _['term']
                        c = _['count']
                        print("%s,%s" % (_csval(t), c))

            if do_query and self.debug:
                print()
                print("GET", command_path, params or '')
                print("  ", pprint.pformat(data))

        if total is not None:
            print()
            print("total: ", total)
