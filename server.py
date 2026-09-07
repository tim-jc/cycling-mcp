from mcp.server import MCPServer

from tools.activities import register_activity_tools

mcp = MCPServer("cycling-mcp")

register_activity_tools(mcp)

if __name__ == "__main__":
    mcp.run()
