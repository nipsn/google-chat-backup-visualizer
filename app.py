from flask import Flask, render_template, send_from_directory, g, redirect, url_for
from markupsafe import Markup
import json
import argparse
import os
import re

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


# Route to serve media files

@app.template_filter('replace_emoji')
def replace_emoji(text, annotations):
    for annotation in annotations:
        if 'custom_emoji_metadata' in annotation:
            shortcode = annotation['custom_emoji_metadata']['custom_emoji']['shortcode']
            content_type = annotation['custom_emoji_metadata']['custom_emoji']['content_type']
            emoji_url = url_for(
                'media', filename=f"CustomEmoji-{shortcode[1:-1]}.{content_type.split('/')[-1]}")
            text = text.replace(
                '�', f'<img src="{emoji_url}" alt="{shortcode}" style="width: 30px; height: 30px;">', 1)

    if not isinstance(text, str):
        text = str(text)

    # Replace URLs with anchor tags
    url_pattern = re.compile(r'(https?://\S+)')
    text = url_pattern.sub(r'<a href="\1">\1</a>', text)

    code_pattern = re.compile(r'```([^`]+)```', re.DOTALL)
    text = code_pattern.sub(r'<pre><code>\1</code></pre>', text)

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


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(g.group_path, filename)

# Route to display group info and messages

@app.route('/<page_name>')
def index(page_name):
    return render_template('index.html',
                           group_info=g.group_info,
                           messages=g.messages,
                           member_colors=g.member_colors)


@app.route('/')
def root():
    return redirect(url_for('index', page_name=app.config['PAGE_NAME']))


@app.before_request
def before_request():
    g.group_path = app.config['GROUP_PATH']
    g.group_info = app.config['GROUP_INFO']
    g.messages = app.config['MESSAGES']
    g.member_colors = app.config['MEMBER_COLORS']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run Flask app with JSON file paths.')
    parser.add_argument('--group_path', required=True,
                        help='Path to the group directory')
    args = parser.parse_args()

    group_info, messages, member_colors = load_json_data(
        args.group_path + "/group_info.json", args.group_path + "/messages.json")

    # Extract the last part of the group_path
    page_name = os.path.basename(os.path.normpath(args.group_path))

    # Store the data in the Flask application config
    app.config['GROUP_PATH'] = "resources"
    app.config['GROUP_INFO'] = group_info
    app.config['MESSAGES'] = messages
    app.config['MEMBER_COLORS'] = member_colors
    app.config['PAGE_NAME'] = page_name

    app.run()
