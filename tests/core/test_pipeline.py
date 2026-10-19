import sys, json, tempfile, unittest
from pathlib import Path

REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(REPO_ROOT/"src"))

from generative_origami.semantic import parse_target
from generative_origami.pipeline import generate
from generative_origami.foldgen import generate_fold
from generative_origami.validate import validate_fold

class PipelineTests(unittest.TestCase):
    def test_four_quadrupeds_share_family_but_differ(self):
        specs=[parse_target(x) for x in ["狗","狐狸","鹿","长颈鹿"]]
        self.assertTrue(all(s.family=="QUADRUPED" for s in specs))
        self.assertEqual(len({json.dumps(s.parameters,sort_keys=True) for s in specs}),4)

    def test_any_query_returns_result(self):
        for q in ["霸王龙","玫瑰","咖啡杯","量子猫头鹰城堡"]:
            r=generate(q)
            self.assertEqual(r["product_status"],"RESULT_AVAILABLE")
            self.assertTrue(r["fallback_links"])
            self.assertIn("validation",r)

    def test_local_fold_gate_passes_samples(self):
        for q in ["狗","狐狸","千纸鹤","盒子","咖啡杯"]:
            spec=parse_target(q)
            fold=generate_fold(spec)
            rep=validate_fold(fold)
            self.assertTrue(rep.passed, (q,rep.to_dict()))

    def test_output_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            r=generate("狐狸",td)
            p=Path(r["artifact_dir"])
            self.assertTrue((p/"candidate.fold").exists())
            self.assertTrue((p/"preview.svg").exists())
            self.assertTrue((p/"tutorial.json").exists())

    def test_deterministic(self):
        a=generate_fold(parse_target("未知目标"))
        b=generate_fold(parse_target("未知目标"))
        self.assertEqual(a["vertices_coords"],b["vertices_coords"])
        self.assertEqual(a["edges_assignment"],b["edges_assignment"])

if __name__=="__main__":
    unittest.main()