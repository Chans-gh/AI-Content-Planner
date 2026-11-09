"""fetch_article.py 的离线测试：在 127.0.0.1 上起一个假网站，不连外网，只用标准库。

    python3 -m unittest discover -s skills/ai-content-planner/scripts/tests
"""
import contextlib
import http.server
import io
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fetch_article  # noqa: E402

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Site title</title>
<meta name="author" content="Ann Analyst"><meta property="article:published_time" content="2026-03-01">
<script>var x = "<p>not text</p>";</script>
</head><body>
<nav><a href="/">Home</a> <p>Menu text that is not the article</p></nav>
<header><img src="/themes/site/logo.png" alt="logo"></header>
<article>
  <h1>The Top 100 Gen AI Apps</h1>
  <p>First paragraph of the report &amp; more.
  <h2>Web rankings</h2>
  <p>Second paragraph, before the chart.</p>
  <figure><img src="/img/rank-400x300.png" srcset="/img/rank-400x300.png 400w, /img/rank-1200x900.png 1200w" alt="chart">
    <figcaption>Top 50 web products by monthly visits</figcaption></figure>
  <ul><li>ChatGPT stays first<li>New entrants: 11</ul>
  <blockquote><p>We expect the list to change fast.</p></blockquote>
  <img data-src="/img/mobile-chart.png" src="data:image/gif;base64,R0lGOD" alt="Chart titled Mobile apps by MAU">
  <img src="/img/icon.png" alt="small icon">
  <img src="/img/rank-1200x900.png" alt="the same chart again">
  <img src="/img/not-an-image.png" alt="broken link to a chart">
  <div class="share-buttons"><p>Share this on social</p></div>
</article>
<footer><p>Copyright</p></footer>
</body></html>"""
GBK_PAGE = '<html><head><meta charset="gbk"></head><body><main><h1>中文标题</h1><p>第一段正文。</p></main></body></html>'
SIZES = {"rank-400x300.png": (400, 300), "rank-1200x900.png": (1200, 900), "rank.png": (1600, 1200),
         "mobile-chart.png": (800, 600), "icon.png": (64, 64)}


def png(size, colour):
    """一张纯色 PNG，只用标准库。"""
    w, h = size
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + bytes(colour) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


class Handler(http.server.BaseHTTPRequestHandler):
    files = {"/article": (PAGE.encode(), "text/html; charset=utf-8"),
             "/gbk": (GBK_PAGE.encode("gbk"), "text/html"),
             "/data.json": (b"{}", "application/json"),
             "/img/not-an-image.png": (b"<html>404</html>", "image/png"),
             "/themes/site/logo.png": (png((600, 400), (1, 1, 1)), "image/png")}
    for i, (name, size) in enumerate(SIZES.items()):
        files[f"/img/{name}"] = (png(size, (40 * i, 90, 150)), "image/png")

    def do_GET(self):
        path = self.path.split("?")[0]
        body, ctype = self.files.get(path, (b"not found", "text/html"))
        self.send_response(200 if path in self.files else 404)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class FetchArticle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.url = cls.base + "/article"
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.out = fetch_article.main([cls.url, str(cls.dir), "--name", "report"])
            cls.with_images = fetch_article.main([cls.url, str(cls.dir), "--name", "report-img", "--images"])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_output_files(self):
        self.assertEqual(self.out, self.dir / "source" / "report")
        for name in ("page.html", "article.md", "charts.md", "charts.json", ".gitignore"):
            self.assertTrue((self.out / name).is_file(), name)
        self.assertEqual((self.out / ".gitignore").read_text(encoding="utf-8").splitlines()[1:], ["page.html", "images/"])

    def test_main_text_in_order_without_page_chrome(self):
        text = (self.out / "article.md").read_text(encoding="utf-8")
        self.assertIn("不可信数据", text.splitlines()[0])
        self.assertIn("# The Top 100 Gen AI Apps", text)
        self.assertIn("- 作者：Ann Analyst", text)
        self.assertIn("- 发布：2026-03-01", text)
        order = ["## The Top 100 Gen AI Apps", "First paragraph of the report & more.", "### Web rankings", "Second paragraph",
                 "[图 1：Top 50 web products by monthly visits]", "- ChatGPT stays first", "- New entrants: 11", "> We expect"]
        positions = [text.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Web rankings Second", text)                                    # 没闭合的 <p> 不吞后面的标题
        for chrome in ("Menu text", "Share this", "Copyright", "not text"):
            self.assertNotIn(chrome, text)

    def test_charts_largest_version_no_logo_icon_duplicate_or_broken(self):
        charts = json.loads((self.out / "charts.json").read_text(encoding="utf-8"))
        self.assertFalse((self.out / "images").exists())                                # 默认不下载
        self.assertEqual([c["file"] for c in charts], ["", ""])
        self.assertEqual([c["size"] for c in charts], [[1600, 1200], [800, 600]])     # WordPress 原图、懒加载的图
        self.assertEqual(charts[0]["title"], "Top 50 web products by monthly visits")
        self.assertEqual(charts[0]["title_from"], "figcaption")
        self.assertEqual(charts[1]["title"], "Mobile apps by MAU")                      # 去掉了 Chart titled
        self.assertEqual(charts[0]["section"], "Web rankings")
        table = (self.out / "charts.md").read_text(encoding="utf-8")
        self.assertIn("共 2 张", table)
        self.assertIn("没下载，要用原图加 --images 重抓", table)
        self.assertIn("| 1 | — | 1600×1200 |", table)

    def test_images_downloaded_only_with_flag_and_within_total(self):
        charts = json.loads((self.with_images / "charts.json").read_text(encoding="utf-8"))
        self.assertEqual([c["size"] for c in charts], [[1600, 1200], [800, 600]])
        self.assertEqual(sorted(p.name.split("-", 1)[0] for p in (self.with_images / "images").iterdir()), ["01", "02"])
        self.assertIn("| 1 | `images/01-", (self.with_images / "charts.md").read_text(encoding="utf-8"))
        first = charts[0]["bytes"]
        cap, fetch_article.MAX_IMAGES_TOTAL = fetch_article.MAX_IMAGES_TOTAL, first + 1     # 只装得下第一张
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                out = fetch_article.main([self.url, tmp, "--name", "capped", "--images"])
                capped = json.loads((out / "charts.json").read_text(encoding="utf-8"))
                self.assertEqual([bool(c["file"]) for c in capped], [True, False])
                self.assertEqual(len(list((out / "images").iterdir())), 1)
                self.assertIn("1 张超过", (out / "charts.md").read_text(encoding="utf-8"))
        finally:
            fetch_article.MAX_IMAGES_TOTAL = cap

    def test_charset_from_meta(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = fetch_article.main([self.base + "/gbk", tmp, "--name", "cn"])
            text = (out / "article.md").read_text(encoding="utf-8")
        self.assertIn("# 中文标题", text)
        self.assertIn("第一段正文。", text)

    def test_only_http_html_existing_folder_and_safe_names(self):
        with self.assertRaises(ValueError):
            fetch_article.fetch("file:///etc/passwd", 1000)
        with self.assertRaises(SystemExit):
            fetch_article.main([self.url, str(self.dir / "missing")])
        with self.assertRaises(SystemExit):
            fetch_article.main([self.url, str(self.dir), "--name", "../escape"])
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit) as stop:
            fetch_article.main([self.base + "/data.json", tmp, "--name", "j"])
        self.assertIn("不是网页", str(stop.exception))

    def test_several_links_side_by_side_failures_listed_at_the_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            links = Path(tmp) / "links.txt"
            links.write_text(f"# 清单\n{self.url}?a named-one\n\n{self.base}/gone\n", encoding="utf-8")
            log = io.StringIO()
            with contextlib.redirect_stdout(log), self.assertRaises(SystemExit) as stop:
                fetch_article.main([self.url, f"{self.url}?b", "--list", str(links), tmp, "--jobs", "3"])
            self.assertEqual(stop.exception.code, 1)
            got = sorted(p.name for p in (Path(tmp) / "source").iterdir() if (p / "article.md").is_file())
            self.assertEqual(got, ["127-0-0-1-article", "127-0-0-1-article-2", "named-one"])   # 同一网站：路径最后一段区分
            self.assertIn("成功 3，失败 1", log.getvalue())
            self.assertRegex(log.getvalue(), r"失败 127-0-0-1-gone：.*/gone")

    def test_names_for_links_from_one_site_and_name_needs_one_link(self):
        self.assertEqual(fetch_article.names_for(["https://www.a16z.com/top-100/", "https://a16z.com/news/x", "https://openai.com/"]),
                         ["a16z-com-top-100", "a16z-com-x", "openai-com"])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            fetch_article.main([self.url, self.url, str(self.dir), "--name", "x"])


class TitleFor(unittest.TestCase):
    def test_file_name_only_when_it_has_words(self):
        img = lambda src: fetch_article.parse(f'<img src="{src}">').find("img")
        self.assertEqual(fetch_article.title_for(img("/u/top-gen-ai-web-list-1200x800.png"), ["H"]), ("top gen ai web list", "file name"))
        self.assertEqual(fetch_article.title_for(img("/u/55182696113-0c4398702d-o-2.jpg"), ["Launch"]), ("Launch", "heading"))


class ImageInfo(unittest.TestCase):
    def test_formats_from_header(self):
        self.assertEqual(fetch_article.image_info(png((7, 5), (0, 0, 0))), ("png", (7, 5)))
        self.assertEqual(fetch_article.image_info(b"GIF89a" + struct.pack("<HH", 320, 200) + b"\x00" * 8), ("gif", (320, 200)))
        jpeg = (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
                + b"\xff\xc4" + struct.pack(">H", 4) + b"\x00\x00"
                + b"\xff\xc2" + struct.pack(">HBHH", 17, 8, 480, 640) + b"\x03" + b"\x00" * 9)
        self.assertEqual(fetch_article.image_info(jpeg), ("jpg", (640, 480)))
        vp8x = b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x0a\x00\x00\x00" + b"\x00" * 4 + (1199).to_bytes(3, "little") + (899).to_bytes(3, "little")
        self.assertEqual(fetch_article.image_info(vp8x), ("webp", (1200, 900)))
        vp8 = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 4 + b"\x00" * 3 + b"\x9d\x01\x2a" + struct.pack("<HH", 800, 600)
        self.assertEqual(fetch_article.image_info(vp8), ("webp", (800, 600)))
        bits = (500 - 1) | ((300 - 1) << 14)
        vp8l = b"RIFF\x00\x00\x00\x00WEBPVP8L" + b"\x00" * 4 + b"\x2f" + bits.to_bytes(4, "little")
        self.assertEqual(fetch_article.image_info(vp8l), ("webp", (500, 300)))
        self.assertIsNone(fetch_article.image_info(b"<html>not found</html>"))
        self.assertIsNone(fetch_article.image_info(jpeg[:30]))                         # 只读到开头，尺寸还没出现


if __name__ == "__main__":
    unittest.main()
