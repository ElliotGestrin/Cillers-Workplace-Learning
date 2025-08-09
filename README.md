# My AI

## Installation
This repository uses UV for Python package management. To install UV, run the following command:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Once UV is installed, you can install the dependencies for this project by running:
```bash
uv sync
```

New dependencies are added with:
```bash
uv add <package_name>
```

Where `<package_name>` is the name of the package you want to add, as for pip.

## Running the Application
To run the application, use the following command:
```bash
uv run webapp.py
```

This will start the Flask web server, and you can access the application in your web browser at `http://localhost:7860`.