import subprocess
from neo4j import GraphDatabase
import time
import os

def alterPassword(tx):
    tx.run("`ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO '12345'`")


dir_path = os.path.dirname(os.path.realpath(__file__))
head, _ = os.path.split(dir_path)
dir_path = os.path.join(head, "app/resources/neoServer/bin/neo4j")

def openNeo4j():
    print("--------------------------NEO--------------------")
    global neo4j
    global neo
    subprocess.Popen(dir_path + "-admin set-initial-password 12345", shell=True)
    neo4j = subprocess.Popen(dir_path + " console", shell=True)
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345"
    while 1:
        try:
            neo = GraphDatabase.driver(uri, auth=(user, password))
            return neo
        except Exception:
            print("---- connection error ----")
            time.sleep(1)

def closeNeo4j():
    if neo4j is not None:
        neo4j.terminate()
        print("---------------------------------------------terminate---------------------------------------------")
        time.sleep(1)
        if neo4j.returncode is None:
            # It has not terminated. Kill it.
            neo4j.kill()
            print("---------------------------------------------kill---------------------------------------------")