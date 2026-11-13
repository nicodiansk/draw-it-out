"""Plugin and marketplace manifests."""
import json
import unittest

from helpers import REPO

PLUGIN = REPO / ".claude-plugin" / "plugin.json"
MARKET = REPO / ".claude-plugin" / "marketplace.json"


class Manifest(unittest.TestCase):
    def test_plugin_name_and_version(self):
        plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "draw-it-out")
        self.assertRegex(plugin["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(plugin["license"], "MIT")

    def test_marketplace_lists_this_repo_without_a_version(self):
        market = json.loads(MARKET.read_text(encoding="utf-8"))
        self.assertEqual(market["name"], "draw-it-out")
        [entry] = market["plugins"]
        self.assertEqual((entry["name"], entry["source"]), ("draw-it-out", "./"))
        self.assertNotIn("version", entry)


if __name__ == "__main__":
    unittest.main()
