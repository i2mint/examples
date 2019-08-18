import time
import struct
import os
from io import BytesIO
import time

import numpy as np
import soundfile as sf
from IPython.display import Audio
import matplotlib.pylab as plt

DFLT_CHK_SIZE_BYTES = 2 * 2048 * 21
DFLT_SR = 44100


class Sound:
    """Holds a waveform and sample rate and displays nicely (and so that sound can be played)"""

    def __init__(self, wf, sr=DFLT_SR):
        self.wf = wf
        self.sr = sr

    def display(self, autoplay=False, **kwargs):
        plt.figure(figsize=(16, 5))
        plt.plot(self.wf)
        return Audio(data=self.wf, rate=self.sr, autoplay=autoplay, **kwargs)


class MockAudioBuffer:
    """A pretend "sensor buffer". It sources from wav files and returns fixed sized 'time-stamped chunks' on read.
    Time-stamped chunks are given as (session_utc_time, block_byte_offset, data)"""
    header_size = 44

    def __init__(self, source, chk_size_bytes=DFLT_CHK_SIZE_BYTES):
        assert isinstance(source, str) and source.endswith('.wav'), \
            "source must be a wav file with 44-byte header and PCM_16 subtype"
        self.source = source
        self.chk_size = chk_size_bytes
        self.fp = None
        self.sr = None

    def __enter__(self):
        self.byte_offset = 0
        self.start_time = time.time()
        self.fp = open(self.source, "rb")
        header_bytes = self.fp.read(self.header_size)
        self.sr = struct.unpack('<L', header_bytes[24:28])[0]
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        fp = self.fp
        self.fp = None
        return fp.close()

    def read(self):
        chk = self.fp.read(self.chk_size)
        chk_size = len(chk)
        if chk_size == self.chk_size:
            current_byte_offset = self.byte_offset
            self.byte_offset += chk_size
            return self.start_time, current_byte_offset, chk
        else:
            return self.start_time, None, None


def do_something_with_stream(stream, something):
    """Reads through a t = (session, block, data) timestamped chunks stream and calls the function 'something' on t."""
    with stream as source:
        print(f"source: {source.source}, sr: {source.sr}")
        while True:
            session, byte_offset, chk = source.read()  # read a chunk
            if chk is not None:
                something(session, byte_offset, chk)
            else:
                break
