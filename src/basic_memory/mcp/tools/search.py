"""Search tools for Basic Memory MCP server."""

from typing import Optional, List, Union
from datetime import datetime
from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.mcp.tools.utils import call_post
from basic_memory.schemas.search import SearchQuery, SearchResponse, SearchItemType
from basic_memory.mcp.async_client import client


@mcp.tool(
    description="""Search across all content in the knowledge base.
    
Use ONE of these primary search modes:
- text: Full-text search with boolean operators (AND, OR, NOT)
- title: Search only in titles
- permalink: Exact permalink match
- permalink_pattern: Pattern matching with * for permalinks

Optionally filter by:
- item_types: List of types ["entity", "observation", "relation"]
- entity_types: List of entity type names
- after_date: Only items after date (ISO format or natural language like "1 week ago")""",
)
async def search_notes(
    text: Optional[str] = None,
    title: Optional[str] = None,
    permalink: Optional[str] = None,
    permalink_pattern: Optional[str] = None,
    item_types: Optional[List[str]] = None,
    entity_types: Optional[List[str]] = None,
    after_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> SearchResponse:
    """Search across all content in the knowledge base.

    Args:
        text: Full-text search with boolean operators (e.g., "project AND planning")
        title: Search only in titles
        permalink: Exact permalink match
        permalink_pattern: Pattern matching for permalinks (e.g., "docs/*-notes")
        item_types: List of types to search (e.g., ["entity", "observation"])
        entity_types: List of entity types to filter by
        after_date: Date filter (ISO format or natural language)
        page: The page number of results to return (default 1)
        page_size: The number of results per page (default 10)

    Returns:
        SearchResponse with results and pagination info

    Examples:
        # Basic text search
        results = await search_notes(text="project planning")

        # Boolean operators
        results = await search_notes(text="project AND planning")
        results = await search_notes(text="project OR meeting")
        results = await search_notes(text="project NOT meeting")
        results = await search_notes(text="(project OR planning) AND notes")

        # Search with type filter
        results = await search_notes(
            text="meeting notes",
            item_types=["entity"]
        )

        # Search for recent content
        results = await search_notes(
            text="bug report",
            after_date="1 week ago"
        )

        # Pattern matching on permalinks
        results = await search_notes(
            permalink_pattern="docs/meeting-*"
        )
    """
    # Convert item_types strings to SearchItemType enum values
    types = None
    if item_types:
        types = [SearchItemType(t.lower()) for t in item_types]

    # Construct the SearchQuery
    query = SearchQuery(
        text=text,
        title=title,
        permalink=permalink,
        permalink_match=permalink_pattern,
        types=types,
        entity_types=entity_types,
        after_date=after_date
    )

    logger.info(f"Searching with query: {query}")
    response = await call_post(
        client,
        "/search/",
        json=query.model_dump(),
        params={"page": page, "page_size": page_size},
    )
    return SearchResponse.model_validate(response.json())
