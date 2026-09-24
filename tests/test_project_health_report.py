import datetime as dt
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH=Path(__file__).parents[1]/"scripts"/"render_project_health_report.py"
spec=importlib.util.spec_from_file_location("project_health",MODULE_PATH)
project_health=importlib.util.module_from_spec(spec);spec.loader.exec_module(project_health)

class ProjectHealthTests(unittest.TestCase):
    def test_author_kind(self):
        self.assertEqual(project_health.kind("AjaneeI"),"human")
        self.assertEqual(project_health.kind("Copilot"),"automation")
        self.assertEqual(project_health.kind("github-actions[bot]"),"automation")

    def test_median_hours(self):
        items=[
          {"created_at":"2026-09-24T10:00:00Z","closed_at":"2026-09-24T11:00:00Z"},
          {"created_at":"2026-09-24T10:00:00Z","closed_at":"2026-09-24T13:00:00Z"},
          {"created_at":"2026-09-24T10:00:00Z","closed_at":"2026-09-24T15:00:00Z"}]
        self.assertEqual(project_health.median_hours(items),3.0)

    def test_analysis_and_visual(self):
        raw={"repo":{"default_branch":"main"},
          "commits":[{"sha":"abc","author":{"login":"AjaneeI"},"commit":{"committer":{"date":"2026-09-24T10:00:00Z"},"author":{"name":"Ajanee"}}}],
          "open_issues":{"total_count":2,"items":[]},"closed_issues":{"total_count":1,"items":[{"created_at":"2026-09-24T09:00:00Z","closed_at":"2026-09-24T10:00:00Z"}]},
          "open_prs":{"total_count":1,"items":[]},"merged_prs":{"total_count":5,"items":[]},"good_first":{"total_count":0,"items":[]},
          "releases":[],"root":[{"name":"README.md"},{"name":"SECURITY.md"}],"workflows":[{"name":"tests.yml"}]}
        s=project_health.analyze("AjaneeI/example",raw,dt.datetime(2026,9,24,19,0,tzinfo=dt.timezone.utc))
        self.assertEqual(s["activity"]["commits_last_7d"],1)
        self.assertFalse(s["documentation"]["CONTRIBUTING"])
        self.assertEqual(s["flow"]["merged_prs"],5)
        visual=project_health.render_svg(s)
        self.assertIn('role="img"',visual)
        self.assertIn("Project Health Snapshot",visual)
        self.assertNotIn("<script",project_health.render_html(s).lower())

if __name__=="__main__":
    unittest.main()
