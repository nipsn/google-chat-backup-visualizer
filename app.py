from flask import Flask, render_template, send_from_directory, g, url_for
from markupsafe import Markup
import json
import os
import re
import datetime
import locale

app = Flask(__name__)


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


def load_json_data(group_path):
    group_info_path = os.path.join(group_path, 'group_info.json')
    messages_path = os.path.join(group_path, 'messages.json')

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


@app.template_filter('replace_emoji')
def replace_emoji(text, annotations):

    if not isinstance(text, str):
        text = str(text)

    text = replace_html_special_chars(text)

    for annotation in annotations:
        if 'custom_emoji_metadata' in annotation:
            shortcode = annotation['custom_emoji_metadata']['custom_emoji']['shortcode']
            content_type = annotation['custom_emoji_metadata']['custom_emoji']['content_type']
            emoji_url = url_for('media',
                                group_name=g.group_name,
                                filename=f"CustomEmoji-{shortcode[1:-1]}.{content_type.split('/')[-1]}")
            text = text.replace(
                '�', f'<img src="{emoji_url}" alt="{shortcode}" style="width: 30px; height: 30px;">', 1)

    url_pattern = re.compile(r'(https?://\S+)')
    text = url_pattern.sub(r'<a href="\1">\1</a>', text)

    code_pattern = re.compile(r'```([^`]+)```', re.DOTALL)
    text = code_pattern.sub(r'<pre><code>\1</code></pre>', text)

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


@app.route('/media/<group_name>/<path:filename>')
def media(group_name, filename):
    return send_from_directory(os.path.join('resources', group_name), filename)


@app.route('/group/<group_name>')
def index(group_name):
    group_path = os.path.join('resources', group_name)
    if not os.path.exists(group_path):
        return "Group not found", 404

    group_info, messages, member_colors = load_json_data(group_path)

    # Store the data in Flask's g context for this request
    g.member_colors = member_colors
    g.group_path = group_path
    g.group_info = group_info
    g.messages = messages
    g.member_colors = member_colors
    g.group_name = group_name

    return render_template('index.html',
                           group_info=group_info,
                           messages=messages,
                           member_colors=member_colors,
                           group_name=group_name)


@app.route('/')
def home():
    groups = []
    base_path = 'resources'
    for group_name in os.listdir(base_path):
        group_path = os.path.join(base_path, group_name)
        if os.path.isdir(group_path):
            group_info_path = os.path.join(group_path, 'group_info.json')
            group_msg_path = os.path.join(group_path, 'messages.json')
            if os.path.exists(group_msg_path):
                with open(group_msg_path, 'r', encoding='utf-8') as f:
                    last_msg_date_str = json.load(f)['messages'][-1]['created_date']
                    # TODO: support multiple locales
                    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
                    last_msg_datetime = datetime.datetime.strptime(last_msg_date_str, "%A, %d de %B de %Y, %H:%M:%S %Z")
            if os.path.exists(group_info_path):
                with open(group_info_path, 'r', encoding='utf-8') as f:
                    group_info = json.load(f)
                    groups.append({
                        'name': group_info['name'],
                        'emoji_id': group_info.get('emoji_id', '📁'),
                        'group_name': group_name,
                        'last_msg_datetime': last_msg_datetime,
                        'last_msg_date_str': last_msg_date_str,
                    })
    groups.sort(key=lambda x: x['last_msg_datetime'], reverse=True)
    return render_template('home.html', groups=groups)


if __name__ == '__main__':
    app.run()
