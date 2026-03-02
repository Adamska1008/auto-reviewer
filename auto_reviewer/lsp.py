# import subprocess
# import pylspclient

# # ===================
# # 启动Lsp Server （安装好pyright）
# # ===================
# p = subprocess.Popen(
#     ["pyright-langserver", "--stdio"],
#     stdin=subprocess.PIPE,
#     stdout=subprocess.PIPE,
#     stderr=subprocess.PIPE,
#     text=True
# )

# json_rpc_endpoint = pylspclient.JsonRpcEndpoint(p.stdin, p.stdout)
# lsp_client = pylspclient.LspClient(json_rpc_endpoint)
