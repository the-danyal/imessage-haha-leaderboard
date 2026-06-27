#!/usr/bin/env python3
"""
iMessage Haha Reaction Leaderboard
Reads directly from ~/Library/Messages/chat.db (Mac only).
Requires Terminal to have Full Disk Access:
  System Settings → Privacy & Security → Full Disk Access → enable Terminal
"""

import sqlite3
import shutil
import os
import sys
import json
import tempfile
import datetime
from collections import defaultdict
from pathlib import Path

DB_PATH = Path.home() / "Library/Messages/chat.db"
NAMES_PATH = Path(__file__).parent / "names.json"

HAHA_TYPE = 2003
HAHA_REMOVE_TYPE = 3003
APPLE_EPOCH = datetime.datetime(2001, 1, 1)


def load_names():
    """Load names.json — phone→name mappings plus optional MY_NAME key."""
    if not NAMES_PATH.exists():
        print(f"ERROR: {NAMES_PATH} not found.")
        print("Copy names_example.json to names.json and fill in your group's numbers.")
        sys.exit(1)
    data = json.loads(NAMES_PATH.read_text())
    # strip comments-style keys (shouldn't be in real JSON but just in case)
    return {k: v for k, v in data.items() if not k.startswith("//")}


def get_my_name(name_map):
    return name_map.pop("MY_NAME", "Me")


def imessage_date(ts_ns):
    return APPLE_EPOCH + datetime.timedelta(seconds=ts_ns / 1e9)


def copy_db():
    tmp = tempfile.mktemp(suffix=".db")
    try:
        shutil.copy2(DB_PATH, tmp)
    except PermissionError:
        print("ERROR: Can't read chat.db.")
        print("Fix: System Settings → Privacy & Security → Full Disk Access → enable Terminal")
        sys.exit(1)
    return tmp


def list_group_chats(conn):
    cur = conn.execute("""
        SELECT c.rowid, c.chat_identifier, c.display_name, COUNT(cmj.message_id) as msg_count
        FROM chat c
        JOIN chat_message_join cmj ON c.rowid = cmj.chat_id
        WHERE c.style = 43
        GROUP BY c.rowid
        ORDER BY msg_count DESC
    """)
    return cur.fetchall()


def pick_chat(chats):
    print("\n=== GROUP CHATS FOUND ===\n")
    for i, (rowid, identifier, display_name, count) in enumerate(chats):
        name = display_name or identifier
        print(f"  [{i+1}] {name}  ({count:,} messages)")
    print()
    print("Enter one number, or multiple separated by commas to merge (e.g. 1,2):")
    while True:
        try:
            raw = input("Pick chat number(s): ").strip()
            choices = [int(x.strip()) - 1 for x in raw.split(",")]
            if all(0 <= c < len(chats) for c in choices):
                return [chats[c][0] for c in choices]
        except (ValueError, KeyboardInterrupt):
            pass
        print("Invalid choice, try again.")


def get_current_members(conn, chat_ids):
    """Return set of handle_ids currently in these chats."""
    placeholders = ",".join("?" * len(chat_ids))
    cur = conn.execute(
        f"SELECT DISTINCT handle_id FROM chat_handle_join WHERE chat_id IN ({placeholders})",
        chat_ids
    )
    return {row[0] for row in cur.fetchall()}


def get_handle_map(conn):
    cur = conn.execute("SELECT rowid, id FROM handle")
    return {row[0]: row[1] for row in cur.fetchall()}


def get_attachment_map(conn):
    """Returns {message_guid: (filename, mime_type)} for messages with attachments."""
    cur = conn.execute("""
        SELECT m.guid, a.filename, a.mime_type
        FROM message m
        JOIN message_attachment_join maj ON m.rowid = maj.message_id
        JOIN attachment a ON maj.attachment_id = a.rowid
    """)
    result = {}
    for guid, filename, mime_type in cur.fetchall():
        if filename:
            full_path = filename.replace("~", str(Path.home()), 1)
            result[guid] = (full_path, mime_type or "")
    return result


def get_messages(conn, chat_ids):
    placeholders = ",".join("?" * len(chat_ids))
    cur = conn.execute(f"""
        SELECT DISTINCT
            m.rowid,
            m.guid,
            m.text,
            m.handle_id,
            m.is_from_me,
            m.associated_message_guid,
            m.associated_message_type,
            m.date
        FROM message m
        JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        WHERE cmj.chat_id IN ({placeholders})
        ORDER BY m.date ASC
    """, chat_ids)
    return cur.fetchall()



def analyze(messages, handle_map, current_member_handle_ids, name_map, my_name):
    guid_to_sender = {}
    guid_to_text = {}
    messages_sent = defaultdict(int)
    active_reactions = {}
    hahas_given = defaultdict(int)
    hahas_received = defaultdict(int)
    msg_haha_count = defaultdict(int)

    for rowid, guid, text, handle_id, is_from_me, assoc_guid, assoc_type, date in messages:
        # Skip system/empty messages (handle_id=0, not from me, no text)
        if handle_id == 0 and not is_from_me:
            continue

        if is_from_me:
            sender_id = my_name
        else:
            if handle_id not in current_member_handle_ids:
                continue
            raw_id = handle_map.get(handle_id)
            if raw_id is None or raw_id not in name_map:
                continue  # not in our known members list
            sender_id = raw_id

        is_reaction = assoc_type in (HAHA_TYPE, HAHA_REMOVE_TYPE)

        if not is_reaction:
            if text or assoc_type == 0:
                guid_to_sender[guid] = sender_id
                guid_to_text[guid] = text if text and text.strip() else "[image/attachment]"
                messages_sent[sender_id] += 1
        else:
            clean_guid = assoc_guid.split("/")[-1] if assoc_guid else ""
            key = (sender_id, clean_guid)

            if assoc_type == HAHA_TYPE:
                if key not in active_reactions:
                    active_reactions[key] = True
                    hahas_given[sender_id] += 1
                    target_sender = guid_to_sender.get(clean_guid)
                    if target_sender:
                        hahas_received[target_sender] += 1
                        msg_haha_count[clean_guid] += 1
            elif assoc_type == HAHA_REMOVE_TYPE:
                if key in active_reactions:
                    del active_reactions[key]
                    hahas_given[sender_id] -= 1
                    target_sender = guid_to_sender.get(clean_guid)
                    if target_sender:
                        hahas_received[target_sender] -= 1
                        msg_haha_count[clean_guid] -= 1

    return hahas_given, hahas_received, messages_sent, msg_haha_count, guid_to_text, guid_to_sender


def get_context(messages, target_guid, handle_map, n=5):
    guids = [m[1] for m in messages]
    try:
        idx = guids.index(target_guid)
    except ValueError:
        return []
    start = max(0, idx - n)
    return messages[start:idx + 1]


def print_message_content(guid, text, attachment_map, indent="  "):
    """Print message text, or attachment info with option to open it."""
    if text and text != "[image/attachment]":
        print(f"{indent}\"{text[:140]}\"")
        return

    att = attachment_map.get(guid)
    if att:
        path, mime = att
        filename = Path(path).name
        print(f"{indent}[attachment: {filename}  ({mime})]")
        exists = Path(path).exists()
        if exists:
            answer = input(f"{indent}  Open this file? (y/N): ").strip().lower()
            if answer == "y":
                os.system(f"open '{path}'")
        else:
            print(f"{indent}  (file no longer on disk)")
    else:
        print(f"{indent}[image/attachment — no path found]")


def print_report(hahas_given, hahas_received, messages_sent, msg_haha_count,
                 guid_to_text, guid_to_sender, messages, handle_map, name_map, my_name, start_date,
                 attachment_map):

    all_senders = set(messages_sent.keys()) | set(hahas_given.keys()) | set(hahas_received.keys())

    display = {}
    for sid in all_senders:
        if sid == my_name:
            display[sid] = my_name
        else:
            display[sid] = name_map.get(sid, sid)

    def ratio_received(sid):
        sent = messages_sent.get(sid, 0)
        return hahas_received.get(sid, 0) / sent if sent else 0.0

    def ratio_given(sid):
        sent = messages_sent.get(sid, 0)
        return hahas_given.get(sid, 0) / sent if sent else 0.0

    W = 62
    print("\n" + "=" * W)
    print("  HAHA LEADERBOARD".center(W))
    print(f"  Since {start_date.strftime('%B %d, %Y')}".center(W))
    print("=" * W)

    for sid in sorted(all_senders, key=lambda x: hahas_received.get(x, 0), reverse=True):
        name = display[sid]
        given = hahas_given.get(sid, 0)
        received = hahas_received.get(sid, 0)
        sent = messages_sent.get(sid, 0)
        r_recv = ratio_received(sid)
        r_give = ratio_given(sid)

        print(f"\n  {name}")
        print(f"    Hahas Given:          {given:>6,}")
        print(f"    Hahas Received:       {received:>6,}")
        print(f"    Messages Sent:        {sent:>6,}")
        print(f"    Hahas Received/Msg:   {r_recv:>8.3f}")
        print(f"    Hahas Given/Msg:      {r_give:>8.3f}")

        their_msgs = {g: c for g, c in msg_haha_count.items()
                      if guid_to_sender.get(g) == sid and c > 0}
        if their_msgs:
            top_guid = max(their_msgs, key=their_msgs.get)
            top_count = their_msgs[top_guid]
            top_text = guid_to_text.get(top_guid, "[no text]")
            print(f"\n    Most laughed message ({top_count} hahas):")
            print_message_content(top_guid, top_text, attachment_map, indent="    > ")
            context = get_context(messages, top_guid, handle_map, n=5)
            if len(context) > 1:
                print("    Context:")
                for m in context[:-1]:
                    raw = handle_map.get(m[3])
                    csid = "Me" if m[4] else (raw or "?")
                    cname = my_name if m[4] else name_map.get(csid, csid)
                    ctext = (m[2] or "").strip()
                    if ctext and m[6] not in (HAHA_TYPE, HAHA_REMOVE_TYPE):
                        print(f"      {cname}: {ctext[:100]}")

    print("\n" + "=" * W)
    print("  TOP 10 MOST LAUGHED MESSAGES".center(W))
    print("=" * W)
    top10 = sorted(msg_haha_count.items(), key=lambda x: x[1], reverse=True)[:10]
    for rank, (guid, count) in enumerate(top10, 1):
        sender = guid_to_sender.get(guid, "?")
        name = display.get(sender, sender)
        text = guid_to_text.get(guid, "[no text]")
        print(f"\n  #{rank} ({count} hahas) — {name}")
        print_message_content(guid, text, attachment_map, indent="  ")

    # Awards — all based on hahas per message sent
    print("\n" + "=" * W)
    print("  AWARDS  (based on hahas per message sent)".center(W))
    print("=" * W)

    eligible = [sid for sid in all_senders if messages_sent.get(sid, 0) > 0]

    if eligible:
        jester_id   = max(eligible, key=ratio_received)
        brick_id    = min(eligible, key=ratio_received)
        chuckle_id  = max(eligible, key=ratio_given)
        debbie_id   = min(eligible, key=ratio_given)

        print(f"\n  Jester        — {display[jester_id]} ({ratio_received(jester_id):.3f} hahas received/msg)")
        print(f"  Brick         — {display[brick_id]} ({ratio_received(brick_id):.3f} hahas received/msg)")
        print(f"  Chucklenuts   — {display[chuckle_id]} ({ratio_given(chuckle_id):.3f} hahas given/msg)")
        print(f"  Debbie Downer — {display[debbie_id]} ({ratio_given(debbie_id):.3f} hahas given/msg)")

    print("\n" + "=" * W + "\n")


def main():
    print("Copying iMessage database...")
    tmp_db = copy_db()

    try:
        conn = sqlite3.connect(tmp_db)

        handle_map = get_handle_map(conn)
        name_map = load_names()
        my_name = get_my_name(name_map)  # pops MY_NAME from the dict

        chats = list_group_chats(conn)
        if not chats:
            print("No group chats found.")
            sys.exit(0)

        chat_ids = pick_chat(chats)
        current_members = get_current_members(conn, chat_ids)

        print("\nLoading messages...")
        messages = get_messages(conn, chat_ids)
        print(f"Found {len(messages):,} total messages (including reactions).")

        # Determine start date from earliest message
        real_msgs = [m for m in messages if m[4] or m[3] != 0]
        start_ts = min(m[7] for m in real_msgs) if real_msgs else 0
        start_date = imessage_date(start_ts)

        hahas_given, hahas_received, messages_sent, msg_haha_count, guid_to_text, guid_to_sender = analyze(
            messages, handle_map, current_members, name_map, my_name
        )

        attachment_map = get_attachment_map(conn)

        print_report(
            hahas_given, hahas_received, messages_sent, msg_haha_count,
            guid_to_text, guid_to_sender, messages, handle_map, name_map, my_name, start_date,
            attachment_map
        )

    finally:
        conn.close()
        os.unlink(tmp_db)


if __name__ == "__main__":
    main()
    