#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import subprocess
import sys
import time

from elasticsearch import Elasticsearch
from scripts.pcVariables import essPath

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

    #openES()
    #time.sleep(5)
    execute_from_command_line(sys.argv)
    #closeES()

esPath = essPath

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


es = Elasticsearch()

if __name__ == '__main__':
    main()
