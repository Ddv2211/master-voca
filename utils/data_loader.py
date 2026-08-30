"""Tải & truy vấn dữ liệu từ vựng từ data/vocabulary.json."""
from __future__ import annotations

import json
import os

import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vocabulary.json")


@st.cache_data(show_spinner=False)
def load_vocabulary() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def get_topics() -> list[str]:
    words = load_vocabulary()
    topics = sorted({w["topic"] for w in words}, key=lambda t: (t == "Từ vựng chung", t))
    return topics


@st.cache_data(show_spinner=False)
def get_batches() -> list[int]:
    words = load_vocabulary()
    return sorted({w["batch"] for w in words})


def words_by_topic(topic: str) -> list[dict]:
    return [w for w in load_vocabulary() if w["topic"] == topic]


def words_by_batch(batch: int) -> list[dict]:
    return [w for w in load_vocabulary() if w["batch"] == batch]


def get_word_by_stt(stt: int) -> dict | None:
    for w in load_vocabulary():
        if w["stt"] == stt:
            return w
    return None
