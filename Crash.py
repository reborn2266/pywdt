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

wdt = Watchdog(5)
w = CrashedWorker(wdt)
wdt.start()
while True:
   print "[WDT] restart"
   w.working()
