import streamlit as st
from taped import LiveWf, list_recording_device_index_names
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time
from slang.chunkers import simple_fixed_step_chunker

from examples.phone_digits.streamlit_utils import stop, store_in_ss
from examples.phone_digits.utils import normalize_wf_taped


def barplot(chks_it, chk_step, length):
    times = np.arange(-length, 1, 1)
    tick_times = np.arange(0, length + 1, 1)
    ticks = np.around(tick_times * (44100 / chk_step))

    fig, axs = plt.subplots(len(chks_it), figsize=(20, 5))
    plt.setp(axs, xticks=ticks, xticklabels=times)

    for ax, chks in zip(axs, chks_it.values()):
        ax.bar(list(range(len(chks))), chks)

    return plt


def chks_for_live(live_wf, frame_start, frame_stop, funcs, chk_size, chk_step):
    new_wf_segment = normalize_wf_taped(live_wf[frame_start:frame_stop])
    new_chks = list(
        simple_fixed_step_chunker(new_wf_segment, chk_size=chk_size, chk_step=chk_step)
    )
    for func in funcs:
        st.session_state.multi_chks[func].extend(map(func, new_chks))


def display_results(chk_step, length):
    st.pyplot(barplot(st.session_state.multi_chks, chk_step, length))


def start_timer():
    st.session_state.start_time = time.time()


def go_live(funcs, **kwargs):
    st.set_page_config(layout="wide")
    mic = st.selectbox(
        "Which microphone would you like to use?",
        list_recording_device_index_names(),
    )

    st.session_state.live_wf = LiveWf(mic)
    st.session_state.live_wf.start()

    st.session_state.pressed = st.button("Press here to start!", on_click=start_timer)

    placeholder = st.empty()

    st.button("Press here to stop!", on_click=stop)

    store_in_ss("frame_start", 0)
    store_in_ss("frame_stop", 44100)

    chk_length = int(44100 * kwargs["interval_length"] / kwargs["chk_step"])

    st.session_state.multi_chks = dict()
    for func in funcs:
        st.session_state.multi_chks[func] = deque(
            np.zeros(chk_length), maxlen=chk_length
        )

    while st.session_state.pressed:
        chks_for_live(
            st.session_state.live_wf,
            st.session_state.frame_start,
            st.session_state.frame_stop,
            funcs,
            kwargs["chk_size"],
            kwargs["chk_step"],
        )

        with placeholder.beta_container():
            display_results(kwargs["chk_step"], kwargs["interval_length"])

        st.session_state.end_time = time.time()

        st.session_state.frame_start = st.session_state.frame_stop
        st.session_state.frame_stop += int(
            44100 * (st.session_state.end_time - st.session_state.start_time)
        )

        st.session_state.start_time = time.time()

    st.session_state.live_wf.stop()

    # if "start_time" in st.session_state and not st.session_state.pressed:
    #     with placeholder.beta_container():
    #         display_results(kwargs["chk_step"], kwargs["interval_length"])
