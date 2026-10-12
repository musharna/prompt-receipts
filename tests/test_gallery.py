"""Runs tools/gallery.py the way the gallery's GitHub Action does, on issue events shaped like GitHub's.
python -m unittest discover -s tests"""

import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tracemalloc
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
GALLERY = os.path.join(HERE, "..", "tools", "gallery.py")
INDEX = os.path.join(HERE, "..", "index.html")
SITE = "https://musharna.github.io/prompt-receipts/"
spec = importlib.util.spec_from_file_location("gallery", GALLERY)
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)

RECEIPT = """Receipt v7.9 · Claude Code 2.1.300 · 9 Oct 2026, 10:00 AM EDT · no. 1a2b-3c4d
model    claude-opus-5-5 · effort medium
time     6 min (model working 5 min) · 1 prompt from me
cost     $1.23 (Claude Code's own total at API prices; the lines below add up to it)
tokens   in 120k (100k cached) · out 9k
prompt   Make a page for my habit tracker"""


def pack(text, raw=None):
    """a receipt's text -> the r1. part of its link, as receipt.py --link makes it"""
    z = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = raw if raw is not None else z.compress(text.encode("utf-8")) + z.flush()
    return "r1." + base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def event(body, number=7, login="someone", action="opened"):
    return {"action": action, "issue": {"number": number, "body": body, "user": {"login": login},
                                        "labels": [{"name": "receipt"}]}}  # fmt: skip


def form(link):
    """an issue body as GitHub's issue form writes it"""
    return f"### Receipt link\n\n{link}\n\n### Anything to add\n\n_No response_\n\n### Public\n\n- [X] I'm happy"


class Gallery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_gallery(self, *args):
        return subprocess.run([sys.executable, "-I", GALLERY, *args], capture_output=True, text=True,
                              encoding="utf-8")  # fmt: skip

    def write_event(self, e, name="event.json"):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(e, fh)
        return p

    def test_the_sites_own_receipts_all_go_in(self):
        out = os.path.join(self.dir, "g.json")
        entries = gallery.seed(INDEX, out)
        self.assertEqual(
            len(entries), 113
        )  # 16 cards × 7 models, and the opus run's page-checked link
        with open(INDEX, encoding="utf-8") as fh:
            self.assertEqual(len(entries), fh.read().count("/r/#r1."))
        models = {e["model"] for e in entries}
        self.assertEqual(models, {"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "gpt-5.6-sol",
                                  "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra"})  # fmt: skip
        self.assertEqual({e["tool"] for e in entries}, {"Claude Code", "Codex CLI"})
        self.assertEqual({(e["kind"], e["by"]) for e in entries}, {("site", "Prompt Receipts")})
        self.assertTrue(all(e["usd"] is not None and e["prompt"] for e in entries))
        p1 = [
            e for e in entries if e["card"] == "p1" and e["model"] == "claude-opus-5-5"
        ][0]
        self.assertEqual((p1["cost"], p1["usd"], p1["time"]), ("$0.80", 0.80, "4 min"))
        self.assertTrue(p1["prompt"].startswith("A three-panel comic page"))
        with open(out, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        self.assertEqual(
            len(lines), 113 + 3
        )  # one entry per line, so each addition is a one-line diff
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), entries)

    def test_what_a_receipt_shows(self):
        e = gallery.entry(pack(RECEIPT))
        self.assertEqual(
            {k: e[k] for k in ("kind", "receipt", "tool", "tool_version", "date", "model", "cost", "usd", "time",
                               "prompt")},  # fmt: skip
            {"kind": "sent", "receipt": "7.9", "tool": "Claude Code", "tool_version": "2.1.300",
             "date": "9 Oct 2026, 10:00 AM EDT", "model": "claude-opus-5-5", "cost": "$1.23", "usd": 1.23,
             "time": "6 min", "prompt": "Make a page for my habit tracker"},
        )  # fmt: skip
        bare = gallery.entry(
            pack("Receipt v7.9 · Codex CLI · no. 1a2b-3c4d\nmodel    gpt-6-astra")
        )
        self.assertEqual((bare["tool"], bare["date"], bare["cost"], bare["usd"], bare["prompt"]),
                         ("Codex CLI", "", "", None, ""))  # fmt: skip
        dear = gallery.entry(pack(RECEIPT.replace("$1.23", "$1,234.50")))
        self.assertEqual(dear["usd"], 1234.5)
        long = gallery.entry(pack(RECEIPT.replace("habit tracker", "x " * 300)))
        self.assertEqual(len(long["prompt"]), gallery.FIELD)
        self.assertTrue(long["prompt"].endswith("…"))
        reported = "Reported v7.9 · Claude Code · 7 Oct 2026\nREPORTED from a post\nmodel    claude-opus-5-5"
        self.assertEqual(gallery.entry(pack(reported))["kind"], "reported")

    def test_bad_links_stay_out_and_a_good_one_goes_in(self):
        good = SITE + "r/#" + pack(RECEIPT)
        self.assertEqual(
            gallery.from_issue(event(form(good)))[1]["model"], "claude-opus-5-5"
        )  # the control
        full = zlib.compressobj(9, zlib.DEFLATED, -15)
        whole = full.compress(RECEIPT.encode()) + full.flush()
        bomb = zlib.compressobj(9, zlib.DEFLATED, -15)
        bomb = (
            bomb.compress(b"Receipt v7.9 \xc2\xb7 x\n" + b"a" * 10_000_000)
            + bomb.flush()
        )
        cut = pack(RECEIPT)
        cut = cut[: 3 + (len(cut) - 3) // 4 * 4 - 3]
        self.assertEqual((len(cut) - 3) % 4, 1)  # base64 can't end there: a link cut off mid-character
        bad = {
            "no receipt link": "I made a page, it cost $2",
            "more than one receipt link": form(good)
            + " and "
            + pack(RECEIPT + "\nwork     2 tool calls"),
            "cut off": cut,
            "does not unpack": pack("", raw=b"\xff" * 40),
            "is cut off": pack("", raw=whole[: len(whole) // 2]),
            "more than 64,000 bytes": pack("", raw=bomb),
            "not UTF-8": pack("", raw=zlib.compress(b"Receipt v7.9 \xff\xfe", 9)[2:-4]),
            "control characters": pack(
                "Receipt v7.9 · Claude Code\nmodel    \x1b[31mred"
            ),
            "isn't a receipt": pack("Hello there\nmodel    x"),
            "Totals isn't one run": pack(
                "Totals v7.9 · Claude Code · folder proj · by day"
            ),
            "comparison": pack(
                "Receipt v7.9 · Comparison · 2 runs · different prompts"
            ),
            "longer than 20,000": "r1." + "A" * 20_004,
        }
        for why, body in bad.items():
            with self.subTest(why):
                tracemalloc.start()
                with self.assertRaises(gallery.Refused) as cm:
                    gallery.from_issue(event(body))
                peak = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
                self.assertLess(peak, 2_000_000)  # a zip bomb is stopped, not unpacked (it unpacks to 10 MB)
                words = {"Totals isn't one run": "isn't a receipt", "comparison": "comparison",
                         "is cut off": "the link is cut off", "cut off": "the link is cut off"}.get(why, why)  # fmt: skip
                self.assertIn(words, str(cm.exception))

    def test_check_replies_with_the_receipt_or_why_not(self):
        p = self.run_gallery(
            "check", self.write_event(event(form(SITE + "r/#" + pack(RECEIPT))))
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(
            "```\n" + RECEIPT + "\n```", p.stdout
        )  # the receipt as the gallery will hold it
        self.assertIn("once the repo's owner adds the `gallery` label", p.stdout)
        self.assertIn("can't check it against the log", p.stdout)
        p = self.run_gallery("check", self.write_event(event("no link here")))
        self.assertEqual(p.returncode, 1)
        self.assertIn("This can't go in the gallery: there's no receipt link", p.stdout)
        sneaky = RECEIPT.replace(
            "habit tracker",
            "x\n" + " " * 9 + "``` @someone [click](https://evil.example)",
        )
        p = self.run_gallery("check", self.write_event(event(pack(sneaky))))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(
            "````\n" + sneaky + "\n````", p.stdout
        )  # a longer fence, so the prompt can't end it

    def test_add_once(self):
        g = os.path.join(self.dir, "gallery.json")
        gallery.seed(INDEX, g)
        p = self.run_gallery(
            "add",
            self.write_event(event(form(pack(RECEIPT)), number=12, login="ana")),
            g,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"{SITE}g/#i12", p.stdout)
        with open(g, encoding="utf-8") as fh:
            entries = json.load(fh)
        self.assertEqual(len(entries), 114)
        new = entries[-1]
        self.assertEqual(
            (new["issue"], new["by"], new["kind"], new["link"]),
            (12, "ana", "sent", pack(RECEIPT)),
        )
        self.assertRegex(new["added"], r"^\d{4}-\d\d-\d\d$")
        again = self.run_gallery(
            "add", self.write_event(event(pack(RECEIPT), number=13)), g
        )
        self.assertEqual(again.returncode, 1)
        self.assertIn("in the gallery already (from issue #12)", again.stdout)
        site = entries[0]["link"]
        p = self.run_gallery("add", self.write_event(event(site, number=14)), g)
        self.assertIn("from the site's own runs", p.stdout)
        other = pack(RECEIPT.replace("$1.23", "$2.00"))
        p = self.run_gallery("add", self.write_event(event(other, number=12)), g)
        self.assertIn("issue #12 is in the gallery already", p.stdout)
        p = self.run_gallery("add", self.write_event(event(other, number=15)), g)
        self.assertEqual(
            p.returncode, 0, p.stdout
        )  # a different receipt from a new issue still goes in
        with open(g, encoding="utf-8") as fh:
            self.assertEqual(len(json.load(fh)), 115)
        bad = self.run_gallery("add", self.write_event(event("nothing", number=16)), g)
        self.assertEqual(bad.returncode, 1)
        with open(g, encoding="utf-8") as fh:
            self.assertEqual(len(json.load(fh)), 115)  # a refusal writes nothing


if __name__ == "__main__":
    unittest.main()
