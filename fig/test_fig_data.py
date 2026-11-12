"""Tests for the figure scripts in this folder.

Run from the repository root:
    uv run --with matplotlib==3.11.2 python -m unittest discover -s fig -p "test_*.py"

The tests write nothing into the repository: the scripts run in a temporary copy.
"""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FIG = Path(__file__).resolve().parent
ROOT = FIG.parent
sys.path.insert(0, str(FIG))

# The released files that the two scripts read. The scripts must need nothing else.
INPUTS = (
    'runs/studyA/studyA_report.json',
    'runs/studyB/studyB_report.json',
    'exploratory/e3_results.json',
    'exploratory/e4c_results.json',
    'exploratory/e5_results.json',
    'data/items/click.json',
)

# Expected plotted values, at the precision the figure prints.
# Study A accuracy in percent, in the order E2B, E4B, 12B, 31B.
STUDY_A = {
    'G0': [32.66, 36.88, 40.00, 46.41],
    'G1': [57.27, 64.84, 91.56, 96.41],
    'G2': [58.44, 61.72, 91.25, 96.09],
    'G3': [46.72, 54.61, 89.84, 93.75],
    'G4': [50.08, 53.98, 87.66, 92.81],
}
# Study B rows in points: (estimate, lower, upper), two decimals.
STUDY_B = {
    'B1': (8.02, 4.92, 11.12),
    'B2': (-2.16, -4.17, -0.29),
    'B3': (-2.30, -5.03, 0.43),
    'B4': (1.35, -6.31, 9.01),
    'B5': (-1.15, -2.87, 0.00),
    'within_module': (-0.72, -2.87, 1.44),
}
# Control rows in points: {model: (estimate, lower, upper)}, one decimal.
CONTROLS = {
    'equal_density': {'31B': (-0.3, -1.4, 0.6), 'E4B': (0.3, -2.0, 2.6)},
    'equal_sparsity': {'31B': (0.9, -0.3, 2.3), 'E4B': (-1.4, -3.2, 0.3)},
    'hint': {'31B': (-5.3, -18.4, 5.3), 'E4B': (-2.6, -7.9, 0.0)},
    'json_vs_line': {'31B': (1.1, -0.2, 2.3), 'E4B': (-0.2, -2.7, 2.2)},
}
# Control row hint_vs_none: exploratory/e3_results.json, hint_true_minus_none, two decimals.
HINT_VS_NONE = {'31B': (-10.53, -26.32, 2.63), 'E4B': (-7.89, -21.05, 0.00)}
HINT_TASKS = 19


def copy_inputs(root):
    """Copy the released input files into the folder `root`, at the same relative paths."""
    for rel in INPUTS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, root / rel)


def png_size(path):
    """Pixel width and height, read from the PNG header."""
    with open(path, 'rb') as f:
        return struct.unpack('>II', f.read(24)[16:24])


class Figure1Data(unittest.TestCase):
    def test_loader_returns_the_plotted_values(self):
        from fig1 import load_values
        v = load_values()
        for ver, expected in STUDY_A.items():
            self.assertEqual([round(x, 2) for x in v['study_a'][ver]], expected, ver)
        for key, expected in STUDY_B.items():
            self.assertEqual(tuple(round(x, 2) for x in v['study_b'][key]), expected, key)
        for key, by_model in CONTROLS.items():
            for model, expected in by_model.items():
                got = tuple(round(x, 1) for x in v['controls'][key][model])
                self.assertEqual(got, expected, f'{key} {model}')
        self.assertEqual(v['hint_tasks'], HINT_TASKS)

    def test_loader_returns_the_hint_against_no_graph_row(self):
        from fig1 import load_values
        row = load_values()['controls']['hint_vs_none']
        for model, expected in HINT_VS_NONE.items():
            for got, want in zip(row[model], expected):
                self.assertAlmostEqual(got, want, places=2, msg=model)


class Figure1ReadsTheReleasedFiles(unittest.TestCase):
    def test_a_changed_file_changes_what_the_figure_draws(self):
        """Values typed into the script would leave the drawing as it was."""
        import fig1
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_inputs(root)

            def rewrite(rel, change):
                data = json.loads((root / rel).read_text())
                change(data)
                (root / rel).write_text(json.dumps(data))

            rewrite('runs/studyA/studyA_report.json', lambda d: d['accuracy']['31B'].update(G1=0.5))
            rewrite('runs/studyB/studyB_report.json', lambda d: d['B1'].update(estimate=0.01))
            rewrite('exploratory/e3_results.json',
                    lambda d: d['models']['31B']['hint_true_minus_rewired'].update(mean=0.02))
            with mock.patch.object(fig1, 'ROOT', root):
                fig = fig1.make_figure()
        try:
            panel_a, panel_b = fig.axes
            g1 = next(line for line in panel_a.lines if str(line.get_label()).startswith('G1 '))
            self.assertAlmostEqual(g1.get_ydata()[fig1.MODELS.index('31B')], 50.0)
            printed = [t.get_text() for t in panel_b.texts]
            self.assertIn('+1.0', printed)
            self.assertTrue(any(t.startswith('31B +2.0 (') for t in printed), printed)
        finally:
            fig1.plt.close(fig)


class FigureOutput(unittest.TestCase):
    def test_each_png_is_written_next_to_its_script_from_any_working_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_inputs(root)
            fig = root / 'fig'
            fig.mkdir()
            for script in ('fig1.py', 'fig2.py'):
                shutil.copyfile(FIG / script, fig / script)
            for script, name in (('fig1.py', 'figure1.png'), ('fig2.py', 'figure2.png')):
                png = fig / name
                for where, cwd in (('the root folder', root), ('the fig folder', fig)):
                    png.unlink(missing_ok=True)
                    done = subprocess.run([sys.executable, str(fig / script)], cwd=str(cwd),
                                          capture_output=True, text=True, timeout=300)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertTrue(png.exists(), f'no {name} after running from {where}')
                self.assertEqual(png_size(png), png_size(FIG / name), f'{name} has another size than the released file')


class Figure2Item(unittest.TestCase):
    def setUp(self):
        import fig2
        self.fig2 = fig2
        self.item = fig2.load_item()

    def test_prompts_differ_in_exactly_the_lines_the_swap_names(self):
        g1, g3 = self.item['g1'].split('\n'), self.item['g3'].split('\n')
        self.assertEqual(len(g1), len(g3))
        callers = [caller for caller, _ in self.item['swap']['remove']]
        differing = [i for i, (a, b) in enumerate(zip(g1, g3)) if a != b]
        self.assertTrue(differing)
        for i in differing:
            self.assertTrue(any(g1[i].startswith(c + ' -> ') for c in callers), g1[i])
        self.assertEqual(differing, list(self.fig2.swapped_lines(self.item)))

    def test_rows_reprint_the_prompt_word_for_word(self):
        rows = self.fig2.build_rows(self.item)
        shown = ' '.join(r['text'] for r in rows if r['kind'] not in ('label', 'swapped'))
        self.assertEqual(shown.split(), self.item['g1'].split())
        g3 = self.item['g3'].split('\n')
        swapped = ' '.join(r['text'] for r in rows if r['kind'] == 'swapped')
        expected = ' '.join(g3[i] for i in self.fig2.swapped_lines(self.item))
        self.assertEqual(swapped.split(), expected.split())

    def test_correct_letters_come_from_the_item_file(self):
        self.assertEqual(self.item['correct_g1'], 'D')
        self.assertEqual(self.item['correct_g3'], 'B')
        marked = {r['text'][0]: r['kind'] for r in self.fig2.build_rows(self.item) if r['kind'].startswith('right_')}
        self.assertEqual(marked, {'D': 'right_true', 'B': 'right_swapped'})


if __name__ == '__main__':
    unittest.main()
