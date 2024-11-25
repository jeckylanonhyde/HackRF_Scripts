#!/usr/bin/env python3
# vim: set ts=4 sw=4 tw=0 et fenc=utf8 pm=:

import sys
import os
import matplotlib.pyplot as plt
from util import parse_channel


def filter_voc(t_start=None, t_stop=None, f_min=None, f_max=None):
    tsl, fl, lines, quals = [], [], [], []

    with open(sys.argv[1], 'r') as file:
        for line in file:
            line = line.strip()
            if 'VOC: ' in line and "LCW(0,001111,100000000000000000000" not in line:
                line_split = line.split()
                oknok = 0

                if line_split[1] == 'VOC:':
                    oknok = int(line_split[0][-1])
                    line_split = line_split[1:]
                else:
                    oknok = "LCW(0,T:maint,C:<silent>," in line

                oknok = ['red', 'orange', 'green'][oknok]
                ts_base = 0
                ts = ts_base + float(line_split[2]) / 1000.0
                freq = parse_channel(line_split[3])

                if ((not t_start or t_start <= ts) and
                        (not t_stop or ts <= t_stop) and
                        (not f_min or f_min <= freq) and
                        (not f_max or freq <= f_max)):
                    tsl.append(ts)
                    fl.append(freq)
                    quals.append(oknok)
                    lines.append(line)

    return tsl, fl, quals, lines


def cut_convert_play(t_start, t_stop, f_min, f_max):
    if t_start and t_stop:
        t_start, t_stop = min(t_start, t_stop), max(t_start, t_stop)
    if f_min and f_max:
        f_min, f_max = min(f_min, f_max), max(f_min, f_max)

    _, _, _, lines = filter_voc(t_start, t_stop, f_min, f_max)

    if not lines:
        print("No data selected")
        return

    output_file = '/tmp/voice.bits'
    with open(output_file, 'w') as f_out:
        f_out.write("\n".join(lines))

    os.system(f"play-iridium-ambe {output_file}")


def onclick(event):
    global t_start, t_stop, f_min, f_max
    print(f'button={event.button}, x={event.x}, y={event.y}, xdata={event.xdata:.2f}, ydata={event.ydata:.2f}')
    if event.button == 1:
        t_start, f_min = event.xdata, event.ydata
        t_stop, f_max = None, None
    elif event.button == 3:
        t_stop, f_max = event.xdata, event.ydata

    if t_start and t_stop:
        cut_convert_play(t_start, t_stop, f_min, f_max)


def main():
    tsl, fl, quals, _ = filter_voc()

    print(f"Number of data points: {len(tsl)}")

    fig, ax = plt.subplots()
    scatter = ax.scatter(x=tsl, y=fl, c=quals, s=30)
    plt.title("Click once left and once right to define an area.\n"
              "The script will play iridium using the play-iridium-ambe script.")

    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()


if __name__ == "__main__":
    t_start, t_stop, f_min, f_max = None, None, None, None
    main()