"""+29 font-shift decoder for the 2014 book. In this PDF the shifted font keeps spaces and
punctuation as control characters (0x03 = space, 0x11 = '.', 0x0F = ','), so a run decodes
completely. Runs may also contain real spaces between shifted words."""
import re

LIG = {"À": "fi", "Á": "fl", "Â": "ffi", "¿": "ff"}
CH = r"[\x01-\x1f!-\]ÀÁÂ¿]"
RUN = re.compile(CH + r"(?:(?:" + CH + r"| (?=" + CH + r"))*" + CH + r")?")
LOWER_SHIFTED = set(chr(c) for c in range(0x44, 0x5E)) | set("ÀÁÂ¿")


def shift(run: str) -> str:
    out = []
    tail = ""
    if run.endswith("-"):  # a real line-end hyphen, not a shifted "J"
        run, tail = run[:-1], "-"
    for ch in run:
        if ch in LIG:
            out.append(LIG[ch])
        elif ch == " ":
            out.append(" ")
        else:
            o = ord(ch)
            out.append(chr(o + 29) if 0x01 <= o <= 0x5D else ch)
    return "".join(out) + tail


def looks_shifted(run: str, nxt: str = "") -> bool:
    letters = [c for c in run if c != " "]
    ctrl = any(ord(c) < 0x20 for c in letters) or any(c in LIG for c in letters)
    if not ctrl and nxt.islower():
        return False
    frac = sum(1 for c in letters if c in LOWER_SHIFTED) / max(1, len(letters))
    if re.fullmatch(r"[\d ,.\-]+", run):
        return False
    if ctrl and len(letters) >= 3:
        return True
    return len(letters) >= 6 and frac >= 0.5 and not (run.startswith("(") and run.endswith(")"))


def decode_line(line: str) -> str:
    def repl(m):
        r = m.group(0)
        nxt = line[m.end()] if m.end() < len(line) else ""
        return "⟨" + shift(r) + "⟩" if looks_shifted(r, nxt) else r
    return RUN.sub(repl, line)


def decode_column(lines):
    return [decode_line(l) for l in lines]
