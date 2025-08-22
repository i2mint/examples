import numpy as np
from examples.live_chunking.live_chunking_utils import go_live


def max(chk):
    return np.max(np.absolute(chk))


def std(chk):
    return np.std(chk)


def min(chk):
    return np.min(np.absolute(chk))


configs = dict(chk_size=2048, chk_step=2048, interval_length=10)

if __name__ == "__main__":
    go_live([max, std, min], **configs)
