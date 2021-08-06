from typing import Iterable, Callable
import numpy as np
from examples.synthetic_sounds.util import (
    seeds_to_wfs,
    seed_to_wf_chk,
    DFLT_SEEDS,
    DFLT_CHUNKER,
    chk_tag_gen,
    frame_annots_to_chk_annots,
)
from sklearn.decomposition import PCA
from sklearn.svm import SVC


def make_frequency_groups(seeds: Iterable, chk_size: int, class_sep: float):
    freq_dict = {}
    for seed in sorted(list(set(seeds))):
        freq_dict[seed] = 100 + class_sep * 1000 * len(freq_dict)

    wfs = seeds_to_wfs(seeds, chk_size, freq_dict, seed_to_wf_chk)

    annots = []
    for idx, wf in enumerate(wfs):
        annots.append((np.array([chk_size * idx, chk_size * (idx + 1)]), seeds[idx]))

    return wfs, annots


def test_classification_model(
    seeds: Iterable = None,
    n_classes: int = None,
    chk_size: int = 2048 * 5,
    class_sep: float = 1.0,
    chunker=DFLT_CHUNKER,
    chunker_chk_size: int = 1024,
    featurizer: Callable = PCA,
    model: Callable = SVC,
):
    if n_classes is None and seeds is None:
        raise AttributeError("Either seeds or n_classes needs to be specified!")
    elif seeds is None:
        seeds = list(DFLT_SEEDS[:n_classes])
    elif n_classes is None:
        pass
    else:
        assert len(set(seeds)) == n_classes

    wfs, annots = make_frequency_groups(seeds, chk_size, class_sep)

    chks, tags = zip(*chk_tag_gen(wfs, seeds, chunker=chunker(chunker_chk_size)))

    featurizer = featurizer().fit(chks, tags)
    fvs = featurizer(chks)

    model = model().fit(fvs, tags)
    scores = model(fvs)

    chk_annots = frame_annots_to_chk_annots(annots, chunker_chk_size)
    classification_wf = np.hstack(wfs)

    return scores, chk_annots, classification_wf
