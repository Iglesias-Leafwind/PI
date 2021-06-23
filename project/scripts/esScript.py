## @package scripts
#  Module for ElasticSearch startup and closure
#
#  More details.
from scripts.pcVariables import essPath
import subprocess
from elasticsearch import Elasticsearch
import time

esPath = essPath
## Method to initialize elasticSearch
def open_es():
    global elasticsearchClient
    global es
    elasticsearchClient = subprocess.Popen(esPath)
    print("------------------ES----------------------------")

    while 1:
        try:
            es = Elasticsearch()
            es.cluster.health(wait_for_status='yellow')
            return es
        except Exception:
            print("---- Trying to connect ----")
            time.sleep(1)
## Method to close elasticSearch
def close_es():
    elasticsearchClient.terminate()
    print("---------------------------------------------terminate---------------------------------------------")
    time.sleep(1)
    if elasticsearchClient.returncode is None:
        # It has not terminated. Kill it.
        elasticsearchClient.kill()
        print("---------------------------------------------kill---------------------------------------------")
