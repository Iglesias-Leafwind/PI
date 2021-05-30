import os
from concurrent.futures.thread import ThreadPoolExecutor
import multiprocessing

numThreads = multiprocessing.cpu_count()

pool = ThreadPoolExecutor(max_workers=numThreads)

def do(fc, args=None):
    if args:
        future = pool.submit(fc, args)
    else:
        future = pool.submit(fc)
    return future

def getFolders():
    results = []
    for root, dirs, files in os.walk('/home/mar/Documents/UA/6-semester/PI/learning'):
        # for root, dirs, files in os.walk('/home/anth0nypereira'):
        array = []
        root_parts = root.split("/")


        for path in dirs:
            if path[0] != "." and len(path) > 1:
                if any(elem[0] == "." for elem in root_parts if len(elem) > 1):
                    continue
                else:
                    array = array + [path]
            else:
                continue

        for dir in array:
            results = results + [os.path.join(root, dir)]
    return results
