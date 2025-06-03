from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
import logging
import sys
import json
from .sefaria_handler import * 

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('sefaria_jewish_library.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('sefaria_jewish_library')

server = Server("sefaria_jewish_library")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.debug("Handling list_tools request")
    return [
        types.Tool(
            name="get_text",
            description="Retrieves the actual text content from a specific reference in the Jewish library. Returns the Hebrew/Aramaic source text and/or English translations as JSON. Use this when you need the actual content of a passage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Required: Specific text reference (e.g. 'Genesis 1:1', 'Berakhot 2a', 'שולחן ערוך אורח חיים סימן א'). Use get_name tool first to validate complex or uncertain references.",
                    },
                    "version_language": {
                        "type": "string",
                        "description": "Optional: Which language version to retrieve - 'source' (Hebrew/Aramaic original), 'english' (English translation only), 'both' (both languages), or omit for all available versions",
                        "enum": ["source", "english", "both"]
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="get_english_translations",
            description="Retrieves all available English translations for a specific text reference. Returns multiple translation versions if available. Use this when you need to compare different English renderings of the same passage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Required: Specific text reference (e.g. 'Genesis 1:1', 'Berakhot 2a'). Use get_name tool first to validate complex references.",
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="get_index",
            description="Retrieves the bibliographic and structural information (index) for a text or work. Shows the organization, authorship, and metadata. Use this to understand the structure and background of a text before diving into specific passages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Required: Title of the text or work (e.g. 'Genesis', 'Mishnah Berakhot', 'Shulchan Arukh, Orach Chaim', 'Rashi on Genesis')",
                    },
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="get_situational_info",
            description="Provides current Jewish calendar information including Hebrew date, weekly Torah portion (Parashat Hashavua), Daf Yomi, holidays, and other daily learning cycles. Use this for context about what's currently being studied or observed.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_links",
            description="Finds all cross-references and connections to a specific text passage, including commentaries, sources, parallels, and related texts. Use this to explore the web of textual relationships and find related discussions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Required: Specific text reference (e.g. 'Genesis 1:1', 'Berakhot 2a'). Use get_name tool first to validate complex references.",
                    },
                    "with_text": {
                        "type": "string",
                        "description": "Optional: Whether to include the actual text content of linked passages - '0' (just references, default and recommended) or '1' (include full text content, slower)",
                        "enum": ["0", "1"],
                        "default": "0"
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="search_texts",
            description="Searches across the entire Jewish library for passages containing specific terms. Works best with 1-2 Hebrew/Aramaic words or very specific English terms. Use filters to narrow search to specific categories. Returns passages with context snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Required: Search terms (works best with 1-2 words; Hebrew/Aramaic often more effective than English)",
                    },
                    "filters": {
                        "type": ["string", "array"],
                        "description": "Optional: Category paths to limit search scope. Use exact category paths like 'Tanakh', 'Mishnah', 'Talmud', 'Midrash', 'Halakhah', 'Kabbalah', 'Talmud/Bavli', 'Tanakh/Torah'. Can be single string or array of strings.",
                        "items": {
                            "type": "string"
                        }
                    },
                    "size": {
                        "type": "integer",
                        "description": "Optional: Maximum number of results to return (default: 10, max recommended: 20)",
                        "default": 10
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_in_book",
            description="Searches for content within one specific book or text work (e.g. within Genesis, within Talmud Berakhot, within Mishneh Torah). More focused than search_texts. Use this when you want to find passages within a particular work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Required: Search terms to find within the specified book",
                    },
                    "book_name": {
                        "type": "string",
                        "description": "Required: Exact name of the book to search within (e.g. 'Genesis', 'Berakhot', 'Bereishit Rabbah', 'Duties of the Heart', 'Mishneh Torah')",
                    },
                    "size": {
                        "type": "integer",
                        "description": "Optional: Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query", "book_name"],
            },
        ),
        types.Tool(
            name="search_dictionaries",
            description="Searches specifically within Jewish reference dictionaries (Jastrow Talmudic Dictionary, BDB Hebrew Dictionary, Klein Dictionary). Returns structured dictionary entries with definitions and etymologies. Use for word meanings and linguistic analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Required: Hebrew, Aramaic, or English term to look up in dictionaries",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_name",
            description="Validates and autocompletes text names, book titles, references, and topic slugs. Returns suggestions and exact matches. Use this tool FIRST when you have uncertain or partial references, or when you need to find the correct topic slug for get_topics. Essential for validating complex citations and discovering available topics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Required: Partial or complete text name, book title, reference, or topic name to validate/complete (e.g. 'Genes', 'Berakh', 'Rashi on', 'Moses', 'Sabbath')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional: Maximum number of suggestions to return (0 = no limit, default behavior varies)",
                    },
                    "type_filter": {
                        "type": "string",
                        "description": "Optional: Filter results by type - 'ref' (textual references), 'Collection' (text collections), 'Topic' (subject topics - use this to find topic slugs), 'TocCategory' (table of contents categories)",
                        "enum": ["ref", "Collection", "Topic", "TocCategory", "Term", "User"],
                    },
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="get_shape",
            description="Retrieves the hierarchical structure and organization of texts or categories. Shows how a work is divided (books, chapters, sections) or lists all texts within a category. Use this to understand the scope and organization before accessing specific content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Required: Text title (e.g. 'Genesis', 'Mishnah', 'Shulchan Arukh') or category name (e.g. 'Tanakh', 'Talmud', 'Midrash', 'Halakhah', 'Kabbalah', 'Liturgy', 'Jewish Thought')",
                    },
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="get_search_path_filter",
            description="Converts a book name into a proper search filter path for use with search_texts. Use this to get the exact filter string needed when you want to search within a specific book using search_texts instead of search_in_book.",
            inputSchema={
                "type": "object",
                "properties": {
                    "book_name": {
                        "type": "string",
                        "description": "Required: Name of the book to convert to a search filter path (e.g. 'Genesis', 'Berakhot', 'Bereishit Rabbah', 'Mishneh Torah')",
                    },
                },
                "required": ["book_name"],
            },
        ),
        types.Tool(
            name="get_topics",
            description="Retrieves detailed information about specific topics in Jewish thought and texts. Topics organize content thematically (e.g. Moses, Sabbath, Prayer, Torah). Returns rich metadata, descriptions, and optionally related content. Use get_name tool first to find the correct topic slug if uncertain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic_slug": {
                        "type": "string",
                        "description": "Required: Topic identifier slug (e.g. 'moses', 'sabbath', 'torah', 'prayer', 'sukkot'). Use get_name tool first with type_filter='Topic' to find the exact slug for uncertain topic names.",
                    },
                    "with_links": {
                        "type": "boolean",
                        "description": "Optional: Include links to related topics (default: false). Set to true to discover topic relationships.",
                        "default": False
                    },
                    "with_refs": {
                        "type": "boolean", 
                        "description": "Optional: Include text references tagged with this topic (default: false). Set to true to get all passages related to this topic.",
                        "default": False
                    },
                },
                "required": ["topic_slug"],
            },
        ),
        types.Tool(
            name="get_manuscripts",
            description="Retrieves historical manuscript images and metadata for text passages. Shows actual ancient/medieval manuscript pages containing the requested text. Provides visual and historical context with high-resolution images. Not all texts have manuscripts available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Required: Specific text reference to find manuscripts for (e.g. 'Genesis 1:1', 'Berakhot 2a', 'Esther 4:14'). Use get_name tool first to validate complex references.",
                    },
                },
                "required": ["reference"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can search the Jewish library and return formatted results.
    """
    logger.debug(f"Handling call_tool request for {name} with arguments {arguments}")
    
    # Handle case where arguments is None
    if arguments is None:
        arguments = {}
    
    try:
        if name == "get_text":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")  
                
                version_language = arguments.get("version_language")
                
                logger.debug(f"handle_get_text: {reference}, version_language: {version_language}")
                text = await get_text(reference, version_language)
                
                return [types.TextContent(
                    type="text",
                    text=text
                )]
            except Exception as err:
                logger.error(f"retrieve text error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_english_translations":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")
                
                logger.debug(f"handle_get_english_translations: {reference}")
                translations = await get_english_translations(reference)
                
                return [types.TextContent(
                    type="text",
                    text=translations
                )]
            except Exception as err:
                logger.error(f"retrieve english translations error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_links":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")
                
                with_text = arguments.get("with_text", "0")
                
                logger.debug(f"handle_get_links: {reference}, with_text: {with_text}")
                links = await get_links(reference, with_text)
                
                return [types.TextContent(
                    type="text",
                    text=links
                )]
            except Exception as err:
                logger.error(f"retrieve links error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "search_texts":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                
                filters = arguments.get("filters")
                size = arguments.get("size", 10)
                
                logger.debug(f"handle_search_texts: {query}, filters: {filters}, size: {size}")
                results = await search_texts(query, filters, size)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(results, ensure_ascii=False)
                )]
            except Exception as err:
                logger.error(f"search texts error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "search_in_book":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                
                book_name = arguments.get("book_name")
                if not book_name:
                    raise ValueError("Missing book_name parameter")
                
                size = arguments.get("size", 10)
                
                logger.debug(f"handle_search_in_book: {query}, book_name: {book_name}, size: {size}")
                results = await search_in_book(query, book_name, size)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(results, ensure_ascii=False)
                )]
            except Exception as err:
                logger.error(f"search in book error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "search_dictionaries":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                
                logger.debug(f"handle_search_dictionaries: {query}")
                results = await search_dictionaries(query)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(results, ensure_ascii=False)
                )]
            except Exception as err:
                logger.error(f"search dictionaries error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_name":
            try:
                name = arguments.get("name")
                if not name:
                    raise ValueError("Missing name parameter")
                
                limit = arguments.get("limit")
                type_filter = arguments.get("type_filter")
                
                logger.debug(f"handle_get_name: {name}, limit: {limit}, type_filter: {type_filter}")
                results = await get_name(name, limit, type_filter)
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"get name error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_shape":
            try:
                name = arguments.get("name")
                if not name:
                    raise ValueError("Missing name parameter")
                
                logger.debug(f"handle_get_shape: {name}")
                shape = await get_shape(name)
                
                return [types.TextContent(
                    type="text",
                    text=shape
                )]
            except Exception as err:
                logger.error(f"get shape error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_search_path_filter":
            try:
                book_name = arguments.get("book_name")
                if not book_name:
                    raise ValueError("Missing book_name parameter")
                
                logger.debug(f"handle_get_search_path_filter: {book_name}")
                filter_path = await get_search_path_filter(book_name)
                
                # Handle case where get_search_path_filter returns None (indicating error)
                if filter_path is None:
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Could not convert book name '{book_name}' to search filter path"
                    )]
                
                return [types.TextContent(
                    type="text",
                    text=filter_path
                )]
            except Exception as err:
                logger.error(f"get search path filter error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_topics":
            try:
                topic_slug = arguments.get("topic_slug")
                if not topic_slug:
                    raise ValueError("Missing topic_slug parameter")
                
                with_links = arguments.get("with_links", False)
                with_refs = arguments.get("with_refs", False)
                
                logger.debug(f"handle_get_topics: {topic_slug}, with_links: {with_links}, with_refs: {with_refs}")
                topics = await get_topics(topic_slug, with_links, with_refs)
                
                return [types.TextContent(
                    type="text",
                    text=topics
                )]
            except Exception as err:
                logger.error(f"get topics error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_manuscripts":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")
                
                logger.debug(f"handle_get_manuscripts: {reference}")
                manuscripts = await get_manuscripts(reference)
                
                return [types.TextContent(
                    type="text",
                    text=manuscripts
                )]
            except Exception as err:
                logger.error(f"get manuscripts error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_index":
            try:
                title = arguments.get("title")
                if not title:
                    raise ValueError("Missing title parameter")
                
                logger.debug(f"handle_get_index: {title}")
                index = await get_index(title)
                
                return [types.TextContent(
                    type="text",
                    text=index
                )]
            except Exception as err:
                logger.error(f"get index error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "get_situational_info":
            try:
                logger.debug("handle_get_situational_info")
                info = await get_situational_info()
                
                return [types.TextContent(
                    type="text",
                    text=info
                )]
            except Exception as err:
                logger.error(f"get situational info error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        else:
            logger.error(f"Unknown tool: {name}")
            return [types.TextContent(
                type="text",
                text=f"Error: Unknown tool {name}"
            )]
    
    except Exception as err:
        logger.error(f"Tool execution error: {err}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(err)}"
        )]

async def main():
    try:
        logger.info("Starting Jewish Library MCP server...")
        
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sefaria_jewish_library",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise