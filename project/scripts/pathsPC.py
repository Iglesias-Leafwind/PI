import os
from concurrent.futures.thread import ThreadPoolExecutor
import multiprocessing

numThreads = multiprocessing.cpu_count()/2
print("Threds:",int(numThreads))
pool = ThreadPoolExecutor(max_workers=numThreads)

def do(fc, args=None):
    if args:
        future = pool.submit(fc, args)
    else:
        future = pool.submit(fc)
    return future

