import os

from app import app, load_conversation_list


def _configure_app() -> None:
    db_path = os.environ.get("GCBV_DB_PATH", "resources/chat.db")
    root_path = os.environ.get("GCBV_ROOT_PATH", "resources/Google Chat")
    conversation = os.environ.get("GCBV_CONVERSATION", "")

    app.config["DB_PATH"] = db_path
    app.config["ROOT_PATH"] = root_path
    app.config["CONVERSATIONS"] = load_conversation_list(db_path)

    if conversation:
        app.config["PAGE_NAME"] = conversation


_configure_app()
