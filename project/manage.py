#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import subprocess
import sys
from scripts.esScript import closeES,openES
from scripts.neoScript import closeNeo4j,openNeo4j
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
    openES()
    openNeo4j()
    execute_from_command_line(sys.argv)
    closeES()
    closeNeo4j()


if __name__ == '__main__':
    main()
