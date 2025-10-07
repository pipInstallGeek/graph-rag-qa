import re
import uuid
from pathlib import Path
import pandas as pd
from api.config import settings
from pypdf import PdfReader

def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    text = []
    for page in reader.pages:
        t = page.extract_text() or ""
        text.append(t)
    print(f'read {path}')
    return "\n".join(text)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

TOC_LINE = re.compile(r'.{3,}\.{3,}\s*\d+$')
HEADER_FOOTER = re.compile(r'^\s*(?:\d+|[ivxlcdm]+)\s*$|^\s*Table of Contents\s*$', re.I)

def clean_text_block(block: str) -> str:
    # drop typical TOC/headers/footers lines
    lines = []
    for line in block.splitlines():
        if TOC_LINE.search(line): 
            continue
        if HEADER_FOOTER.match(line.strip()):
            continue
        lines.append(line)
    text = "\n".join(lines)
    # collapse multiple spaces/newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def chunk_text(txt: str, max_chars: int = 2000, overlap: int = 300) -> list[str]:
    assert max_chars > 0 and 0 <= overlap < max_chars, "overlap must be < max_chars"
    # light cleanup
    txt = re.sub(r'\n{2,}', '\n\n', txt).strip()
    n = len(txt)
    chunks = []
    start = 0
    max_iters = 1_000_000  # hard safety

    iters = 0
    while start < n and iters < max_iters:
        iters += 1
        end = min(start + max_chars, n)

        cut = txt.rfind("\n\n", start, end)
        if cut == -1:
            cut = txt.rfind(". ", start, end)
        if cut == -1 or cut <= start + 500:
            cut = end
        chunks.append(txt[start:cut].strip())
        if cut == n:
            break
        if cut == end:
            next_start = end - overlap
        else:
            next_start = cut  # allow overlap via next cut search window

        if next_start <= start:
            next_start = min(start + (max_chars - overlap), n)

        start = next_start

    return [c for c in chunks if c]


def main():
    raw_dir = Path(settings.data_dir) / "raw"
    out_path = Path(settings.processed_dir) / "docs.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in raw_dir.glob("**/*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".pdf"}:
            print(f'file : {p}')
            text = read_pdf(p)
        elif p.suffix.lower() in {".md", ".txt"}:
            text = read_text(p)
        else:
            continue
        chunks = chunk_text(text)
        for i, ch in enumerate(chunks):
            ch = clean_text_block(ch)
            if not ch or len(ch) < 80:
                continue
            rows.append({
                "id": str(uuid.uuid4()),
                "doc_name": p.name,
                "chunk_idx": i,
                "text": ch
            })
    if not rows:
        print(f"No files found in {raw_dir}. Drop a few PDFs/MD/TXT there.")
        return

    df = pd.DataFrame(rows)
    df.to_parquet(out_path, index=False)
    print(f"[ingest] Wrote {len(df)} chunks -> {out_path}")

if __name__ == "__main__":
    main()
