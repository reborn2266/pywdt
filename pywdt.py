#!/usr/bin/env python
import sys, time, os, signal, threading, fcntl

class TimeoutChecker(threading.Thread):
   def __init__(self, wdt, timeout):
      super(TimeoutChecker, self).__init__()
      self.wdt = wdt
      self.timeout = timeout

   def run(self):
      while True:
         with self.wdt.lock:
            is_stop = self.wdt.is_stop
            last_kicked_time = self.wdt.last_kicked_time
         if is_stop:
            break
         print "[WDT] check timeout"
         if (time.time() - last_kicked_time) > self.timeout:
            print "[WDT] timeout"
            with self.wdt.lock:
               self.wdt.is_timeout = True
         else:
            with self.wdt.lock:
               self.wdt.is_timeout = False
         time.sleep(1)

class KickedChecker(threading.Thread):
   def __init__(self, wdt):
      super(KickedChecker, self).__init__()
      self.wdt = wdt

   def run(self):
      while True:
         with self.wdt.lock:
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
            with self.wdt.lock:
               self.wdt.last_kicked_time = time.time()

         # take a break
         time.sleep(1)

class Watchdog(object):
   def __init__(self, period=10, before_restart=None):
      self.check_period = period
      self.before_restart = before_restart
      self.reset_members(self.check_period)

   def reset_members(self, period):
      self.pipe_rfd, self.pipe_wfd = os.pipe()
      self.pipe_r, self.pipe_w = os.fdopen(self.pipe_rfd, 'r', 0), os.fdopen(self.pipe_wfd, 'w', 0)
      self.got_sigterm = False
      self.is_stop = False
      self.lock = threading.Lock()

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
            with self.lock:
               is_timeout = self.is_timeout
               got_sigterm = self.got_sigterm
            if is_timeout or got_sigterm:
               print "[WDT] stop checkers"
               with self.lock:
                  self.is_stop = True
               self.timeout_checker.join()
               self.kicked_checker.join()
               print "[WDT] kill worker"
               os.kill(self.worker_pid, signal.SIGKILL)
               os.waitpid(self.worker_pid, 0)
               self.pipe_r.close()

               if got_sigterm:
                  return 2
               elif is_timeout:
                  return 1
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
            # if there is user defined clean up, do it
            if (self.before_restart != None):
               self.before_restart()
            self.reset_members(self.check_period)
         else:
            sys.exit(1)

   def kick(self):
      print >>self.pipe_w, "Y"
      self.pipe_w.flush()

if __name__ == "__main__":
   pass
