import base64
import io
import re

import numpy as np
import pandas as pd
import requests
from dagster import MetadataValue, Output, asset, get_dagster_logger
from matplotlib import pyplot as plt

LIMIT = 100

logger = get_dagster_logger()

NON_ALPHA_PATTERN = re.compile(r"[^a-zA-Z\s]")


@asset
def top_story_ids():
    result = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    data = result.json()
    return data[:LIMIT]


@asset
def top_stories(top_story_ids):
    results = []
    for index, id in enumerate(top_story_ids):
        logger.info(f"Progress: {index + 1}/{LIMIT}")
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json")
        data = item.json()
        results.append(data)

    df = pd.DataFrame(results)
    metadata = {
        "num_records": len(results),
        "preview": MetadataValue.md(df.to_markdown()),
    }
    return Output(value=df, metadata=metadata)


@asset
def most_frequent_words(top_stories):
    stop_words = [
        "a",
        "the",
        "an",
        "of",
        "to",
        "in",
        "for",
        "and",
        "with",
        "on",
        "is",
        "are",
        "its",
        "be",
        "vs",
        "as",
    ]

    word_counts = {}
    for title in top_stories["title"]:
        title: str = title.lower()
        for word in title.split():
            cleaned_word = re.sub(NON_ALPHA_PATTERN, "", word)
            if (
                cleaned_word not in stop_words
                and len(cleaned_word) > 0
                and not cleaned_word.isnumeric()
            ):
                word_counts[cleaned_word] = word_counts.get(cleaned_word, 0) + 1

    top_words = {
        key: value
        for key, value in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[
            :25
        ]
    }

    plt.figure(figsize=(10, 6))
    plt.bar(top_words.keys(), top_words.values())
    plt.xticks(rotation=45, ha="right")
    plt.yticks(np.arange(0, max(top_words.values()) + 1, 1))
    plt.title("Top 25 Words in Hacker News Titles")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    image_data = base64.b64encode(buffer.getvalue())

    md_content = f"![img](data:image/png;base64,{image_data.decode()})"
    metadata = {"plot": MetadataValue.md(md_content)}
    return Output(value=top_words, metadata=metadata)
