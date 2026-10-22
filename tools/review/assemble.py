import sys
from pathlib import Path
s = Path(sys.argv[1])
html = (s / "review_template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", (s / "review_data.json").read_text(encoding="utf-8"))
(s / "hornlab_review.html").write_text(html, encoding="utf-8")
print(len(html))
