## @package scripts
#  Calculation of thread quantity and creation of thread pool
#
#  More details.
import os
from concurrent.futures.thread import ThreadPoolExecutor
import multiprocessing

numThreads = multiprocessing.cpu_count() // 2
print("Threds:",int(numThreads))
pool = ThreadPoolExecutor(max_workers=numThreads)

## This function calls and executes a function in a thread.
#  @param fc Is the name of the function that will be called.
#  @param args Are the arguments that the function will or not use.
def do(fc, args=None):
    if args:
        future = pool.submit(fc, args)
    else:
        future = pool.submit(fc)
    return future

