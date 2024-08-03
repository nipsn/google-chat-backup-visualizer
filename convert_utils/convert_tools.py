import json
import convert_utils.html_constants as hc


def get_gif_url_if_exists(message) -> (bool, str):
    try:
        return message["annotations"][0]["url_metadata"]["image_url"]
    except KeyError:
        return ""


def get_image_uri_if_exists(message) -> str:
    try:
        return "resources/" + message["attached_files"][0]["export_name"]
    except KeyError:
        return ""


def get_text_if_exists(message) -> str:
    try:
        return message["text"]
    except KeyError:
        return ""


def reduce(message) -> dict:
    return {
        "author": message["creator"]["name"],
        "datetime": message["created_date"],
        "text": get_text_if_exists(message),
        "id": message["message_id"],
        "image": get_image_uri_if_exists(message),
        "gif": get_gif_url_if_exists(message),
    }


def format_into_html(message: dict) -> str:
    return f"""<div class="container">
  <p style="font-height:4px">{message["author"]}:</p>
  <b><p> - {message["text"]}</p></b>
  <img src="{message["image"]}">
  <img src="{message["gif"]}">
  <span class="time-right">{message["datetime"]}</span>
</div>"""


def json_messages_to_html(path: str) -> None:
    with open(path) as f:
        messages = json.load(f)["messages"]

    content = "\n".join([format_into_html(reduce(m)) for m in messages])
    with open("static/index.html", "w") as f:
        f.write(hc.header + content + hc.footer)
