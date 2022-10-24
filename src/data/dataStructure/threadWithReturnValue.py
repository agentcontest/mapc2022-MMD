from threading import Thread
import concurrent.futures
import warnings

class ThreadWithReturnValue(Thread):
    """
    Thread which gives back the return value.
    """

    def __init__(self, group=None, target=None, name=None,
        args=(), kwargs={}) -> None:

        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        warnings.filterwarnings("ignore")

        try:
            if self._target is not None:
                self._return = self._target(*self._args, **self._kwargs)
        except concurrent.futures._base.CancelledError:
            pass
    
    def join(self, *args):
        Thread.join(self, *args)
        return self._return