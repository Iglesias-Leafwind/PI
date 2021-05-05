#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import subprocess
import sys
import threading
import time
from elasticsearch import Elasticsearch
from elasticsearch_dsl import connections

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # x = threading.Thread(target=openES)
    # x.start()
    # x.join()
    print(connections.get_connection().cluster.health())
    execute_from_command_line(sys.argv)
    # closeES()


connections.create_connection(hosts=['localhost'])
es = Elasticsearch()

"""
# CHANGE TO YOUR PATH!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# esPath = "D:\Java\JavaEE\elasticsearch\elasticsearch-7.11.1\\bin\elasticsearch.bat"
# esPath = "/usr/share/elasticsearch/bin"
esPath = "/home/mar/Documents/UA/6-semester/PI/elasticsearch-7.12.0/bin/elasticsearch"

def openES():
    global elasticsearchClient
    elasticsearchClient = subprocess.Popen(esPath)

def closeES():
    elasticsearchClient.terminate()
    print("---------------------------------------------terminate---------------------------------------------")
    time.sleep(1)
    if elasticsearchClient.returncode is None:
        # It has not terminated. Kill it.
        elasticsearchClient.kill()
        print("---------------------------------------------kill---------------------------------------------")


"""
if __name__ == '__main__':
    main()
