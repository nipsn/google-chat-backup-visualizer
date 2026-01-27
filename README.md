# Google Chat Backup Visualizer

This project aims to provide a way to easily visualize a Google Chat backup.

To get started:

 - Get your backup
 - Unzip all content in the `resources` directory

Optional: import the JSON into SQLite for faster querying and indexing of files:

```sh
python3 import_db.py --root "resources/Google Chat" --db resources/chat.db
```

Now you can launch the app with:

```sh
pip install -r requirements.txt
python3 app.py
```

## Docker

The container mounts a host directory at `/app/resources`.

By default it uses `./resources` from the repo:

```sh
docker compose up --build
```

Or point it at any directory containing your Google Chat export:

```sh
GCBV_RESOURCES_DIR=/path/to/resources docker compose up --build
```

Then open `http://localhost:5000`.
