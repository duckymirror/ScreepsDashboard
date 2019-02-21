from datetime import datetime
from elasticsearch import Elasticsearch
import json
import time

from screepsdashboard import app

def query_records(query, start_at = 'now-1m', max_records=100, order='asc', default_field="_all"):
    host = app.config.get('es_host', 'localhost')
    es = Elasticsearch([host])
    index = app.config.get('es_index_prefix', 'screepsdash-%s-' % (app.config['screeps_user'].lower(),))
    results = es.search(index="%sconsole*" % (index), doc_type='log', body={
      "size": max_records,
      "query": {
        "bool" : {
            "must": [
                {"query_string": {
                  "default_field": default_field,
                  "default_operator": "AND",
                  "query": query
                }}
            ],
            "filter" : {
                "range" : {
                    "timestamp" : {
                      "gt": start_at
                    }
                }
            }
        }
      },
      "sort": [
        {
          "timestamp": {
            "order": order
          }
        }
      ]
    })['hits']
    messages = []
    for hit in results['hits']:
      record = hit['_source']

      if '.' in record['timestamp']:
          timeformat = "%Y-%m-%dT%H:%M:%S.%f"
      else:
          timeformat = "%Y-%m-%dT%H:%M:%S"

      if isinstance(start_at, datetime):
          row_time = datetime.strptime(record['timestamp'], timeformat)
          if row_time < start_at:
              continue
          start_at = row_time
      else:
          start_at = datetime.strptime(record['timestamp'], timeformat)

      messages.append(record)
    return messages
