from slang.snippers import PcaChkToFv, LdaChkToFv
from slang.chunkers import mk_chunker
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score

import numpy as np
from hum import mk_sine_wf
from typing import Iterable

DFLT_CHUNKER = mk_chunker
DFLT_FEATURIZER = {"supervised": LdaChkToFv, "unsupervised": PcaChkToFv}
DFLT_SEEDS = "abcdefghijklmnopqrstuvwxyz"


def chk_gen(wf, chunker=DFLT_CHUNKER):
    for chk in chunker(wf):
        yield chk


def wf_tag_gen(wfs, tags):
    for tup in zip(wfs, tags):
        yield tup[0], tup[1]


def chk_tag_gen(wfs, tags, chunker=DFLT_CHUNKER):
    for wf, tag in wf_tag_gen(wfs, tags):
        for chk in chunker(wf):
            yield chk, tag


def times_to_frames_range(
    times: np.ndarray, click_len: int = 44100 * 0.1, sample_rate: int = 44100
):
    frames = times * sample_rate
    return np.array(list(map(lambda x: (x, x + click_len), frames)))


def frames_to_chunks(frames, chunk_size):
    return list(map(tuple, np.int32(frames / chunk_size)))


def frame_annots_to_chk_annots(annots, chunk_size):
    chk_annots = []
    for frame_range, tag in annots:
        chk_annots.append(((tuple(np.int32(frame_range / chunk_size))), tag))
    return chk_annots


def outlier_performance(
    outlier_scores: np.ndarray, click_chunks: np.ndarray, threshold=0.5
):
    outlier_chunks = np.concatenate(np.argwhere(outlier_scores > threshold)).tolist()
    normal_chunks = np.concatenate(np.argwhere(outlier_scores < threshold)).tolist()
    click_chunks = (
        np.concatenate(list(map(lambda x: np.arange(x[0], x[1]), click_chunks)))
        .ravel()
        .tolist()
    )
    accuracy = (
        sum([chunk in click_chunks for chunk in outlier_chunks])
        + sum([chunk not in click_chunks for chunk in normal_chunks])
    ) / len(outlier_scores)
    recall = sum([chunk in click_chunks for chunk in outlier_chunks]) / len(
        outlier_chunks
    )
    precision = sum([chunk in click_chunks for chunk in outlier_chunks]) / len(
        click_chunks
    )
    f1 = 2 * (recall * precision) / (recall + precision)
    return accuracy, recall, precision, f1


def classification_performance(
    scores: np.ndarray, annots: Iterable, method: str = "weighted"
):
    truth = []
    for idxs, tag in annots:
        for _ in np.arange(*idxs):
            truth.append(tag)

    accuracy = accuracy_score(truth, scores)
    recall = recall_score(truth, scores, average=method)
    precision = precision_score(truth, scores, average=method)
    f1 = f1_score(truth, scores, average=method)

    return accuracy, recall, precision, f1


def seeds_to_wfs(
    seeds,
    chk_size,
    freq_dict,
    seed_to_wf_chk,
):
    chks = map(seed_to_wf_chk, seeds, [chk_size] * len(seeds), [freq_dict] * len(seeds))
    return list(chks)


def seed_to_wf_chk(seed, chk_size, freq_dict):
    return mk_sine_wf(freq=freq_dict[seed], n_samples=chk_size)


def frames_to_chks(wf, frames):
    chks = []
    last_click = 0
    for click in frames:
        chks.append(wf[last_click : int(click[0])])
        last_click = int(click[0])
    return chks
