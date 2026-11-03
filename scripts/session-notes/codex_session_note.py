#!/usr/bin/env python3
"""SessionEnd hook: 会話ログを要約して Obsidian 保管庫 (~/work/notes) にノートとして残す。

フック本体はすぐ終わり、要約処理はバックグラウンドで走る。
同じセッションが再開・再終了したら、同じノートを最新の内容で上書きする。
ログ: ~/.codex/hooks/session_note.log
手動実行: python3 ~/.codex/hooks/session_note.py --run <transcript.jsonl> [cwd]
"""
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VAULT = Path.home() / "work" / "notes"
SESSIONS = VAULT / "sessions"
PROJECTS = VAULT / "projects"
LOG = Path.home() / ".codex" / "hooks" / "session_note.log"
GUARD_ENV = "CLAUDE_SESSION_NOTE"
MODEL = "sonnet"
MIN_USER_TURNS = 2          # これ未満の短いセッションはノートにしない
STOP_MIN_NEW_TURNS = 3      # Stop 時: 前回の要約から新しいユーザー発言がこれ以上、または
STOP_MIN_SECONDS = 600      #          新しい発言が1回以上あり、これだけ経過したら要約する
STATE = Path.home() / ".codex" / "hooks" / "session_note.state.json"
RUN_LOCK = VAULT / ".session_note.run.lock"
MAX_CHARS = 120_000         # 要約に渡す会話テキストの上限
SKIP_TOOLS = {"mcp__ccd_turn__update_plan", "ToolSearch", "TodoWrite"}

SYSTEM_PROMPT = """あなたは開発作業の記録係です。Codex の会話ログを読み、
後から見返して経緯・判断・手順を再現できる日本語の Markdown ノートを書きます。

出力形式（これ以外は何も書かない。コードフェンスで囲まない）:
1行目: SLUG: <英小文字・数字・ハイフンのみ、3〜6語、内容を表す>
2行目: TITLE: <日本語の短いタイトル>
3行目: PROJECTS: <関係するリポジトリ名をカンマ区切り。なければ空>
4行目: TAGS: <小文字の英単語タグをカンマ区切り、2〜5個>
5行目以降: ノート本文（見出しは ## から）

本文の構成:
## 目的
## やったこと      … 時系列の番号付きリスト。何を・なぜ
## 決めたこと      … 判断とその理由。選ばなかった案があれば併記
## コマンド・設定  … 再現に必要なコマンド、変更したファイルと要点（コードブロック）
## 問題と解決      … エラーや詰まった点と対処（なければ節ごと省く）
## 残課題          … - [ ] 形式のチェックリスト（なければ節ごと省く）

ルール:
- ログにない事実を作らない。未確認・未完了のことはそう書く
- 関係するリポジトリやノートは Obsidian の [[名前]] 形式でリンクする
- パスワード・トークン・鍵などの秘密情報は書かない（伏せ字にする）
- 雑談やツール操作の細部は省き、再現と判断の理解に必要なことに絞る
"""


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")


def strip_reminders(text):
    return re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S).strip()


def clip(text, n):
    text = text.strip()
    return text if len(text) <= n else text[:n] + " …(略)"


def condense(transcript):
    """Read only public conversation messages; event_msg duplicates are ignored."""
    lines, title, turns, first, last = [], None, 0, None, None
    for raw in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue  # a live rollout may end with an incomplete line
        if not isinstance(row, dict):
            continue
        p = row.get("payload", {})
        if not isinstance(p, dict):
            continue
        if row.get("type") == "session_meta":
            title = p.get("title") or title
        if row.get("type") != "response_item" or p.get("type") != "message":
            continue
        role = p.get("role")
        if role not in ("user", "assistant") or p.get("phase") == "analysis":
            continue
        content = p.get("content", [])
        if not isinstance(content, list):
            continue
        text = "\n".join(x.get("text", "") for x in content
                         if isinstance(x, dict) and x.get("type") in ("input_text", "output_text", "text")
                         and isinstance(x.get("text"), str))
        text = strip_reminders(text)
        # Codex injects workspace instructions and environment envelopes as user messages.
        if not text or text.startswith(("# AGENTS.md instructions", "<environment_context>",
                                       "<external_codex_apps_open_page>")):
            continue
        ts = row.get("timestamp")
        first = first or ts
        last = ts or last
        if role == "user":
            turns += 1
        lines.append("\n### " + ("ユーザー" if role == "user" else "Codex") + "\n" + text)
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        half = MAX_CHARS // 2
        text = text[:half] + "\n…(中略)…\n" + text[-half:]
    return text, title, turns, first, last


def session_id(transcript):
    for raw in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
            if row.get("type") == "session_meta":
                value = row.get("payload", {}).get("id")
                if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]+", value):
                    return "codex-" + value
        except (ValueError, AttributeError):
            continue
    raise ValueError("Codex session_meta.id missing")


def claude_bin():
    """フックの PATH に claude が無い環境（macOS の GUI 経由など）のために、よくある場所も探す。"""
    found = shutil.which("claude")
    if found:
        return found
    for c in ("~/.local/bin/claude", "~/.claude/local/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        c = os.path.expanduser(c)
        if os.access(c, os.X_OK):
            return c
    return "claude"


def summarize(convo, title, cwd):
    prompt = (
        f"作業ディレクトリ: {cwd}\n"
        f"セッション名: {title or '(なし)'}\n"
        f"既存のプロジェクトノート: {', '.join(p.stem for p in PROJECTS.glob('*.md')) or '(なし)'}\n\n"
        f"--- 会話ログ ---\n{convo}"
    )
    # デスクトップアプリから引き継いだ接続設定は外し、CLI 自身のログインを使う
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CLAUDE_CODE_") and k not in ("ANTHROPIC_BASE_URL", "CLAUDECODE")}
    env[GUARD_ENV] = "1"
    r = subprocess.run(
        [claude_bin(), "-p", "--model", MODEL, "--no-session-persistence", "--tools", "",
         "--settings", '{"disableAllHooks": true}', "--system-prompt", SYSTEM_PROMPT],
        input=prompt, capture_output=True, text=True, env=env, timeout=900,
    )
    if r.returncode != 0:
        raise RuntimeError(f"summary provider failed ({r.returncode})")
    return r.stdout.strip()


def parse(out):
    meta, body = {}, []
    lines = out.splitlines()
    i = 0
    while i < len(lines) and i < 8:
        m = re.match(r"^(SLUG|TITLE|PROJECTS|TAGS):\s*(.*)$", lines[i].strip())
        if not m:
            if lines[i].strip() == "":
                i += 1
                continue
            break
        meta[m.group(1)] = m.group(2).strip()
        i += 1
    body = "\n".join(lines[i:]).strip()
    split = lambda s: [x.strip() for x in (s or "").split(",") if x.strip()]
    slug = re.sub(r"[^a-z0-9-]+", "-", meta.get("SLUG", "").lower()).strip("-") or "session"
    return slug, meta.get("TITLE") or "作業記録", split(meta.get("PROJECTS")), split(meta.get("TAGS")), body


def find_existing(session_id):
    for p in SESSIONS.glob("*.md"):
        head = p.read_text(encoding="utf-8")[:1000]
        if f"session_id: {session_id}" in head:
            return p
    return None


def link_projects(note_name, title, projects):
    for proj in projects:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", proj):
            continue
        pf = PROJECTS / f"{proj}.md"
        if not pf.exists():
            continue
        text = pf.read_text(encoding="utf-8")
        if f"[[{note_name}]]" in text:
            continue
        if "## セッション" not in text:
            text = text.rstrip() + "\n\n## セッション\n"
        text = text.rstrip() + f"\n- [[{note_name}]] — {title}\n"
        pf.write_text(text, encoding="utf-8")


def git(*args):
    return subprocess.run(["git", "-C", str(VAULT), *args], capture_output=True, text=True)


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temp.replace(STATE)


def run(transcript, cwd, session_id, mode="end"):
    # 要約は同時に1つだけ。Stop は混んでいたら諦め(次のターンで追いつく)、終了時は順番を待つ
    with open(RUN_LOCK, "w") as rl:
        try:
            fcntl.flock(rl, fcntl.LOCK_EX | (fcntl.LOCK_NB if mode == "stop" else 0))
        except BlockingIOError:
            log(f"skip {session_id}: another summary is running")
            return
        write_note(transcript, cwd, session_id, mode)


def write_note(transcript, cwd, session_id, mode):
    convo, title, user_turns, first_ts, last_ts = condense(transcript)
    if user_turns < MIN_USER_TURNS:
        log(f"skip {session_id}: user turns={user_turns}")
        return
    state = load_state()
    prev = state.get(session_id, {})
    new_turns = user_turns - prev.get("turns", 0)
    fingerprint = hashlib.sha256(convo.encode()).hexdigest()
    if prev.get("fingerprint") == fingerprint:
        return
    if mode == "stop" and new_turns <= 0:
        return
    if mode == "stop":
        since = prev.get("at")
        if since is None:
            try:
                since = datetime.datetime.fromisoformat(first_ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                since = 0
        if new_turns < STOP_MIN_NEW_TURNS and datetime.datetime.now().timestamp() - since < STOP_MIN_SECONDS:
            return
    out = summarize(convo, title, cwd)
    slug, ntitle, projects, tags, body = parse(out)
    if not body:
        raise RuntimeError(f"empty summary: {out[:500]}")

    def local_date(ts):
        try:
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        except Exception:
            return datetime.datetime.now().astimezone()
    start, end = local_date(first_ts), local_date(last_ts)

    with open(VAULT / ".session_note.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        SESSIONS.mkdir(parents=True, exist_ok=True)
        path = find_existing(session_id) or SESSIONS / f"{start:%Y-%m-%d}-{slug}.md"
        n = 2
        while path.exists() and session_id not in path.read_text(encoding="utf-8")[:1000]:
            path = SESSIONS / f"{start:%Y-%m-%d}-{slug}-{n}.md"
            n += 1
        targets = [str(path.relative_to(VAULT))]
        targets += [f"projects/{proj}.md" for proj in projects
                    if re.fullmatch(r"[A-Za-z0-9_-]+", proj) and (PROJECTS / f"{proj}.md").exists()]
        dirty = git("status", "--porcelain", "--", *targets)
        if dirty.returncode or dirty.stdout.strip():
            raise RuntimeError("target note has local edits; preserve them before retry")
        originals = {rel: (VAULT / rel).read_bytes() if (VAULT / rel).exists() else None
                     for rel in targets}
        fm = [
            "---",
            f"date: {start:%Y-%m-%d}",
            f"started: {start:%Y-%m-%d %H:%M}",
            f"ended: {end:%Y-%m-%d %H:%M}",
            f"tags: [session{''.join(', ' + t for t in tags)}]",
            f"projects: [{', '.join(projects)}]",
            f"session_id: {session_id}",
            f"session_title: {title or ''}",
            f"cwd: {cwd}",
            f"transcript: {transcript}",
            "generated_by: session-note hook",
            "---",
        ]
        path.write_text("\n".join(fm) + f"\n\n# {ntitle}\n\n{body}\n", encoding="utf-8")
        link_projects(path.stem, ntitle, projects)

        # Do not include unrelated staged edits or other sessions in this commit.
        paths = [str(path.relative_to(VAULT))]
        paths += [f"projects/{proj}.md" for proj in projects
                  if re.fullmatch(r"[A-Za-z0-9_-]+", proj) and (PROJECTS / f"{proj}.md").exists()]
        try:
            if git("add", "--", *paths).returncode:
                raise RuntimeError("git add failed")
            changed = git("diff", "--quiet", "HEAD", "--", *paths).returncode
            if changed not in (0, 1):
                raise RuntimeError("git diff failed")
            if changed and git("commit", "--only", "-m", f"session: {ntitle}", "--", *paths).returncode:
                raise RuntimeError("git commit failed")
        except RuntimeError:
            # All targets were clean before this transaction; restore only our changes.
            git("reset", "--quiet", "HEAD", "--", *paths)
            for rel, original in originals.items():
                target = VAULT / rel
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(original)
            raise
        for args in (("pull", "--rebase", "--autostash", "--quiet"), ("push", "--quiet")):
            if git(*args).returncode:
                raise RuntimeError("git sync failed; retry next hook")
    state[session_id] = {"fingerprint": fingerprint, "turns": user_turns, "at": datetime.datetime.now().timestamp()}
    save_state(state)
    log(f"wrote {path} ({session_id}, {mode})")


def main():
    if (Path(__file__).parent / "session_note.disabled").exists():
        log("disabled: awaiting explicit provider and repository sync authorization")
        return
    if os.environ.get(GUARD_ENV):  # 要約用の claude -p 自身では何もしない
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "--run":
        transcript = sys.argv[2]
        cwd = (sys.argv[3] if len(sys.argv) > 3 else "") or os.getcwd()
        mode = sys.argv[4] if len(sys.argv) > 4 else "end"
        try:
            run(transcript, cwd, session_id(transcript), mode)
        except Exception as e:
            log(f"error {transcript}: {e}")
            raise
        return
    # フックとして呼ばれた場合: stdin の JSON を読んでバックグラウンドで処理する
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return
    if not isinstance(data, dict):
        return
    transcript = data.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return
    subprocess.Popen(
        [sys.executable, __file__, "--run", transcript, data.get("cwd") or "",
         "stop" if data.get("hook_event_name") == "Stop" else "end"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
