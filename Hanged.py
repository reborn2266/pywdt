import time
from pywdt import *

class HangedWorker(object):
   def __init__(self, wdt):
      self.wdt = wdt

   def working(self):
      enter_time = time.time()
      while True:
         print "[WORKER] running"
         time.sleep(1)
         #self.wdt.kick()

   def destroy_working(self):
      print "[WORKER] destroy"

wdt = Watchdog(5)
w = HangedWorker(wdt)
wdt.start()
print "[WDT] restart"
w.working()
