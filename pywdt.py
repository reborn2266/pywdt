#!/usr/bin/env python
import sys, time, os, signal, threading, fcntl

class TimeoutChecker(threading.Thread):
   def __init__(self, wdt, timeout):
      super(TimeoutChecker, self).__init__()
      self.wdt = wdt
      self.timeout = timeout

   def run(self):
      while True:
         if self.wdt.is_stop:
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

   def run(self):
      while True:
         if self.wdt.is_stop:
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
   def __init__(self, period=10):
      self.check_period = period
      self.reset_members(self.check_period)

   def reset_members(self, period):
      self.pipe_rfd, self.pipe_wfd = os.pipe()
      self.pipe_r, self.pipe_w = os.fdopen(self.pipe_rfd, 'r', 0), os.fdopen(self.pipe_wfd, 'w', 0)
      self.got_sigterm = False
      self.is_stop = False

   def receive_sigterm(self):
      return self.got_sigterm

   def start_once(self):
      try:
         self.worker_pid = os.fork()
      except OSError:
         print "Fork failed"
         raise OSError

      if self.worker_pid == 0:
         # Mmm, I am child, need to be a worker...
         self.pipe_r.close()
         return 0
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
               self.is_stop = True
               self.timeout_checker.join()
               self.kicked_checker.join()
               print "[WDT] kill worker"
               os.kill(self.worker_pid, signal.SIGKILL)
               os.waitpid(self.worker_pid, 0)
               self.pipe_r.close()
               if self.is_timeout:
                  return 1
               elif self.got_sigterm:
                  return 2
            else:
               time.sleep(1)

   def start(self):
      def on_term(sig, func=None):
         self.got_sigterm = True

      signal.signal(signal.SIGTERM, on_term)
      signal.signal(signal.SIGINT, on_term)
      signal.signal(signal.SIGQUIT, on_term)

      while True:
         ret = self.start_once()
         if ret == 0:
            break
         elif ret == 1:
            self.reset_members(self.check_period)
         else:
            sys.exit(1)

   def kick(self):
      print >>self.pipe_w, "Y"
      self.pipe_w.flush()

class Worker(object):
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

if __name__ == "__main__":
   wdt = Watchdog(5)
   w = Worker(wdt)
   wdt.start()
   while True:
      print "[WDT] restart"
      w.working()
