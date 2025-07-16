from fastmcp import FastMCP
from tools.dice import roll_dice

mcp = FastMCP(name="Dice Roller")

mcp.tool(roll_dice)  # Register the tool function

if __name__ == "__main__":
        mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8081,
        path="/",
        log_level="debug",
    )