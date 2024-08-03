from flask import Flask, render_template, send_from_directory, g
import json
import argparse

app = Flask(__name__)


def assign_colors(members):
    colors = ['#33FF57', '#FF5733', '#3357FF', '#FF33A1', '#A133FF', '#33FFF5']
    member_colors = {}
    color_index = 0
    for member in members:
        member_colors[member['name']] = colors[color_index % len(colors)]
        color_index += 1
    return member_colors


def replace_image_references_in_string(input_string):
    search_term = "File-image.png"
    count = 0
    start = 0

    while True:
        start = input_string.find(search_term, start)
        if start == -1:
            break
        if count > 0:
            replacement = f"File-image({count}).png"
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
        messages_string = replace_image_references_in_string(messages_string)
        messages = json.loads(messages_string)

    return group_info, messages, member_colors

# Route to serve media files


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(g.group_path, filename)

# Route to display group info and messages


@app.route('/')
def index():
    return render_template('index.html',
                           group_info=g.group_info,
                           messages=g.messages,
                           member_colors=g.member_colors)


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

    # Store the data in the Flask application config
    app.config['GROUP_PATH'] = args.group_path
    app.config['GROUP_INFO'] = group_info
    app.config['MESSAGES'] = messages
    app.config['MEMBER_COLORS'] = member_colors

    app.run()
