elseql
======
You know, for Query
-------------------
A SQL-like command line / REPL client for ElasticSearch

### USAGE

    elseql [--debug] [--port=host:port] 

### COMMANDS

* select - see SEARCH SYNTAX
* describe [index]
* set options [on|off]
* help

### SEARCH SYNTAX

    SELECT {fields}
        [FACETS facet-fields]
        [SCRIPT script-field = 'script']
        FROM index
        [WHERE where-condition]
        [FILTER filter-condition]
        [ORDERY BY order-fields]
        [LIMIT [start,] count]

where:
    fields: '*' or comma-separated list of field names to be returned

    facet-fields: comma-separated list of fields to execute a facet query on

    script-field: name of script field, to be used in select clause
    script: ElasticSearch script

    index: index to query

    where-condition:
        {field-name} [ = != > >= < <= ] {value}
        {field-name} LIKE {value}
        {field-name} IN (value1, value2, ...)
        {field-name} BETWEEN {min-value} AND {max-value}
        NOT {where-condition}
        {where-condition} AND {where-condition}
        {where-condition} OR {where-condition}

    or where-condition:
        'query in Lucene syntax'

    filter-condition: 
        QUERY {where-condition} - query filter, same syntax as where condition
        EXIST {field-name}      - exists field filter
        MISSING {field.name}    - missing field filter

    order-fields: comma-separated list of {field-name} [ASC | DESC]

    start: start index for pagination
    count: maximum number of returned results

A special case for LIMIT start,count allows to do a "scroll" query (i.e. results will be returned in batches):

    start: -1 - enable "scroll" query
    count: batch size - the query will return {count} results (actually {count} per shard) and will be repeated until all results are returned.

This is very useful when you are expecting large result sets (or you are doing a full table scan). Note that in
"scroll" mode sort and facets are disabled.

### INSTALLATION

From pypi:

	sudo easy_install elseql
or:

	sudo pip install elseql

With python and setuptools installed:

	sudo python setup.py install

You can also run the command without installing as:

	python -m elseql.elseql

To do this you will need the pyparsing, rawes and cmd2 packages installed, that are automatically installed in the previous step.

	sudo easy_install pyparsing
	sudo easy_install rawes
        sudo easy_install cmd2

The cmd2 package add a few extra features "command-line" related features. The most useful is redirection:

	elsesql> select id,field1,field2 from index where condition > result.csv

Note that because '>' is used for redirection you'll need to use GT in the where clause insted (also available LT, GTE, LTE)

### SEE ALSO

http://elasticsearch.org/, You know, for Search
