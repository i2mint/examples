import numpy as np
from typing import Iterable
from examples.synthetic_sounds.outlier_problems import build_click_wf
from examples.synthetic_sounds.util import frames_to_chks
from hum import pure_tone

# This doesn't work


def train_chunking_model(SPA=None):
    if SPA is None:
        from omodel.ml.event_detector import SpectraPatternDetection
        SPA = SpectraPatternDetection()
    wf = pure_tone(chk_size_frm=44100 * 30, max_amplitude=30)
    times = np.arange(0.3, 30, 0.5)
    click_wf, _ = build_click_wf(wf, times)
    SPA.fit(click_wf, times)
    return SPA


def test_chunking_model(base_wf: np.ndarray, times_for_clicks: Iterable[float]):
    click_wf, true_click_frames = build_click_wf(base_wf, times_for_clicks)

    SPA = train_chunking_model()
    gen = SPA.detect(click_wf, timestamps=False)
    model_click_frames = np.array(list(gen))

    model_chks = frames_to_chks(click_wf, model_click_frames)
    true_chks = frames_to_chks(click_wf, true_click_frames)

    return model_chks, true_chks
