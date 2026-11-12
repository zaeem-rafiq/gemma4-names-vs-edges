"""Figure 2: one real Study A question, under the true graph and after one edge swap.

The prompt is printed word for word from the released item file. The graph lines that
the swap changes are highlighted, and each is followed by its swapped form. The PNG is
written next to this script, whatever the working folder.

    python fig/fig2.py        (needs matplotlib)
"""
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from fig1 import BG, GRID, INK, SEC, C1, C2   # Figure 1's colors: true graph blue, swapped graph orange

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'figure2.png'
ITEM_FILE = ROOT / 'data' / 'items' / 'click.json'
# A short one-hop question from a widely known confirmatory repository whose swapped graph contradicts the real code.
ITEM_ID = 'click/A/S12/003'

BLUE_TINT, ORANGE_TINT, BOX = '#e3eefb', '#fdeee6', '#f7f7f4'
BLUE_TEXT, ORANGE_TEXT = '#1a5aa8', '#b8420f'   # darker C1 and C2, for small text
MONO, SANS = 'DejaVu Sans Mono', 'DejaVu Sans'

W = 7.2                  # inches
FS = 9                   # point size of every line of the prompt
ROW = 0.19               # inches per text row
X0, XR = 0.30, 7.00      # left edge of the prompt text, right edge for tags
WRAP = 86                # monospace columns that fit between X0 and the right margin (0.0767 in each at 9 pt)


def load_item():
    """The chosen item: both prompts, the correct letters, the swap record and the pinned commit."""
    data = json.loads(ITEM_FILE.read_text())
    item = next(i for i in data['items'] if i['item_id'] == ITEM_ID)
    g1, g3 = item['versions']['G1'], item['versions']['G3']
    return {'item_id': ITEM_ID, 'repo': item['repo'], 'commit': item['commit'], 'g1': g1['text'], 'g3': g3['text'],
            'correct_g1': g1['correct'], 'correct_g3': g3['correct'], 'swap': item['swap']}


def swapped_lines(item):
    """{line number: swapped line} for each graph line whose caller the swap removes an edge from."""
    prefixes = tuple(caller + ' -> ' for caller, _ in item['swap']['remove'])
    g1, g3 = item['g1'].split('\n'), item['g3'].split('\n')
    return {i: g3[i] for i, line in enumerate(g1) if line.startswith(prefixes)}


def wrap(line):
    return textwrap.wrap(line, width=WRAP, subsequent_indent='    ',
                         break_long_words=False, break_on_hyphens=False)


def build_rows(item):
    """Rows of the drawing, top to bottom. kind: plain, true, label, swapped, right_true, right_swapped, blank."""
    swapped = swapped_lines(item)
    rows = []
    for i, line in enumerate(item['g1'].split('\n')):
        if not line:
            rows.append({'kind': 'blank', 'text': ''})
            continue
        kind = 'true' if i in swapped else 'plain'
        if line.startswith(f"{item['correct_g1']}. "):
            kind = 'right_true'
        elif line.startswith(f"{item['correct_g3']}. "):
            kind = 'right_swapped'
        rows += [{'kind': kind, 'text': piece} for piece in wrap(line)]
        if i in swapped:
            rows.append({'kind': 'label', 'text': 'after the swap (G3):'})
            rows += [{'kind': 'swapped', 'text': piece} for piece in wrap(swapped[i])]
    return rows


# kind -> (band color, bar color, tag text, tag color)
STYLE = {
    'true': (BLUE_TINT, C1, None, None),
    'label': (ORANGE_TINT, C2, None, None),
    'swapped': (ORANGE_TINT, C2, None, None),
    'right_true': (BLUE_TINT, C1, 'correct under the true graph', BLUE_TEXT),
    'right_swapped': (ORANGE_TINT, C2, 'correct under the swapped graph', ORANGE_TEXT),
}


def make_figure():
    item = load_item()
    rows = build_rows(item)
    heights = [ROW * 0.5 if r['kind'] == 'blank' else ROW for r in rows]
    top_pad, title_h, sub_h, gap, box_pad, foot_h = 0.15, 0.30, 0.40, 0.14, 0.10, 0.34
    box_h = sum(heights) + 2 * box_pad
    H = top_pad + title_h + sub_h + gap + box_h + foot_h
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)          # inches from the top of the figure
    ax.axis('off')

    ax.text(0.12, top_pad, 'One Study A question, under the true graph and after one edge swap',
            ha='left', va='top', fontsize=11, fontweight='bold', color=INK, family=SANS)
    ax.text(0.12, top_pad + title_h, 'The released prompt, word for word. It holds either the blue graph lines (G1) or the orange ones (G3).\n'
            'The swap changes only those lines. Orange labels and right-hand tags are not in the prompt.',
            ha='left', va='top', fontsize=9, color=SEC, family=SANS, linespacing=1.35)

    box_top = top_pad + title_h + sub_h + gap
    ax.add_patch(Rectangle((0.12, box_top), W - 0.24, box_h, facecolor=BOX, edgecolor=GRID, lw=0.8, zorder=0))
    y = box_top + box_pad
    for r, h in zip(rows, heights):
        style = STYLE.get(r['kind'])
        if style:
            band, bar, tag, tag_color = style
            ax.add_patch(Rectangle((0.13, y), W - 0.26, h, facecolor=band, edgecolor='none', zorder=1))
            ax.add_patch(Rectangle((0.13, y), 0.06, h, facecolor=bar, edgecolor='none', zorder=2))
            if tag:
                ax.text(XR, y + h / 2, tag, ha='right', va='center_baseline', fontsize=FS,
                        fontweight='bold', color=tag_color, family=SANS, zorder=3)
        if r['text']:
            font = (dict(fontweight='bold', color=ORANGE_TEXT, family=SANS) if r['kind'] == 'label'
                    else dict(color=INK, family=MONO))
            ax.text(X0, y + h / 2, r['text'], ha='left', va='center_baseline', fontsize=FS, zorder=3, **font)
        y += h
    ax.text(0.12, box_top + box_h + 0.12, f"Item {item['item_id']} in data/items/{ITEM_FILE.name}. "
            f"Repository {item['repo']}, pinned commit {item['commit'][:7]}.",
            ha='left', va='top', fontsize=8.5, color=SEC, family=SANS)
    return fig


def main():
    fig = make_figure()
    fig.savefig(OUT, dpi=300, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
