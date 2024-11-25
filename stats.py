#!/usr/bin/env python3
# vim: set ts=4 sw=4 tw=0 et fenc=utf8 pm=:

import sys
import matplotlib.pyplot as plt
import collections
from util import parse_channel


def read_input_file():
    """Reads the input file from arguments or stdin."""
    if len(sys.argv) < 2:
        return open("/dev/stdin")
    return open(sys.argv[1])


def initialize_frame_data():
    """Initialize the frame configurations."""
    colors = [
        '#cab2d6', '#33a02c', '#fdbf6f', '#ffff99', '#6a3d9a', '#e31a1c', '#ff7f00',
        '#fb9a99', '#b2df8a', '#1f78b4', '#aaaaaa', '#a6cee3', '#dddd77'
    ]

    return collections.OrderedDict({
        'IMS': [colors[0], 'x', 1], 'MSG': [colors[1], 'o', 1],
        'IRA': [colors[2], 'x', 1], 'ITL': [colors[9], 'x', 1],
        'ISY': [colors[3], 'o', 1], 'IBC': [colors[4], 'o', 1],
        'IU3': [colors[5], 'o', 1], 'IDA': [colors[6], 'o', 1],
        'IIU': [colors[7], 'o', 1], 'IIR': [colors[10], 'o', 1],
        'IIP': [colors[9], 'o', 1], 'IIQ': [colors[8], 'o', 1],
        'VOC': [colors[11], 'o', 1], 'VOD': [colors[1], 'x', 1],
        'VDA': [colors[2], 'o', 1], 'VO6': [colors[12], 'o', 1],
        'IRI': ['purple', 'x', 0], 'RAW': ['grey', 'x', 0]
    })


def process_data(file, frames):
    """Process the data and extract relevant information."""
    data = collections.OrderedDict({t: [[], [], None] for t in frames})
    newtypes = []
    max_f, min_f, max_ts, min_ts = None, None, None, None

    for line in file:
        line = line.strip().split()
        ftype = line[0][:-1]

        if ftype == "ERR":
            continue

        ts_base = 0
        ts = ts_base + float(line[2]) / 1000.0
        frequency = parse_channel(line[3]) if "|" in line[3] else int(line[3])

        max_f = max(max_f, frequency) if max_f else frequency
        min_f = min(min_f, frequency) if min_f else frequency
        max_ts = max(max_ts, ts) if max_ts else ts
        min_ts = min(min_ts, ts) if min_ts else ts

        if ftype in data:
            data[ftype][0].append(ts)
            data[ftype][1].append(frequency)
        elif ftype not in newtypes:
            print(f"Unhandled frame type: {ftype}")
            newtypes.append(ftype)

    return data, max_f, min_f, max_ts, min_ts


def create_plot(data, frames):
    """Create and display the plot with interactive legend."""
    for t, frame_data in frames.items():
        if len(data[t][0]) > 0:
            data[t][2] = plt.scatter(
                y=data[t][1], x=data[t][0], c=frame_data[0], label=t,
                alpha=1, facecolors=frame_data[0], marker=frame_data[1], s=20
            )
        else:
            del data[t]

    legend = plt.legend(loc='upper right')
    legend.set_draggable(True)
    return legend


def update_legend(legend, data, frames):
    """Update the legend to toggle lines on/off interactively."""
    legend_items = legend.get_children()[0].get_children()[1].get_children()[0].get_children()
    legend_map = {}

    def toggle_visibility(legend_item, onoff):
        frame_type = legend_map[legend_item]
        item = data[frame_type][2]
        if onoff == -1:
            onoff = not item.get_visible()
        item.set_visible(onoff)

        dots, txts = legend_item.get_children()
        dot, txt = dots.get_children()[0], txts.get_children()[0]
        txt.set_alpha(1.0 if onoff else 0.2)
        dot.set_alpha(1.0 if onoff else 0.2)

    for i, frame_type in enumerate(data):
        legend_items[i].set_picker(5)  # 5 pts tolerance
        legend_map[legend_items[i]] = frame_type
        if frames[frame_type][2] == 0:
            toggle_visibility(legend_items[i], 0)

    return legend_map


def main():
    file = read_input_file()
    frames = initialize_frame_data()
    data, max_f, min_f, max_ts, min_ts = process_data(file, frames)

    plt.ylim([1618e6, 1626.7e6])
    plt.xlim([min_ts, max_ts])

    legend = create_plot(data, frames)
    legend_map = update_legend(legend, data, frames)

    def onpick(event):
        if isinstance(event.artist, plt.Line2D):
            toggle_visibility(event.artist, -1)
            plt.gcf().canvas.draw()

    plt.gcf().canvas.mpl_connect('pick_event', onpick)
    plt.title('Click on legend line to toggle line visibility')
    plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.05)
    plt.show()


if __name__ == "__main__":
    main()