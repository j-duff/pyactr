"""
Simple temporal module based on Taatgen, van Rijn & Anderson (2007).
Values of LHS checks to the temporal buffer are always evaluated as a threshold, not an exact match.
TO DO: Test for accurate replication of Taatgen et al. model results.
"""

import pyactr.chunks as chunks
import pyactr.utilities as utilities
from pyactr.utilities import ACTRError
import pyactr.buffers as buffers
import numpy as np
import warnings

Event = utilities.Event
roundtime = utilities.roundtime

class TemporalBuffer(buffers.Buffer):
    """
    Temporal buffer.
    """

    def __init__(self, time_start=0.011, time_mult=1.1, time_noise=0.015, default_harvest=None):
        buffers.Buffer.__init__(self, default_harvest, data=None)
        self.start = time_start
        self.mult = time_mult
        self.noise = time_noise

    @property
    def default_harvest(self):
        """
        Default harvest of goal buffer.
        """
        return self.dm

    @default_harvest.setter
    def default_harvest(self, value):
        try:
            self.dm = value
        except ValueError:
            raise ACTRError('The default harvest set in the temporal buffer is not a possible declarative memory')

    def add(self, elem):
        """
        If the buffer has a chunk, it clears current buffer (into the memory associated with the temporal buffer). It adds a new chunk, specified as elem. Decl. memory is specified as default_harvest.
        """
        super().add(elem)

    def clear(self, time=0):
        """
        Clear buffer, add the cleared chunk into decl. memory. Decl. memory is specified as default_harvest when buffer is initialized
        """
        if self._data:
            self.dm.add(self._data.pop(), time)

    def test(self, state, inquiry):
        """
        Is current state busy/free/error?
        """
        return getattr(self, state) == inquiry

    def retrieve(self, otherchunk, actrvariables=None):
        """
        Retrieve a chunk. This is not possible in goal buffer, so an error is raised.
        """
        raise utilities.ACTRError(
            "An attempt to retrieve the chunk '%s' from temporal; retrieving from temporal is not possible" % otherchunk)

    def create(self, otherchunk, actrvariables=None):
        """
        Create (aka set) a chunk in temporal buffer.
        """
        try:
            mod_attr_val = {x[0]: utilities.check_bound_vars(actrvariables, x[1]) for x in
                            otherchunk.removeunused()}  # creates dict of attr-val pairs according to otherchunk
        except utilities.ACTRError as arg:
            raise utilities.ACTRError("Setting the buffer using the chunk '%s' is impossible; %s" % (otherchunk, arg))

        if len(mod_attr_val) > 1 or "ticks" not in mod_attr_val:
            raise utilities.ACTRError("Chunks in the temporal buffer must specify the attribute ticks and nothing else")
        elif mod_attr_val["ticks"].values != "0":
            raise utilities.ACTRError("The temporal buffer must begin counting at 0")

        new_chunk = chunks.Chunk(utilities.TEMPORAL, **mod_attr_val)  # creates new chunk

        self.add(new_chunk)  # put chunk using add

    def tick(self, time):
        """
        Process that generates events for temporal incrementing so long as the temporal buffer has a chunk in it.
        """
        tickcount = 0
        while self._data:
            if tickcount == 0:
                lag = self.start + logistic_noise(self.noise * 5 * self.start)
            else:
                lag = self.mult * lag + logistic_noise(self.noise * self.mult * lag)
            yield Event(roundtime(time+lag), "TEMPORAL", f"Incrementing time ticks to {tickcount}")
            try:
                self.modify(chunks.Chunk(utilities.TEMPORAL, **{"ticks": str(tickcount)}))
            except KeyError:
                warnings.warn(f"The temporal buffer has been cleared, so the final scheduled tick ({tickcount}) was not logged.")
            tickcount += 1

def logistic_noise(s):
    """
    Duplicates the act-r-noise command
    :param s: scale parameter
    :return:
    """
    noise = np.random.default_rng().logistic(loc = 0, scale = s)
    return noise
