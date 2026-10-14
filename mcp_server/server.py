"""Servidor MCP de las fuentes ficticias de Pasarela Austral."""

from mcp.server.mcpserver import MCPServer

from mcp_server.tools import informes, listas, noticias, registro, riesgo

server = MCPServer("pasarela-fuentes")

server.tool(name="consultar_registro_mercantil", description=registro.DESCRIPTION)(
    registro.consultar_registro_mercantil
)
server.tool(name="consultar_listas_restrictivas", description=listas.DESCRIPTION)(
    listas.consultar_listas_restrictivas
)
server.tool(name="buscar_noticias", description=noticias.DESCRIPTION)(noticias.buscar_noticias)
server.tool(name="consultar_riesgo_categoria", description=riesgo.DESCRIPTION)(
    riesgo.consultar_riesgo_categoria
)
server.tool(name="registrar_informe", description=informes.DESCRIPTION_INFORME)(
    informes.registrar_informe
)
server.tool(name="escalar_a_cumplimiento", description=informes.DESCRIPTION_ESCALAR)(
    informes.escalar_a_cumplimiento
)


def main() -> None:
    server.run(transport="stdio")
