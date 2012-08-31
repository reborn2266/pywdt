#!/usr/bin/env python
import sys, time, os, signal, threading, fcntl

class TimeoutChecker(threading.Thread):
   def __init__(self, wdt, timeout):
      super(TimeoutChecker, self).__init__()
      self.wdt = wdt
      self.timeout = timeout
      self.is_stop = False

   def stop(self):
      self.is_stop = True

   def run(self):
      while True:
         if self.is_stop:
            break
         print "[WDT] check timeout"
         if (time.time() - self.wdt.last_kicked_time) > self.timeout:
            print "[WDT] timeout"
            self.wdt.is_timeout = True
         else:
            self.wdt.is_timeout = False
         time.sleep(1)

class KickedChecker(threading.Thread):
   def __init__(self, wdt):
      super(KickedChecker, self).__init__()
      self.wdt = wdt
      self.is_stop = False

   def stop(self):
      self.is_stop = True

   def run(self):
      while True:
         if self.is_stop:
            break
         # set READ side nonblock
         # we do this beacuse we want to check more status not just block in readline
         # Think about it: if worker not kick and blocked in readline, how can we break this loop?
         fcntl.fcntl(self.wdt.pipe_rfd, fcntl.F_SETFL, os.O_NONBLOCK)
         data = None

         try:
            data = self.wdt.pipe_r.readline()
         except IOError:
            # since we use nonblock IO, this might happen when no data there
            pass

         if data:
            #print data
            print "[WDT] kicked"
            self.wdt.last_kicked_time = time.time()

         # take a break
         time.sleep(1)

class Watchdog(object):
   def __init__(self, worker, period=10):
      self.worker = worker
      self.check_period = period
      self.pipe_rfd, self.pipe_wfd = os.pipe()
      self.pipe_r, self.pipe_w = os.fdopen(self.pipe_rfd, 'r', 0), os.fdopen(self.pipe_wfd, 'w', 0)
      self.got_sigterm = False

   def receive_sigterm(self):
      return self.got_sigterm

   def start(self):
      def on_term(sig, func=None):
         self.got_sigterm = True

      signal.signal(signal.SIGTERM, on_term)
      signal.signal(signal.SIGINT, on_term)
      signal.signal(signal.SIGQUIT, on_term)

      try:
         self.worker_pid = os.fork()
      except OSError:
         print "Fork failed"
         raise OSError

      if self.worker_pid == 0:
         # Mmm, I am child, need to be a worker...
         self.pipe_r.close()
         while True:
            self.worker.working()
            # kick watchdog
            print >>self.pipe_w, "Y"
            self.pipe_w.flush()
            print "[WORKER WRAPPER] kick wdt"
      else:
         # I am parent, need to take care the status of worker and handle when bad things happen
         self.pipe_w.close()
         self.is_timeout = False
         self.last_kicked_time = time.time()
         self.timeout_checker = TimeoutChecker(self, self.check_period)
         self.kicked_checker = KickedChecker(self)
         self.timeout_checker.start()
         self.kicked_checker.start()

         while True:
            if self.is_timeout or self.got_sigterm:
               print "[WDT] stop checkers"
               self.timeout_checker.stop()
               self.kicked_checker.stop()
               self.timeout_checker.join()
               self.kicked_checker.join()
               print "[WDT] kill worker"
               os.kill(self.worker_pid, signal.SIGKILL)
               os.waitpid(self.worker_pid, 0)
               break
            else:
               time.sleep(1)

class Worker(object):
    def working(self):
      enter_time = time.time()
      while True:
         print "[WORKER] running"
         time.sleep(1)
         if (time.time() - enter_time) > 3:
            break

    def destroy_working(self):
        print "[WORKER] destroy"

if __name__ == "__main__":
   w = Worker()
   wdt = Watchdog(w, 5)
   wdt.start()
   while True:
      if not wdt.receive_sigterm():
         # should not be here, means we need restart a watchdog
         wdt = ERSWatchdog(w, 5)
         wdt.start()
      else:
         break

