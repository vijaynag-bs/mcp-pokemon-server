import logging
import os
import contextlib
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any, Optional
from starlette.routing import Mount
from starlette.applications import Starlette
from starlette.routing import Route
from pydantic.types import Json
import uvicorn
import typer
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from poke_client import PokeClient, PokeClientSettings


class _MCPTransport(Enum):
    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"


class PokemonMCPServer:
    def __init__(self, name: str, poke_client: Optional[PokeClient] = None):
        self.server = FastMCP(name=name)
        self.poke_client = poke_client or PokeClient(PokeClientSettings())
        self.register_tools()


    def register_tools(self):
        @self.server.tool()
        def greet_pokemon_user(name: str) -> str:
            try:
                return f"Hello {name}, Welcome to Pokemon MCP Server"
            except Exception as e:
                logging.error(f"Failed to get pokemon data: {e}")
                return {"error": str(e)}

        @self.server.tool()
        def get_pokemon(name: str) -> Json:
            try:
                return self.poke_client.get_pokemon_data(name)
            except Exception as e:
                logging.error(f"Failed to get pokemon data: {e}")
                return {"error": str(e)}


class ASGIAppFactory:
    def __init__(self, server):
        self.server = server

    def bootstrap_asgi(self, server: Server, debug: bool = False):
        session_manager = StreamableHTTPSessionManager(
            app=self.server, event_store=None, json_response=True, stateless=True
        )

        async def streamable_http(scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            async with session_manager.run():
                logging.info("Application started with StreamableHTTP session manager!")
                try:
                    yield
                finally:
                    logging.info("Application shutting down...")

        return Starlette(
            debug=debug,
            routes=[Mount("/mcp", app=streamable_http)],
            lifespan=lifespan,
        )


def main(
    host: str = os.getenv("MCP_HOST", "0.0.0.0"),
    port: str = os.getenv("MCP_PORT", "8080"),
    transport: str = _MCPTransport.STREAMABLE_HTTP.value,
):
    poke_server = PokemonMCPServer("Pokemon MCP Server")
    mcp_server = poke_server.server._mcp_server
    asgi = ASGIAppFactory(mcp_server)
    if transport == "streamable-http":
        asgi_app = asgi.bootstrap_asgi(True)
        uvicorn.run(app=asgi_app, host=host, port=int(port))
    elif transport == "stdio":
        mcp_server.server.run()
    else:
        typer.echo(
            f"Unsupported: {transport}! Choose from {[t.value for t in _MCPTransport]}",
            err=True,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    typer.run(main)
