# Sefaria Jewish Library MCP Server

[![smithery badge](https://smithery.ai/badge/mcp-sefaria-server)](https://smithery.ai/server/mcp-sefaria-server)



An MCP ([Model Context Protocol](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)) server that provides access to Jewish texts from the [Sefaria](https://www.sefaria.org/) library. This server enables Large Language Models to retrieve and reference Jewish texts through a standardized interface.

<a href="https://glama.ai/mcp/servers/j3v6vnp4xk"><img width="380" height="200" src="https://glama.ai/mcp/servers/j3v6vnp4xk/badge" alt="Sefaria Jewish Library Server MCP server" /></a>

## Features

- Retrieve Jewish texts by reference
- Retrieve commentaries and connections to a given text
- Search the Jewish library for a query
- Get bibliographic information about texts
- Access Jewish calendar information
- Validate and autocomplete text names and references
- View the structure of texts and contents of categories

## Installation

Requires Python 3.10 or higher.

### Clone the repository
```bash
git clone https://github.com/sivan22/mcp-sefaria-server.git
cd mcp-sefaria-server
```


### Running the Server

The server can be run directly:

```bash
uv --directory path/to/directory run sefaria_jewish_library
```

Or through an MCP client that supports the Model Context Protocol.
for claude desktop app and cline you should use the following config:
```
{
  "mcpServers": {        
      "sefaria_jewish_library": {
          "command": "uv",
          "args": [
              "--directory",
              "absolute/path/to/mcp-sefaria-server",
              "run",
              "sefaria_jewish_library"
          ],
          "env": {
            "PYTHONIOENCODING": "utf-8" 
          }
      }
  }
}
```

### Installing via Smithery

To install Sefaria Jewish Library for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-sefaria-server):

```bash
npx -y @smithery/cli install mcp-sefaria-server --client claude
```

## Available tools

The server provides the following tools through the MCP interface:

### get_text

Retrieves a specific Jewish text by its reference.

Example:
```
reference: "Genesis 1:1"
reference: "שמות פרק ב פסוק ג"
reference: "משנה ברכות פרק א משנה א"
version_language: "en" (optional, can be "en", "he", or "all")
```

### get_english_translations

Retrieves all available English translations for a specific reference.

Example:
```
reference: "Genesis 1:1"
```

### get_links

Retrieves a list of commentaries and connections for a given text.

Example:
```
reference: "Genesis 1:1"
with_text: 0 (optional, set to 1 to include text content)
```

### search_texts

Searches for Jewish texts in the Sefaria library based on a query.

Example:
```
query: "moshiach"
slop: 1 (optional)
filters: ["Talmud", "Bavli"] (optional)
size: 5 (optional)
```

### search_dictionaries

Searches specifically in Jewish dictionaries (Jastrow, BDB, Klein).

Example:
```
query: "shalom"
```

### get_index

Retrieves bibliographic records for Jewish texts.

Example:
```
title: "Genesis"
```

### get_situational_info

Provides current Jewish calendar information (Hebrew date, Parshat Hashavua, Daf Yomi).

No parameters required.

### get_name

Validates and autocompletes text names, references, topics.

Example:
```
name: "Gen"
limit: 10 (optional)
type_filter: "ref" (optional)
```

### get_shape

Retrieves structure of texts or lists contents of categories.

Example:
```
name: "Genesis" (for text structure)
name: "Tanakh" (for category contents)
```

## Development

This project uses:
- [MCP SDK](https://github.com/modelcontextprotocol/sdk) for server implementation
- [Sefaria API](https://github.com/Sefaria/Sefaria-API) for accessing Jewish texts

  
![image](https://github.com/user-attachments/assets/14ee8826-a76e-4c57-801d-473b177416d3)

## Requirements

- Python >= 3.10
- MCP SDK >= 1.1.1
- Sefaria API

## License

MIT License