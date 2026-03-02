import os

import subprocess
import pylspclient
from pylspclient.lsp_pydantic_strcuts import Position
from loguru import logger


class LspClient:
    def __init__(self, cmd):
        self.p = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.json_rpc_endpoint = pylspclient.JsonRpcEndpoint(
            self.p.stdin, self.p.stdout
        )
        self.lsp_endpoint = pylspclient.LspEndpoint(self.json_rpc_endpoint)
        self.lsp_client = pylspclient.LspClient(self.lsp_endpoint)

        capabilities = {
            "textDocument": {
                "references": {"dynamicRegistration": True},
            }
        }
        root_uri = f"file://{os.getcwd()}"
        self.lsp_client.initialize(
            os.getpid(), None, root_uri, None, capabilities, "off", None
        )
        self.lsp_client.initialized()
        logger.info("LSP Server initialized")

    def get_references(self, file_path, line, character):
        uri = f"file://{os.path.abspath(file_path)}"
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        }
        references = self.lsp_endpoint.call_method("textDocument/references", **params)
        return references

    def shutdown(self):
        self.lsp_client.shutdown()
        self.lsp_client.exit()
        self.p.terminate()
        logger.info("LSP Server shut down")
