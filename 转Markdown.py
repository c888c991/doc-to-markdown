# -*- coding: utf-8 -*-
"""
批量把办公文档转成便于 AI 阅读的 Markdown。

用法一（推荐）：把文件丢进「待转换」文件夹，双击「一键转换.bat」。
用法二（命令行）：
    python 转Markdown.py                         处理「待转换」文件夹
    python 转Markdown.py 某个文件.docx            只转这一个文件
    python 转Markdown.py D:\资料\合同           转整个文件夹（会递归子目录）
    python 转Markdown.py D:\资料\合同 D:\输出    指定输出目录
"""

import sys
from pathlib import Path

# 脚本所在目录，作为默认的工作根目录
BASE = Path(__file__).resolve().parent
DEFAULT_SRC = BASE / "待转换"
DEFAULT_DST = BASE / "转换结果"

# 能直接转换的格式
SUPPORTED = {
    ".docx", ".pptx", ".xlsx", ".pdf",
    ".html", ".htm", ".epub",
    ".csv", ".json", ".xml",
}

# 需要额外处理的老格式：后缀 -> 提示
UNSUPPORTED = {
    ".doc": "老版 Word（.doc）不支持，请先用 Word 另存为 .docx",
    ".ppt": "老版 PPT（.ppt）不支持，请先另存为 .pptx",
    ".xls": "老版 Excel（.xls）需要额外组件，请另存为 .xlsx",
}


# ----------------------------------------------------------------------
# 输出清理：MarkItDown 转 Word 表格时会留下一行空表头，
# 这会让 AI 读不懂表格，这里把真实首行提升为表头。
# ----------------------------------------------------------------------
def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _split_cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_empty_row(line: str) -> bool:
    return all(c == "" for c in _split_cells(line))


def _is_separator(line: str) -> bool:
    if not _is_table_row(line):
        return False
    cells = _split_cells(line)
    return all(c and set(c) <= set("-: ") and "-" in c for c in cells)


def fix_empty_header(text: str) -> str:
    """把「空表头 + 分隔线 + 真实首行」修正为「真实首行 + 分隔线」。"""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if (
            i + 2 < len(lines)
            and _is_table_row(lines[i])
            and _is_empty_row(lines[i])
            and _is_separator(lines[i + 1])
            and _is_table_row(lines[i + 2])
            and not _is_empty_row(lines[i + 2])
        ):
            out.append(lines[i + 2])
            out.append(lines[i + 1])
            i += 3
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


# ----------------------------------------------------------------------
# 收集待转换文件
# ----------------------------------------------------------------------
def collect(src: Path):
    """返回 (文件列表, 相对路径基准目录)。"""
    if src.is_file():
        return [src], src.parent

    files = []
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        if p.name.startswith("~$"):          # Office 打开时产生的临时文件
            continue
        ext = p.suffix.lower()
        if ext in SUPPORTED or ext in UNSUPPORTED:
            files.append(p)
    return files, src


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
def main() -> int:
    args = [a for a in sys.argv[1:]]
    src = Path(args[0]).expanduser().resolve() if args else DEFAULT_SRC
    dst = Path(args[1]).expanduser().resolve() if len(args) > 1 else DEFAULT_DST

    print("=" * 56)
    print("办公文档  ->  Markdown")
    print("=" * 56)

    if not src.exists():
        print(f"× 找不到路径：{src}")
        return 1

    files, root = collect(src)
    if not files:
        print(f"× 「{src}」里没有找到可转换的文档。")
        print("  支持的格式：" + "、".join(sorted(SUPPORTED)))
        print("  把文件放进去再运行一次即可。")
        return 1

    print(f"源目录：{root}")
    print(f"输出到：{dst}")
    print(f"共找到 {len(files)} 个文件，开始转换……\n")

    from markitdown import MarkItDown

    converter = MarkItDown()
    done, failed, skipped = 0, [], []

    for f in files:
        ext = f.suffix.lower()
        rel = f.relative_to(root)

        if ext in UNSUPPORTED:
            skipped.append((str(rel), UNSUPPORTED[ext]))
            print(f"[跳过] {rel} —— {UNSUPPORTED[ext]}")
            continue

        target = dst / rel.with_suffix(".md")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = converter.convert(str(f)).text_content
            target.write_text(fix_empty_header(text), encoding="utf-8")
            done += 1
            print(f"[完成] {rel}")
        except Exception as e:
            failed.append((str(rel), str(e)))
            print(f"[失败] {rel} —— {e}")

    print("\n" + "=" * 56)
    print(f"转换完成：成功 {done} 个", end="")
    if skipped:
        print(f"，跳过 {len(skipped)} 个", end="")
    if failed:
        print(f"，失败 {len(failed)} 个", end="")
    print()

    if failed:
        print("\n失败明细：")
        for name, reason in failed:
            print(f"  · {name}：{reason}")

    if done:
        print(f"\n结果在：{dst}")

    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
