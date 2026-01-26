import argparse
import json
import os
import sqlite3
from pathlib import Path


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            user_type TEXT,
            UNIQUE(name, email, user_type)
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            conv_type TEXT NOT NULL,
            conv_key TEXT NOT NULL,
            dir_name TEXT NOT NULL,
            name TEXT,
            emoji_id TEXT,
            path TEXT,
            UNIQUE(conv_type, conv_key)
        );

        CREATE TABLE IF NOT EXISTS conversation_members (
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (conversation_id, user_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            message_id TEXT NOT NULL,
            topic_id TEXT,
            created_date TEXT,
            text TEXT,
            creator_user_id INTEGER,
            raw_json TEXT,
            UNIQUE(conversation_id, message_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS message_attachments (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            original_name TEXT,
            export_name TEXT,
            file_path TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS message_annotations (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            start_index INTEGER,
            length INTEGER,
            annotation_type TEXT,
            raw_json TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS message_reactions (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            emoji_unicode TEXT,
            emoji_shortcode TEXT,
            emoji_state TEXT,
            emoji_creator_user_id INTEGER,
            emoji_owner_customer_id TEXT,
            emoji_create_time TEXT,
            emoji_content_type TEXT,
            reactor_emails_json TEXT,
            raw_json TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (emoji_creator_user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS quoted_messages (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL UNIQUE,
            creator_user_id INTEGER,
            text TEXT,
            raw_json TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS quoted_attachments (
            id INTEGER PRIMARY KEY,
            quoted_message_id INTEGER NOT NULL,
            original_name TEXT,
            export_name TEXT,
            file_path TEXT,
            FOREIGN KEY (quoted_message_id) REFERENCES quoted_messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quoted_annotations (
            id INTEGER PRIMARY KEY,
            quoted_message_id INTEGER NOT NULL,
            start_index INTEGER,
            length INTEGER,
            annotation_type TEXT,
            raw_json TEXT,
            FOREIGN KEY (quoted_message_id) REFERENCES quoted_messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS message_add_ons (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            raw_json TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created_date ON messages(created_date);
        """
    )


def normalize_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def get_or_create_user(conn: sqlite3.Connection, user: dict | None) -> int | None:
    if not user:
        return None

    name = user.get("name")
    email = user.get("email")
    user_type = user.get("user_type")

    conn.execute(
        "INSERT OR IGNORE INTO users (name, email, user_type) VALUES (?, ?, ?)",
        (name, email, user_type),
    )
    row = conn.execute(
        "SELECT id FROM users WHERE name IS ? AND email IS ? AND user_type IS ?",
        (name, email, user_type),
    ).fetchone()
    return row[0] if row else None


def upsert_conversation(
    conn: sqlite3.Connection,
    conv_type: str,
    conv_key: str,
    dir_name: str,
    name: str | None,
    emoji_id: str | None,
    path: str,
) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO conversations
        (conv_type, conv_key, dir_name, name, emoji_id, path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (conv_type, conv_key, dir_name, name, emoji_id, path),
    )
    row = conn.execute(
        "SELECT id FROM conversations WHERE conv_type = ? AND conv_key = ?",
        (conv_type, conv_key),
    ).fetchone()
    return row[0]


def replace_export_name_duplicates(messages: list[dict], filenames: list[str]) -> None:
    for filename in filenames:
        count = 0
        for msg in messages:
            attached = msg.get("attached_files") or []
            if not attached:
                continue
            export_name = attached[0].get("export_name")
            if export_name == filename:
                if count > 0:
                    stem, ext = os.path.splitext(export_name)
                    attached[0]["export_name"] = f"{stem}({count}){ext}"
                count += 1


def import_messages(
    conn: sqlite3.Connection,
    messages: list[dict],
    conversation_id: int,
    conversation_dir: Path,
    root_dir: Path,
) -> None:
    replace_export_name_duplicates(
        messages,
        ["File-image.png", "File-imagen.png", "File-unnamed.png"],
    )

    for msg in messages:
        creator_id = get_or_create_user(conn, msg.get("creator"))
        conn.execute(
            """
            INSERT OR IGNORE INTO messages
            (conversation_id, message_id, topic_id, created_date, text, creator_user_id, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                msg.get("message_id"),
                msg.get("topic_id"),
                msg.get("created_date"),
                msg.get("text"),
                creator_id,
                json.dumps(msg, ensure_ascii=False),
            ),
        )
        row = conn.execute(
            "SELECT id FROM messages WHERE conversation_id = ? AND message_id = ?",
            (conversation_id, msg.get("message_id")),
        ).fetchone()
        if not row:
            continue
        message_row_id = row[0]

        for attachment in msg.get("attached_files") or []:
            export_name = attachment.get("export_name")
            file_path = None
            if export_name:
                file_path = normalize_path(conversation_dir / export_name, root_dir)
            conn.execute(
                """
                INSERT INTO message_attachments
                (message_id, original_name, export_name, file_path)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message_row_id,
                    attachment.get("original_name"),
                    export_name,
                    file_path,
                ),
            )

        for annotation in msg.get("annotations") or []:
            conn.execute(
                """
                INSERT INTO message_annotations
                (message_id, start_index, length, annotation_type, raw_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message_row_id,
                    annotation.get("start_index"),
                    annotation.get("length"),
                    annotation.get("type"),
                    json.dumps(annotation, ensure_ascii=False),
                ),
            )

        for reaction in msg.get("reactions") or []:
            emoji = reaction.get("emoji") or {}
            custom = emoji.get("custom_emoji") or {}
            emoji_creator = None
            if isinstance(custom.get("creator_user_id"), dict):
                emoji_creator = get_or_create_user(conn, custom.get("creator_user_id"))
            conn.execute(
                """
                INSERT INTO message_reactions
                (message_id, emoji_unicode, emoji_shortcode, emoji_state,
                 emoji_creator_user_id, emoji_owner_customer_id, emoji_create_time,
                 emoji_content_type, reactor_emails_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_row_id,
                    emoji.get("unicode"),
                    custom.get("shortcode"),
                    custom.get("state"),
                    emoji_creator,
                    custom.get("owner_customer_id"),
                    custom.get("create_time"),
                    custom.get("content_type"),
                    json.dumps(reaction.get("reactor_emails") or [], ensure_ascii=False),
                    json.dumps(reaction, ensure_ascii=False),
                ),
            )

        for add_on in msg.get("add_on_data") or []:
            conn.execute(
                "INSERT INTO message_add_ons (message_id, raw_json) VALUES (?, ?)",
                (message_row_id, json.dumps(add_on, ensure_ascii=False)),
            )

        quoted = msg.get("quoted_message_metadata")
        if quoted:
            quoted_creator = get_or_create_user(conn, quoted.get("creator"))
            conn.execute(
                """
                INSERT OR IGNORE INTO quoted_messages
                (message_id, creator_user_id, text, raw_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message_row_id,
                    quoted_creator,
                    quoted.get("text"),
                    json.dumps(quoted, ensure_ascii=False),
                ),
            )
            quoted_row = conn.execute(
                "SELECT id FROM quoted_messages WHERE message_id = ?",
                (message_row_id,),
            ).fetchone()
            if quoted_row:
                quoted_id = quoted_row[0]
                for attachment in quoted.get("attached_files") or []:
                    export_name = attachment.get("export_name")
                    file_path = None
                    if export_name:
                        file_path = normalize_path(conversation_dir / export_name, root_dir)
                    conn.execute(
                        """
                        INSERT INTO quoted_attachments
                        (quoted_message_id, original_name, export_name, file_path)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            quoted_id,
                            attachment.get("original_name"),
                            export_name,
                            file_path,
                        ),
                    )

                for annotation in quoted.get("annotations") or []:
                    conn.execute(
                        """
                        INSERT INTO quoted_annotations
                        (quoted_message_id, start_index, length, annotation_type, raw_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            quoted_id,
                            annotation.get("start_index"),
                            annotation.get("length"),
                            annotation.get("type"),
                            json.dumps(annotation, ensure_ascii=False),
                        ),
                    )


def import_conversations(root_dir: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)

    groups_root = root_dir / "Groups"
    if not groups_root.exists():
        raise FileNotFoundError(f"Groups directory not found: {groups_root}")

    for conv_dir in sorted(groups_root.iterdir()):
        if not conv_dir.is_dir():
            continue

        group_info_path = conv_dir / "group-info.json"
        if not group_info_path.exists():
            group_info_path = conv_dir / "group_info.json"
        messages_path = conv_dir / "messages.json"
        if not group_info_path.exists() or not messages_path.exists():
            continue

        with group_info_path.open("r", encoding="utf-8") as handle:
            group_info = json.load(handle)

        with messages_path.open("r", encoding="utf-8") as handle:
            messages = json.load(handle).get("messages", [])

        dir_name = conv_dir.name
        if dir_name.startswith("DM "):
            conv_type = "dm"
            conv_key = dir_name.replace("DM ", "", 1).strip()
        elif dir_name.startswith("Space "):
            conv_type = "space"
            conv_key = dir_name.replace("Space ", "", 1).strip()
        else:
            conv_type = "unknown"
            conv_key = dir_name

        conv_id = upsert_conversation(
            conn,
            conv_type=conv_type,
            conv_key=conv_key,
            dir_name=dir_name,
            name=group_info.get("name"),
            emoji_id=group_info.get("emoji_id"),
            path=normalize_path(conv_dir, root_dir),
        )

        for member in group_info.get("members") or []:
            member_id = get_or_create_user(conn, member)
            if member_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO conversation_members
                    (conversation_id, user_id)
                    VALUES (?, ?)
                    """,
                    (conv_id, member_id),
                )

        import_messages(conn, messages, conv_id, conv_dir, root_dir)
        conn.commit()

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Google Chat JSON backups into a SQLite database."
    )
    parser.add_argument(
        "--root",
        default="resources/Google Chat",
        help="Path to the Google Chat export root (contains Groups/ and Users/).",
    )
    parser.add_argument(
        "--db",
        default="resources/chat.db",
        help="SQLite database path to create or update.",
    )
    args = parser.parse_args()

    root_dir = Path(args.root)
    db_path = Path(args.db)

    import_conversations(root_dir, db_path)
    print(f"Imported conversations into {db_path}")


if __name__ == "__main__":
    main()
