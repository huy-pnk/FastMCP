# FastMCP Dice Roller Server

A simple [FastMCP](https://gofastmcp.com/) server that provides a dice-rolling tool via HTTP. This project demonstrates how to build and run a minimal MCP server using FastMCP.

## Features
- **Dice Roller Tool**: Roll any number of 6-sided dice and get the results via an MCP-compatible API.
- **HTTP Transport**: Exposes the server over HTTP for easy integration and testing.
- **FastMCP 2.x Compatible**: Uses the latest FastMCP features and best practices.

## Requirements
- Python >= 3.10
- [FastMCP](https://gofastmcp.com/) >= 2.10.5
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

## Installation
1. **Clone the repository**
   ```sh
   git clone <your-repo-url>
   cd fastmcp/server
   ```
2. **Set up a virtual environment**
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # or
   source .venv/bin/activate  # On macOS/Linux
   ```
3. **Install dependencies**
   ```sh
   uv pip install -r requirements.txt  # If you have a requirements.txt
   # or, to sync from pyproject.toml
   uv sync
   ```

## Usage
### Run the server (HTTP transport)
```sh
fastmcp run ./src/main.py --transport http --host 127.0.0.1 --port 8081 --log-level debug
```
Or, run directly with Python (uses HTTP transport as set in code):
```sh
python ./src/main.py
```

### Example: Roll Dice Tool
Send a request to the server to roll dice (see FastMCP client documentation for details).

- **Tool name:** `roll_dice`
- **Arguments:** `n_dice` (integer, number of dice to roll)
- **Returns:** List of integers (dice results)

#### Example (Python client):
```python
from fastmcp import Client
import asyncio

client = Client("http://127.0.0.1:8081/")

async def main():
    async with client:
        result = await client.call_tool("roll_dice", {"n_dice": 3})
        print(result.data)  # e.g., [2, 5, 6]

asyncio.run(main())
```

## Configuration
- The server listens on `127.0.0.1:8081` by default (see `src/main.py`).
- You can change the host, port, or log level by editing the `mcp.run(...)` call or passing CLI arguments.

## Development
- Add new tools by decorating functions with `@mcp.tool` in `src/main.py`.
- See [FastMCP documentation](https://gofastmcp.com/) for advanced features.

## License
Specify your license here (e.g., MIT, Apache-2.0).

## Contact / Contributing
- Issues and PRs welcome!
- For questions, see the [FastMCP community](https://gofastmcp.com/community) or open an issue in this repo.