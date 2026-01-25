import os, subprocess, sqlite3, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("JOBS_DB_PATH", str(REPO / "data" / "raw" / "jobs.sqlite3"))
OUT = REPO / "repo_state.md"

def sh(cmd):
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    out = (p.stdout + "\n" + p.stderr).strip()
    return p.returncode, out

def md_block(title, content):
    return f"\n## {title}\n\n```text\n{content}\n```\n"

def scan_sqlite(db_path):
    if not Path(db_path).exists():
        return f"DB not found at {db_path} (set JOBS_DB_PATH)."
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()
    lines = [f"DB: {db_path}",
             f"Tables ({len(tables)}): " + ", ".join(t[0] for t in tables)]
    jobs_candidates = [t[0] for t in tables if "job" in t[0].lower()]
    if jobs_candidates:
        t = jobs_candidates[0]
        cols = cur.execute(f"PRAGMA table_info({t});").fetchall()
        colnames = [c[1] for c in cols]
        count = cur.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
        lines += [f"Primary jobs table guess: {t}",
                  f"Row count: {count}",
                  "Columns: " + ", ".join(colnames)]
    con.close()
    return "\n".join(lines)

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [f"# Repo State Snapshot\n\nGenerated: {now}\n\nRepo: {REPO}\n"]

    for name, cmd in [
        ("Git status", ["git", "status", "-sb"]),
        ("Git last 20 commits", ["git", "log", "--oneline", "-n", "20"]),
        ("Git branches", ["git", "branch", "--all"]),
    ]:
        rc, out = sh(cmd)
        parts.append(md_block(name, f"(rc={rc})\n{out}"))

    rc, out = sh(["python", "--version"])
    parts.append(md_block("Python", f"(rc={rc})\n{out}"))

    # Improved project tree command (skip .git, .venv, etc.)
    tree_cmd = "find . -maxdepth 4 -not -path '*/.*' -not -path './backend/venv3.11/*' -not -path './node_modules/*' | sed 's|^./||' | sort"
    rc, out = sh(["bash", "-lc", f"command -v tree >/dev/null && tree -L 4 -I '.git|venv*|.venv*|node_modules' || {tree_cmd}"])
    parts.append(md_block("Project tree", f"(rc={rc})\n{out}"))

    # Try to find ruff and pytest in venv
    venv_bin = REPO / "backend" / "venv3.11" / "bin"
    ruff_path = str(venv_bin / "ruff") if (venv_bin / "ruff").exists() else "ruff"
    pytest_path = str(venv_bin / "pytest") if (venv_bin / "pytest").exists() else "pytest"

    for name, cmd in [
        ("Ruff", ["bash", "-lc", f"{ruff_path} --version && {ruff_path} check . && {ruff_path} format --check ."]),
        ("Pytest", ["bash", "-lc", f"{pytest_path} -q"]),
        ("Mypy (optional)", ["bash", "-lc", "mypy --version && mypy src || echo 'mypy not configured'"]),
    ]:
        rc, out = sh(cmd)
        parts.append(md_block(name, f"(rc={rc})\n{out}"))

    parts.append(md_block("SQLite summary", scan_sqlite(DB_PATH)))

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
