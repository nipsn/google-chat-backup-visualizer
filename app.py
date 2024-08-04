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
    print(member_colors)
    return member_colors


def replace_image_references_in_string(search_term, input_string):
    count = 0
    start = 0

    replace = search_term.split(".")[0]
    type = search_term.split(".")[1]

    while True:
        start = input_string.find(search_term, start)
        if start == -1:
            break
        if count > 0:
            replacement = f"{replace}({count}).{type}"
            input_string = input_string[:start] + replacement + \
                input_string[start + len(search_term):]
            start += len(replacement)  # Move past the replacement
        else:
            start += len(search_term)  # Move past the search term
        count += 1

    return input_string


def load_json_data(group_info_path, messages_path):
    with open(group_info_path, 'r', encoding='utf-8') as f:
        group_info = json.load(f)
        member_colors = assign_colors(group_info['members'])

    with open(messages_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)
        messages_string = json.dumps(messages)
        messages_string = replace_image_references_in_string(
            "File-image.png", messages_string)
        messages_string = replace_image_references_in_string(
            "File-imagen.png", messages_string)
        messages = json.loads(messages_string)

    return group_info, messages, member_colors


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

    # Replace inline code blocks
    code_pattern = re.compile(r'```(\w+)?\s*([^`]+)```', re.DOTALL)
    text = code_pattern.sub(r'<pre><code class="\1">\2</code></pre>', text)

    # Replace user mentions with colored text
    mention_pattern = re.compile(
        r'@((?:[\w\áéíóúÁÉÍÓÚñÑ]+\s+){0,2}[\w\áéíóúÁÉÍÓÚñÑ]+)')

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
    app.config['GROUP_PATH'] = args.group_path
    app.config['GROUP_INFO'] = group_info
    app.config['MESSAGES'] = messages
    app.config['MEMBER_COLORS'] = member_colors
    app.config['PAGE_NAME'] = page_name

    app.run()
