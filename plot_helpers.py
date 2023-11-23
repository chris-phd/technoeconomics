#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List

def histogram_labels_from_datasets(dataset_dicts: List[Dict[str, float]]) -> List[str]:
    labels = []
    for dataset_dict in dataset_dicts:
        labels += list(dataset_dict.keys())
    return sorted(set(labels))


def add_stacked_histogram_data_to_axis(ax: plt.Axes, histogram_column_names: List[str], 
                                       stacked_data_labels: List[str], 
                                       dataset_dicts: List[Dict[str, float]], scale_data=1.0):
    bottom = np.array([0.0] * len(histogram_column_names))
    for label in stacked_data_labels:
        data_for_this_label = np.array([d[label] * scale_data for d in dataset_dicts])
        ax.bar(histogram_column_names, data_for_this_label, bottom=bottom, label=label)
        bottom = bottom + data_for_this_label


def add_titles_to_axis(ax: plt.Axes, title: str, y_label: str):
    ax.set_title(title)
    ax.set_ylabel(y_label)
    ax.legend(bbox_to_anchor = (1.0, 1.0), loc='upper left')
    plt.subplots_adjust(right=0.8)
    ax.grid(axis='y', linestyle='--')