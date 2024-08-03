# Google Chat Backup Visualizer

This project aims to provide a way to easily visualize a Google Chat backup.

To get started:

 - Get your backup
 - Unzip all content in the `resources` directory
 - Run the following lines in a REPL to generate the initial index.html

```python
>>> import convert_utils.convert_tools as ct
>>> ct.json_messages_to_html("resources/messages.json")
```

You should find the `index.html` file inside the `static` directory.

Now you can launch the app with:

```sh
pip install -r requirements.txt
python3 app.py
```