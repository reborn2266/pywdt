import time
from pywdt import *

class CrashedWorker(object):
   def __init__(self, wdt):
      self.wdt = wdt

   def working(self):
      enter_time = time.time()
      while True:
         print "[WORKER] running"
         time.sleep(2)
         raise Exception

   def destroy_working(self):
      print "[WORKER] destroy"

def hello():
   print "hello"

wdt = Watchdog(5, hello)
w = CrashedWorker(wdt)
wdt.start()
print "[WDT] restart"
w.working()
