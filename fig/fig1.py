"""Figure 1: Study A accuracy (panel a) and Study B differences (panel b).

Every plotted value is read from the released run and exploratory files when the
script runs. The PNG is written next to this script, whatever the working folder.

    python fig/fig1.py        (needs matplotlib)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'figure1.png'

INK, SEC, MUT, GRID, BG = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#ffffff'
C1, C2, C3, C4 = '#2a78d6', '#eb6834', '#1baf7a', '#8a5cc7'   # C1 true/real, C2 swapped/real
BAND = '#eef3fb'
RC = {'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': MUT, 'axes.labelcolor': SEC,
      'xtick.color': SEC, 'ytick.color': SEC, 'axes.titlesize': 11, 'axes.titleweight': 'bold',
      'axes.titlecolor': INK}

MODELS = ['E2B', 'E4B', '12B', '31B']     # left to right in panel a
CHANCE = 25        # percent: four answer options
EQUIV = 5          # points: the pre-registered equivalence margin, half-width of the band
XMIN = -12         # left edge of panel b; an interval that runs past it is drawn as an arrow

B_KEYS = ['B1', 'B2', 'B3', 'B4', 'B5']
CONTROL_MODELS = (('31B', 's'), ('E4B', '^'))   # model and its marker in the control rows
# marker styles shared by the plotted points and their legend entries
STUDY_MARK = dict(marker='o', ls='', ms=7, markeredgecolor=INK, markeredgewidth=1.6)
CONTROL_MARK = dict(ls='', ms=6, markeredgecolor=SEC, markeredgewidth=1.4)
# control row -> (exploratory results file, key of the difference in each model's entry)
CONTROL_SOURCES = {
    'equal_density': ('e4c', 'acc_true_minus_random_dense'),
    'equal_sparsity': ('e4c', 'acc_true_thinned_minus_rewired'),
    'hint': ('e3', 'hint_true_minus_rewired'),
    'hint_vs_none': ('e3', 'hint_true_minus_none'),
    'json_vs_line': ('e5', 'G1J_minus_G1'),
}


def _read(path):
    return json.loads((ROOT / path).read_text())


def load_values():
    """Read every plotted value from the released files. Values are in percent or points."""
    a = _read('runs/studyA/studyA_report.json')['accuracy']
    b = _read('runs/studyB/studyB_report.json')
    study_b = {k: (b[k]['estimate'] * 100, *[c * 100 for c in b[k]['ci95_stratified']]) for k in B_KEYS}
    wm = b['exploratory']['within_module_null']
    study_b['within_module'] = (wm['estimate'] * 100, *[c * 100 for c in wm['ci95']])
    files = {name: _read(f'exploratory/{name}_results.json')['models'] for name in ('e3', 'e4c', 'e5')}
    controls = {}
    for key, (name, field) in CONTROL_SOURCES.items():
        controls[key] = {m: (files[name][m][field]['mean'] * 100,
                             *[c * 100 for c in files[name][m][field]['ci95']])
                         for m, _ in CONTROL_MODELS}
    return {
        'study_a': {ver: [a[m][ver] * 100 for m in MODELS] for ver in ('G0', 'G1', 'G2', 'G3', 'G4')},
        'study_b': study_b,
        'controls': controls,
        'hint_tasks': files['e3']['31B']['hint_true_minus_rewired']['n'],
    }


def signed(x):
    return f'{x:+.1f}'.replace('-', '−')


def plain(x):
    return f'{x:.1f}'.replace('-', '−')


# Figure size in inches. The width stays under 7.5 in, so the point sizes below hold at the width shown.
W = 7.2
PAD_BOTTOM, LEGEND_H, XAXIS_H = 0.10, 0.55, 0.52
B_H, TITLE_GAP, A_H, A_XAXIS_H, TITLE_H = 4.64, 0.42, 2.65, 0.55, 0.50
B_BOTTOM = PAD_BOTTOM + LEGEND_H + XAXIS_H
B_TOP = B_BOTTOM + B_H
A_BOTTOM = B_TOP + TITLE_GAP + A_XAXIS_H
A_TOP = A_BOTTOM + A_H
H = A_TOP + TITLE_H
A_LEFT, B_LEFT, RIGHT = 0.70, 2.30, 0.15


def rect(left, bottom, width, height):
    return [left / W, bottom / H, width / W, height / H]


def draw_panel_a(ax, v):
    x = range(len(MODELS))
    lines = [('G1', C1, 'G1 true graph, real names', '-'), ('G2', C3, 'G2 true graph, neutral names', '--'),
             ('G3', C2, 'G3 swapped graph, real names', '-'), ('G4', C4, 'G4 swapped graph, neutral names', '--'),
             ('G0', MUT, 'G0 no graph', ':')]
    for ver, color, label, ls in lines:
        ax.plot(x, v['study_a'][ver], color=color, lw=2, ls=ls, marker='o', ms=5, label=label,
                markeredgecolor=BG, markeredgewidth=1)
    ax.axhline(CHANCE, color=MUT, lw=1, ls=(0, (2, 2)))
    ax.text(3.9, CHANCE + 1.2, f'chance ({CHANCE}%)', va='bottom', ha='right', color=SEC)
    ax.set_xticks(list(x))
    ax.set_xticklabels(MODELS)
    ax.set_xlim(-0.25, 3.95)
    ax.set_ylim(20, 100)
    ax.set_yticks(range(20, 101, 20))
    ax.set_xlabel('Gemma 4 model')
    ax.set_ylabel('Accuracy (%)')
    ax.grid(axis='y', color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    # the area right of 12B between about 48 and 84 percent holds no line
    ax.legend(frameon=False, loc='center left', bbox_to_anchor=(2.1, 67), bbox_transform=ax.transData,
              labelcolor=SEC, handlelength=2.2, labelspacing=0.5)


def draw_panel_b(ax, v):
    rows = [('B1', 'B1 real − renamed names', True),
            ('B2', 'B2 true − rewired\n(renamed, anchored)', True),
            ('B3', 'B3 graph value,\nrenamed − real', False),
            ('B4', 'B4 names effect,\n31B − E4B', False),
            ('B5', 'B5 scorer,\ntrue − rewired', False),
            ('within_module', 'Within-module rewiring\n(exploratory)', False)]
    ctrl = [('equal_density', 'Equal density:\ntrue − random'),
            ('equal_sparsity', 'Equal sparsity:\nthinned true − rewired'),
            ('hint', f"With hint: true − rewired\n({v['hint_tasks']} tasks)"),
            ('hint_vs_none', f"With hint: true − no graph\n({v['hint_tasks']} tasks)"),
            ('json_vs_line', 'JSON vs line format\n(Study A, G1)')]
    header = 'Exploratory controls\n(Sections 4.3, 5)'
    n = len(rows) + 1 + len(ctrl)
    header_y = n - 1 - len(rows)
    ax.axvspan(-EQUIV, EQUIV, color=BAND, zorder=0)
    ax.axvline(0, color=MUT, lw=1, zorder=1)
    for i, (key, _, confirmatory) in enumerate(rows):
        y = n - 1 - i
        e, lo, hi = v['study_b'][key]
        ax.plot([lo, hi], [y, y], color=INK, lw=2, solid_capstyle='round', zorder=2)
        ax.plot(e, y, color=INK if confirmatory else BG, zorder=3, **STUDY_MARK)
        ax.text(hi + 0.6, y, signed(e), va='center_baseline', ha='left', color=SEC)
    text_x = 6.2          # control labels sit right of every control interval
    dy = 0.22
    for j, (key, _) in enumerate(ctrl):
        y = header_y - 1 - j
        for (model, marker), off in zip(CONTROL_MODELS, (dy, -dy)):
            e, lo, hi = v['controls'][key][model]
            ax.plot([max(lo, XMIN + 0.05), hi], [y + off] * 2, color=SEC, lw=1.6, solid_capstyle='round', zorder=2)
            if lo < XMIN:
                ax.annotate('', xy=(XMIN + 0.05, y + off), xytext=(XMIN + 0.9, y + off),
                            arrowprops=dict(arrowstyle='->', color=SEC, lw=1.2))
            ax.plot(e, y + off, marker=marker, color=BG, zorder=3, **CONTROL_MARK)
            ax.text(text_x, y + off, f'{model} {signed(e)} ({plain(lo)} to {plain(hi)})',
                    va='center_baseline', ha='left', color=SEC)
    ax.axhline(header_y + 0.5, color=GRID, lw=0.8)
    ax.set_yticks(range(n))
    top_to_bottom = [r[1] for r in rows] + [header] + [c[1] for c in ctrl]
    ax.set_yticklabels(top_to_bottom[::-1], linespacing=1.15)
    ax.get_yticklabels()[header_y].set_fontweight('bold')
    ax.set_xlim(XMIN, 16.6)
    ax.set_ylim(-0.7, n - 0.4)
    ax.set_xlabel('Difference in accuracy, points (95% CI)')
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='y', length=0, pad=9)   # keeps the left-edge arrow clear of the row labels
    ax.set_xticks([-10, -5, 0, 5, 10])
    ax.set_xticklabels(['−10', '−5', '0', '+5', '+10'])
    handles = [Line2D([], [], color=INK, **STUDY_MARK), Line2D([], [], color=BG, **STUDY_MARK),
               *[Line2D([], [], marker=marker, color=BG, **CONTROL_MARK) for _, marker in CONTROL_MODELS],
               Patch(facecolor=BAND, edgecolor=GRID)]
    labels = ['Confirmatory comparison', 'Secondary or exploratory comparison',
              *[f'Control row: {model}' for model, _ in CONTROL_MODELS], f'±{EQUIV}-point equivalence band']
    return handles, labels


def make_figure():
    plt.rcParams.update(RC)
    v = load_values()
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(BG)
    a = fig.add_axes(rect(A_LEFT, A_BOTTOM, W - A_LEFT - RIGHT, A_H))
    b = fig.add_axes(rect(B_LEFT, B_BOTTOM, W - B_LEFT - RIGHT, B_H))
    draw_panel_a(a, v)
    handles, labels = draw_panel_b(b, v)
    title_kw = dict(ha='left', va='bottom', fontsize=11, fontweight='bold', color=INK)
    fig.text(0.12 / W, (A_TOP + 0.18) / H, '(a) Study A: Gemma 4 reads the graph it is shown', **title_kw)
    fig.text(0.12 / W, (B_TOP + 0.18) / H, '(b) Study B: names help ranking, true edges do not', **title_kw)
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, PAD_BOTTOM / H), ncol=3,
               frameon=False, labelcolor=SEC, columnspacing=1.6, handletextpad=0.5)
    return fig


def main():
    fig = make_figure()
    fig.savefig(OUT, dpi=300, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
