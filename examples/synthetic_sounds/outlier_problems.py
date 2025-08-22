import librosa
import numpy as np
import augly.audio as audaugs
from examples.synthetic_sounds.util import (
    times_to_frames_range,
    frames_to_chunks,
    chk_gen,
    DFLT_CHUNKER,
)
from typing import Iterable, Callable
from sklearn.decomposition import PCA
from sklearn.svm import OneClassSVM


def build_click_wf(
    base_wf: np.ndarray,
    times_for_clicks: np.ndarray,
    sample_rate: int = 44100,
    strength_of_click: float = 0,
    click_sample: np.ndarray = None,
):
    times_for_clicks = np.array(times_for_clicks)
    times_for_clicks = np.append(times_for_clicks, base_wf.shape[-1] / sample_rate)

    clicks_audio = librosa.clicks(
        times=times_for_clicks, sr=sample_rate, click=click_sample
    )

    new_wf, sample_rate = audaugs.add_background_noise(
        base_wf,
        sample_rate=sample_rate,
        background_audio=clicks_audio,
        snr_level_db=strength_of_click,
    )

    if click_sample is not None:
        frames_range = times_to_frames_range(
            times=times_for_clicks, click_len=len(click_sample), sample_rate=sample_rate
        )
    else:
        frames_range = times_to_frames_range(
            times=times_for_clicks, sample_rate=sample_rate
        )

    return new_wf, frames_range


def test_outlier_model(
    base_wf: np.ndarray,
    sample_rate: int = 44100,
    seconds_between_clicks: float = None,
    times_for_clicks: Iterable = None,
    strength_of_click: float = 0,
    click_sample: np.ndarray = None,
    chunker=DFLT_CHUNKER,
    chk_size=2048,
    featurizer: Callable = PCA,
    model: Callable = OneClassSVM,
):
    num_samples = base_wf.shape[-1]
    seconds = num_samples / sample_rate

    if seconds_between_clicks is None and times_for_clicks is None:
        raise AttributeError(
            "Either seconds_between_clicks or times needs to be specified!"
        )
    elif times_for_clicks is None:
        times_for_clicks = np.arange(0, seconds, seconds_between_clicks)
    elif seconds_between_clicks is None:
        times_for_clicks = np.array(times_for_clicks)
    else:
        raise AttributeError(
            "Only one of times and seconds_between_clicks should be specified!"
        )

    outlier_wf, frames_range = build_click_wf(
        base_wf=base_wf,
        times_for_clicks=times_for_clicks,
        sample_rate=sample_rate,
        strength_of_click=strength_of_click,
        click_sample=click_sample,
    )
    chunker = chunker(chk_size)
    chks = [tup for tup in chk_gen(outlier_wf, chunker)]

    featurizer = featurizer().fit(chks)
    fvs = featurizer(chks)

    model = model().fit(fvs)
    outlier_scores = model.predict(fvs)

    click_chunks = frames_to_chunks(frames_range, chk_size)
    return outlier_scores, click_chunks, outlier_wf
