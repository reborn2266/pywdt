import time
from pywdt import *

class Worker(object):
   def __init__(self, wdt):
      self.wdt = wdt

   def working(self):
      print self.L
      self.L = None
      enter_time = time.time()
      while True:
         print "[WORKER] running"
         time.sleep(1)

   def destroy_working(self):
      print "[WORKER] destroy"

L = [1, 2, 3]
wdt = Watchdog(5)
w = Worker(wdt)
w.L = L
wdt.start()
print "[WDT] restart"
print w.L
w.working()
