from flask import Flask, render_template, send_from_directory, g, redirect, url_for, request, jsonify
from markupsafe import Markup
import argparse
import json
import os
import re
import sqlite3

app = Flask(__name__)

DELETED_USER_NAME = "Deleted User"
ANONYMOUS_USER_NAME = "Anonymous User"


def assign_colors(members):
    colors = ['#33FF57', '#FF5733', '#3357FF', '#FF33A1', '#A133FF', '#33FFF5']
    member_colors = {}
    color_index = 0
    for member in members:
        member_colors[member['name']] = colors[color_index % len(colors)]
        color_index += 1
    return member_colors


def replace_image_references(msg_list, search_term):
    count = 0
    for msg in msg_list:
        try:
            has_attached_files = msg["attached_files"]
        except KeyError:
            has_attached_files = False
        if has_attached_files:
            # not common to have more than 1 attachment
            try:
                export_file_name = msg["attached_files"][0]["export_name"]
            except KeyError:
                export_file_name = ""
            if export_file_name == search_term:
                if count > 0:
                    (file_name, extension) = search_term.split(".")
                    msg["attached_files"][0]["export_name"] = f"{file_name}({count}).{extension}"
                count += 1
    return msg_list

def replace_html_special_chars(text):
    text = text.replace("<", "&lt;")
    text = text.replace("\u003c", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\u003e", "&gt;")
    text = text.replace("&", "&amp;")
    return text.replace("\u0026", "&amp;")


def load_json_data(group_info_path, messages_path):
    with open(group_info_path, 'r', encoding='utf-8') as f:
        group_info = json.load(f)
        member_colors = assign_colors(group_info['members'])

    with open(messages_path, 'r', encoding='utf-8') as f:
        msg_list = json.load(f)["messages"]

        msg_list = replace_image_references(msg_list, "File-image.png")
        msg_list = replace_image_references(msg_list, "File-imagen.png")
        msg_list = replace_image_references(msg_list, "File-unnamed.png")
        messages = {"messages": msg_list}

    return group_info, messages, member_colors


def ensure_pins_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS pinned_messages (
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            message_id TEXT NOT NULL,
            pinned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(conversation_id, message_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_pinned_messages_conversation
            ON pinned_messages(conversation_id);
        """
    )


def load_sqlite_data(db_path, root_path, conversation):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_pins_schema(conn)

    conv_row = None
    if conversation:
        if conversation.isdigit():
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (int(conversation),),
            ).fetchone()
        if not conv_row:
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE dir_name = ?",
                (conversation,),
            ).fetchone()
        if not conv_row:
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE conv_key = ?",
                (conversation,),
            ).fetchone()
    else:
        conv_row = conn.execute(
            "SELECT * FROM conversations ORDER BY dir_name LIMIT 1"
        ).fetchone()

    if not conv_row:
        conn.close()
        raise FileNotFoundError("No conversations found in the SQLite database.")

    members = conn.execute(
        """
        SELECT users.name, users.email, users.user_type
        FROM conversation_members
        JOIN users ON users.id = conversation_members.user_id
        WHERE conversation_members.conversation_id = ?
        ORDER BY users.name
        """,
        (conv_row["id"],),
    ).fetchall()
    group_info = {
        "name": conv_row["name"] or conv_row["dir_name"],
        "emoji_id": conv_row["emoji_id"],
        "members": [dict(row) for row in members],
    }
    member_colors = assign_colors(group_info["members"])

    message_rows = conn.execute(
        """
        SELECT raw_json
        FROM messages
        WHERE conversation_id = ?
        ORDER BY message_index, id
        """,
        (conv_row["id"],),
    ).fetchall()
    msg_list = []
    for row in message_rows:
        raw_json = row["raw_json"]
        if not raw_json:
            continue
        msg_list.append(json.loads(raw_json))

    msg_list = replace_image_references(msg_list, "File-image.png")
    msg_list = replace_image_references(msg_list, "File-imagen.png")
    msg_list = replace_image_references(msg_list, "File-unnamed.png")

    messages = {"messages": msg_list}
    conn.close()

    group_path = os.path.normpath(os.path.join(root_path, conv_row["path"] or ""))
    page_name = conv_row["dir_name"]
    return group_info, messages, member_colors, group_path, page_name, conv_row["id"]


def fetch_pinned_messages(db_path: str, conversation_id: int) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_pins_schema(conn)
    rows = conn.execute(
        """
        SELECT pinned_messages.message_id AS message_id,
               messages.text AS text,
               messages.created_date AS created_date,
               users.name AS creator_name
        FROM pinned_messages
        JOIN messages
          ON messages.conversation_id = pinned_messages.conversation_id
         AND messages.message_id = pinned_messages.message_id
        LEFT JOIN users ON users.id = messages.creator_user_id
        WHERE pinned_messages.conversation_id = ?
        ORDER BY pinned_messages.pinned_at DESC, pinned_messages.id DESC
        """,
        (conversation_id,),
    ).fetchall()
    conn.close()
    pinned = []
    for row in rows:
        pinned.append(
            {
                "message_id": row["message_id"],
                "creator": {"name": row["creator_name"] or "Unknown"},
                "text": row["text"] or "",
                "created_date": row["created_date"] or "",
            }
        )
    return pinned


def load_conversation_list(db_path):
    if not db_path or not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    member_rows = conn.execute(
        """
        SELECT conversation_members.conversation_id, users.name
        FROM conversation_members
        JOIN users ON users.id = conversation_members.user_id
        ORDER BY users.name
        """
    ).fetchall()
    members_by_conv = {}
    for row in member_rows:
        name = row["name"]
        if name:
            members_by_conv.setdefault(row["conversation_id"], []).append(name)

    conv_rows = conn.execute(
        """
        SELECT id, conv_type, conv_key, dir_name, name, emoji_id
        FROM conversations
        ORDER BY conv_type, name, dir_name
        """
    ).fetchall()
    conversations = []
    for row in conv_rows:
        conv_type = row["conv_type"] or "unknown"
        raw_name = (row["name"] or "").strip()
        display_name = raw_name
        if conv_type == "dm":
            if not raw_name or raw_name.startswith("DM "):
                members = members_by_conv.get(row["id"], [])
                display_name = ", ".join(members) if members else row["conv_key"]
        else:
            if not display_name:
                display_name = row["dir_name"] or row["conv_key"]
            if display_name.startswith("Space "):
                display_name = display_name.replace("Space ", "", 1).strip()

        display_name = display_name or row["dir_name"] or row["conv_key"]
        emoji_id = (row["emoji_id"] or "").strip()
        icon_text = emoji_id
        if not icon_text:
            if conv_type == "dm":
                parts = [part for part in re.split(r"\s+", display_name) if part]
                initials = "".join([part[0] for part in parts[:2]]).upper()
                icon_text = initials or "DM"
            else:
                icon_text = "💬"

        conversations.append(
            {
                "id": row["id"],
                "conv_type": conv_type,
                "conv_key": row["conv_key"],
                "dir_name": row["dir_name"],
                "display_name": display_name,
                "emoji_id": emoji_id,
                "icon_text": icon_text,
                "members": members_by_conv.get(row["id"], []),
            }
        )

    conn.close()
    return conversations


def fetch_assignable_users(db_path: str) -> list[dict]:
    if not db_path or not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, name, email, user_type
        FROM users
        WHERE name IS NOT NULL
          AND TRIM(name) != ''
          AND TRIM(name) != ?
          AND TRIM(name) != ?
          AND user_type = 'Human'
        ORDER BY name
        """,
        (DELETED_USER_NAME, ANONYMOUS_USER_NAME),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def load_conversation_path(db_path, root_path, conversation):
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError("SQLite database not found.")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = None
    if conversation:
        if conversation.isdigit():
            row = conn.execute(
                "SELECT path FROM conversations WHERE id = ?",
                (int(conversation),),
            ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT path FROM conversations WHERE dir_name = ?",
                (conversation,),
            ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT path FROM conversations WHERE conv_key = ?",
                (conversation,),
            ).fetchone()
    conn.close()
    if not row:
        raise FileNotFoundError("Conversation not found.")
    return os.path.normpath(os.path.join(root_path, row["path"] or ""))


# Route to serve media files

@app.template_filter('replace_emoji')
def replace_emoji(text, annotations):

    if not isinstance(text, str):
        text = str(text)

    text = replace_html_special_chars(text)

    for annotation in annotations:
        if 'custom_emoji_metadata' in annotation:
            shortcode = annotation['custom_emoji_metadata']['custom_emoji']['shortcode']
            content_type = annotation['custom_emoji_metadata']['custom_emoji']['content_type']
            emoji_url = url_for(
                'media',
                page_name=getattr(g, "page_name", app.config.get("PAGE_NAME", "")),
                filename=f"CustomEmoji-{shortcode[1:-1]}.{content_type.split('/')[-1]}",
            )
            text = text.replace(
                '�', f'<img src="{emoji_url}" alt="{shortcode}" style="width: 30px; height: 30px;">', 1)
    # Replace URLs with anchor tags
    url_pattern = re.compile(r'(https?://\S+)')
    text = url_pattern.sub(r'<a href="\1">\1</a>', text)

    code_block_pattern = re.compile(r'```(.*?)```', re.DOTALL)
    text = code_block_pattern.sub(r'<pre><code>\1</code></pre>', text)

    tilde_block_pattern = re.compile(r'~~~(.*?)~~~', re.DOTALL)
    text = tilde_block_pattern.sub(r'<pre><code>\1</code></pre>', text)

    inline_backtick_pattern = re.compile(r'\\?`([^`\n]+?)`')
    text = inline_backtick_pattern.sub(r'<code>\1</code>', text)

    inline_code_pattern = re.compile(r'(?<!~)~(?!~)([^~\n]+?)~(?!~)')
    text = inline_code_pattern.sub(r'<code>\1</code>', text)

    # Replace user mentions with colored text
    mention_pattern = re.compile(
        r'@((?:[\wáéíóúÁÉÍÓÚñÑ]+\s+){0,2}[\wáéíóúÁÉÍÓÚñÑ]+)')

    def replace_match(match):
        full_mention = match.group(1)
        color = g.member_colors.get(full_mention, "#000")

        if full_mention in g.member_colors:
            return f'<span style="color: {color}">@{full_mention}</span>'
        else:
            return match.group(0)

    text = mention_pattern.sub(replace_match, text)
    return Markup(text)


@app.route('/media/<page_name>/<path:filename>')
def media(page_name, filename):
    group_path = load_conversation_path(
        app.config['DB_PATH'], app.config['ROOT_PATH'], page_name
    )
    return send_from_directory(group_path, filename)

# Route to display group info and messages

@app.route('/chat/<page_name>')
def chat(page_name):
    spaces = sorted(
        [conv for conv in g.conversations if conv["conv_type"] != "dm"],
        key=lambda conv: conv["display_name"].lower(),
    )
    dms = sorted(
        [conv for conv in g.conversations if conv["conv_type"] == "dm"],
        key=lambda conv: conv["display_name"].lower(),
    )
    return render_template(
        'chat.html',
        group_info=g.group_info,
        messages=g.messages,
        member_colors=g.member_colors,
        pinned_messages=fetch_pinned_messages(
            app.config['DB_PATH'], g.conversation_id
        ),
        conversations=g.conversations,
        active_conversation=g.page_name,
        spaces=spaces,
        dms=dms,
        conversation_id=g.conversation_id,
        assignable_users=fetch_assignable_users(app.config['DB_PATH']),
        deleted_user_name=DELETED_USER_NAME,
    )


@app.route('/<page_name>')
def legacy_chat(page_name):
    return redirect(url_for('chat', page_name=page_name))


@app.route('/')
def root():
    spaces = sorted(
        [conv for conv in g.conversations if conv["conv_type"] != "dm"],
        key=lambda conv: conv["display_name"].lower(),
    )
    dms = sorted(
        [conv for conv in g.conversations if conv["conv_type"] == "dm"],
        key=lambda conv: conv["display_name"].lower(),
    )
    return render_template(
        'landing.html',
        conversations=g.conversations,
        spaces=spaces,
        dms=dms,
        has_data=bool(g.conversations),
    )


@app.route('/pin', methods=['POST'])
def pin_message():
    payload = request.get_json(silent=True) or {}
    message_id = payload.get("message_id")
    conversation_id = payload.get("conversation_id")
    if not message_id:
        return jsonify({"error": "message_id is required"}), 400
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    ensure_pins_schema(conn)

    existing = conn.execute(
        """
        SELECT 1 FROM pinned_messages
        WHERE conversation_id = ? AND message_id = ?
        """,
        (conversation_id, message_id),
    ).fetchone()
    status = "exists"
    if not existing:
        conn.execute(
            """
            INSERT OR IGNORE INTO pinned_messages (conversation_id, message_id)
            VALUES (?, ?)
            """,
            (conversation_id, message_id),
        )
        conn.commit()
        status = "pinned"

    row = conn.execute(
        """
        SELECT pinned_messages.message_id AS message_id,
               messages.text AS text,
               messages.created_date AS created_date,
               users.name AS creator_name
        FROM pinned_messages
        JOIN messages
          ON messages.conversation_id = pinned_messages.conversation_id
         AND messages.message_id = pinned_messages.message_id
        LEFT JOIN users ON users.id = messages.creator_user_id
        WHERE pinned_messages.conversation_id = ?
          AND pinned_messages.message_id = ?
        """,
        (conversation_id, message_id),
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "message not found"}), 404

    pinned = {
        "message_id": row["message_id"],
        "creator": {"name": row["creator_name"] or "Unknown"},
        "text": row["text"] or "",
        "created_date": row["created_date"] or "",
    }
    return jsonify({"status": status, "pinned": pinned})


@app.route('/unpin', methods=['POST'])
def unpin_message():
    payload = request.get_json(silent=True) or {}
    message_id = payload.get("message_id")
    conversation_id = payload.get("conversation_id")
    if not message_id:
        return jsonify({"error": "message_id is required"}), 400
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    ensure_pins_schema(conn)

    conn.execute(
        """
        DELETE FROM pinned_messages
        WHERE conversation_id = ? AND message_id = ?
        """,
        (conversation_id, message_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "unpinned", "message_id": message_id})


@app.route('/users', methods=['POST'])
def create_user():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    email = (payload.get("email") or "").strip() or None
    user_type = (payload.get("user_type") or "Human").strip() or "Human"

    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT OR IGNORE INTO users (name, email, user_type) VALUES (?, ?, ?)",
        (name, email, user_type),
    )
    row = conn.execute(
        "SELECT id, name, email, user_type FROM users WHERE name IS ? AND email IS ? AND user_type IS ?",
        (name, email, user_type),
    ).fetchone()
    conn.commit()
    conn.close()
    if not row:
        return jsonify({"error": "failed to create user"}), 500
    return jsonify({"user": dict(row)})


@app.route('/assign-message', methods=['POST'])
def assign_message():
    payload = request.get_json(silent=True) or {}
    message_id = payload.get("message_id")
    conversation_id = payload.get("conversation_id")
    user_id = payload.get("user_id")
    if not message_id:
        return jsonify({"error": "message_id is required"}), 400
    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        conversation_id = int(conversation_id)
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "conversation_id and user_id must be integers"}), 400

    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    message_row = conn.execute(
        """
        SELECT id, raw_json
        FROM messages
        WHERE conversation_id = ? AND message_id = ?
        """,
        (conversation_id, message_id),
    ).fetchone()
    if not message_row:
        conn.close()
        return jsonify({"error": "message not found"}), 404

    user_row = conn.execute(
        "SELECT id, name, email, user_type FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not user_row:
        conn.close()
        return jsonify({"error": "user not found"}), 404

    existing_member = conn.execute(
        """
        SELECT 1 FROM conversation_members
        WHERE conversation_id = ? AND user_id = ?
        """,
        (conversation_id, user_id),
    ).fetchone()
    member_added = False
    if not existing_member:
        conn.execute(
            """
            INSERT OR IGNORE INTO conversation_members (conversation_id, user_id)
            VALUES (?, ?)
            """,
            (conversation_id, user_id),
        )
        member_added = True

    raw_json = message_row["raw_json"] or "{}"
    try:
        message_payload = json.loads(raw_json)
    except json.JSONDecodeError:
        message_payload = {}

    message_payload["creator"] = {
        "name": user_row["name"],
        "email": user_row["email"],
        "user_type": user_row["user_type"],
    }
    updated_json = json.dumps(message_payload, ensure_ascii=False)

    conn.execute(
        """
        UPDATE messages
        SET creator_user_id = ?, raw_json = ?
        WHERE id = ?
        """,
        (user_id, updated_json, message_row["id"]),
    )
    conn.commit()

    members = conn.execute(
        """
        SELECT users.name, users.email, users.user_type
        FROM conversation_members
        JOIN users ON users.id = conversation_members.user_id
        WHERE conversation_id = ?
        ORDER BY users.name
        """,
        (conversation_id,),
    ).fetchall()
    member_colors = assign_colors([dict(row) for row in members])
    conn.close()

    return jsonify(
        {
            "status": "assigned",
            "user": dict(user_row),
            "member_color": member_colors.get(user_row["name"]),
            "member_added": member_added,
        }
    )


@app.before_request
def before_request():
    g.conversations = app.config.get('CONVERSATIONS', [])
    db_path = app.config.get('DB_PATH')
    if not g.conversations and db_path and os.path.exists(db_path):
        g.conversations = load_conversation_list(db_path)

    if request.endpoint in {'chat'}:
        page_name = request.view_args.get('page_name')
        group_info, messages, member_colors, group_path, resolved_page_name, conversation_id = load_sqlite_data(
            app.config['DB_PATH'], app.config['ROOT_PATH'], page_name
        )
        g.group_path = group_path
        g.group_info = group_info
        g.messages = messages
        g.member_colors = member_colors
        g.page_name = resolved_page_name
        g.conversation_id = conversation_id


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Run the Google Chat backup visualizer."
    )
    parser.add_argument(
        "--db",
        default="resources/chat.db",
        help="SQLite database path to read from.",
    )
    parser.add_argument(
        "--root",
        default="resources/Google Chat",
        help="Path to the Google Chat export root.",
    )
    parser.add_argument(
        "--conversation",
        default="",
        help="Conversation id, dir name, or key to render.",
    )
    args = parser.parse_args()

    app.config['DB_PATH'] = args.db
    app.config['ROOT_PATH'] = args.root
    app.config['CONVERSATIONS'] = load_conversation_list(args.db)
    if args.conversation:
        app.config['PAGE_NAME'] = args.conversation

    app.run()
