"""Tests for the figure scripts in this folder.

Run from the repository root:
    uv run --with matplotlib==3.11.2 python -m unittest discover -s fig -p "test_*.py"
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

FIG = Path(__file__).resolve().parent
ROOT = FIG.parent
sys.path.insert(0, str(FIG))

# Values the first version of fig1.py hard-coded, in the precision the figure uses.
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
# A control row the first version did not draw, from exploratory/e3_results.json
# (hint_true_minus_none), two decimals.
HINT_VS_NONE = {'31B': (-10.53, -26.32, 2.63), 'E4B': (-7.89, -21.05, 0.00)}


def run_script(script, cwd):
    """Run a figure script in a separate process and return the finished process."""
    return subprocess.run([sys.executable, str(FIG / script)], cwd=str(cwd),
                          capture_output=True, text=True, timeout=300)


class Figure1Data(unittest.TestCase):
    def test_loader_returns_every_value_the_old_script_hard_coded(self):
        from fig1 import load_values
        v = load_values()
        self.assertEqual(v['models'], ['E2B', 'E4B', '12B', '31B'])
        for ver, expected in STUDY_A.items():
            self.assertEqual([round(x, 2) for x in v['study_a'][ver]], expected, ver)
        for key, expected in STUDY_B.items():
            self.assertEqual(tuple(round(x, 2) for x in v['study_b'][key]), expected, key)
        for key, by_model in CONTROLS.items():
            for model, expected in by_model.items():
                got = tuple(round(x, 1) for x in v['controls'][key][model])
                self.assertEqual(got, expected, f'{key} {model}')

    def test_loader_returns_the_hint_against_no_graph_row(self):
        from fig1 import load_values
        row = load_values()['controls']['hint_vs_none']
        for model, expected in HINT_VS_NONE.items():
            for got, want in zip(row[model], expected):
                self.assertAlmostEqual(got, want, places=2, msg=model)


class Figure1Output(unittest.TestCase):
    def test_png_is_written_next_to_the_script_from_any_working_folder(self):
        png = FIG / 'figure1.png'
        for cwd in (ROOT, FIG):
            if png.exists():
                os.utime(png, (0, 0))  # an old time, so any rewrite is visible
            done = run_script('fig1.py', cwd)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(png.exists(), f'no figure1.png after running from {cwd.name}')
            self.assertGreater(png.stat().st_mtime, 0, f'figure1.png not rewritten from {cwd.name}')


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
        self.assertEqual(differing, [i for i, _, _ in self.fig2.swap_rows(self.item)])

    def test_correct_letters_come_from_the_item_file(self):
        self.assertEqual(self.item['correct_g1'], 'D')
        self.assertEqual(self.item['correct_g3'], 'B')
        marked = {r['text'][0]: r['kind'] for r in self.fig2.build_rows(self.item) if r['kind'].startswith('right_')}
        self.assertEqual(marked, {'D': 'right_true', 'B': 'right_swapped'})


if __name__ == '__main__':
    unittest.main()
