import datetime
from calendar import error

import requests
import json
import logging
import urllib.parse
import hdate

SEFARIA_API_BASE_URL = "https://sefaria.org"

def get_request_json_data(endpoint, ref=None, param=None):
    """
    Helper function to make GET requests to the Sefaria API and parse the JSON response.
    """
    url = f"{SEFARIA_API_BASE_URL}/{endpoint}"

    if ref:
        url += f"{ref}"

    if param:
        url += f"?{param}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None

def get_parasha_data():
    """
    Retrieves the weekly Parasha data using the Calendars API.
    """
    data = get_request_json_data("api/calendars")

    if data:
        calendar_items = data.get('calendar_items', [])
        for item in calendar_items:
            if item.get('title', {}).get('en') == 'Parashat Hashavua':
                parasha_ref = item.get('ref')
                parasha_name = item.get('displayValue', {}).get('en')
                return parasha_ref, parasha_name
    
    print("Could not retrieve Parasha data.")
    return None, None

async def get_situational_info():
    """
    Returns situational information related to the Jewish calendar.
    
    Returns:
        str: JSON string containing:
            - Current date in the Gregorian and Hebrew calendars
            - Current year
            - Current Parshat HaShavuah and other daily learning
            - Additional calendar information from Sefaria
    """
    try:
        # Get current Hebrew date
        # Note: This may be off by a day if server time and user timezone differ
        now = datetime.datetime.now()
        h = hdate.HDate(now, hebrew=False)  # Includes day of week
        
        # Get extended calendar information from Sefaria
        # Note: This will retrieve the Israel Parasha when Israel and diaspora differ
        calendar_data = get_request_json_data("api/calendars")
        
        if not calendar_data:
            return json.dumps({
                "error": "Could not retrieve calendar data from Sefaria",
                "Hebrew Date": str(h)
            })
        
        # Add Hebrew date to the response
        calendar_data["Hebrew Date"] = str(h)
        
        return json.dumps(calendar_data, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Error retrieving situational information: {str(e)}"
        })


async def get_commentaries(parasha_ref)-> list[str]:
    """
    Retrieves and filters commentaries on the given verse.
    """
    data = get_request_json_data("api/related/", parasha_ref)

    commentaries = []
    if data and "links" in data:
        for linked_text in data["links"]:
            if linked_text.get('type') == 'commentary':
                commentaries.append(linked_text.get('sourceHeRef'))

    return commentaries

async def get_text(reference: str, version_language: str = None) -> str:
    """
    Retrieves the text for a given reference.
    
    Args:
        reference (str): The reference to retrieve (e.g. 'Genesis 1:1' or 'שולחן ערוך אורח חיים סימן א')
        version_language (str, optional): Language version to retrieve. Options:
            - None: returns all versions
            - "source": returns the original source language (usually Hebrew)
            - "english": returns the English translation
            - "both": returns both source and English
    
    Returns:
        str: JSON string containing the text data
    """
    try:
        # Construct the API URL
        url = f"{SEFARIA_API_BASE_URL}/api/v3/texts/{urllib.parse.quote(reference)}"
        params = []
        
        # Add version parameters based on request
        if version_language == "source":
            params.append("version=source")
        elif version_language == "english":
            params.append("version=english")
        elif version_language == "both":
            params.append("version=english&version=source")
        
        if params:
            url += "?" + "&".join(params)
        
        logging.debug(f"Text API request URL: {url}")
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Process the response to filter only relevant fields
        if "versions" in data:
            filtered_versions = []
            for version in data["versions"]:
                filtered_version = {
                    "languageFamilyName": version.get("languageFamilyName", ""),
                    "text": version.get("text", ""),
                    "versionTitle": version.get("versionTitle", "")
                }
                filtered_versions.append(filtered_version)
            data["versions"] = filtered_versions
        
        # Filter available_versions array if present
        if "available_versions" in data:
            filtered_available_versions = []
            for version in data["available_versions"]:
                filtered_version = {
                    "versionTitle": version.get("versionTitle", ""),
                    "languageFamilyName": version.get("languageFamilyName", "")
                }
                filtered_available_versions.append(filtered_version)
            data["available_versions"] = filtered_available_versions
        
        return json.dumps(data, indent=2)
    
    except requests.exceptions.RequestException as e:
        return f"Error fetching text: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error parsing response: {str(e)}"

async def search_texts(query: str, slop: int =2, filters=None, size=10):
    """
    Search for texts in the Sefaria library.
    
    Args:
        query (str): The search query
        slop (int, optional): The maximum distance between each query word in the resulting document. 0 means an exact match must be found. defaults to 2
        filters (list, optional): Filters to apply to the text path in English (Examples: "Shulkhan Arukh", "maimonides", "talmud").
        size (int, optional): Number of results to return. defaults to 10.
        
    Returns:
        str: Formatted search results
    """
    # Use the www subdomain as specified in the documentation
    url = "https://www.sefaria.org/api/search-wrapper"
    
    # Build the request payload
    payload = {
        "query": query,
        "type": "text",
        "field":  "naive_lemmatizer",
        "size": size,
  "source_proj": True,
        "sort_fields": [
    "pagesheetrank"
  ],
  "sort_method": "score",
        "slop": slop,
     
    }
    if filters:
        payload["filters"] = filters

    
    # Make the POST request
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        logging.debug(f"Sefaria's Search API response: {response.text}")
        
        # Parse JSON response
        data = response.json()
        
        print(data)
        
        # Format the results
        results = []
        
        # Check if we have hits in the response
        if "hits" in data and "hits" in data["hits"]:
            # Get the actual total hits count
            total_hits = data["hits"].get("total", 0)
            # Handle different response formats
            if isinstance(total_hits, dict) and "value" in total_hits:
                total_hits = total_hits["value"]
         
            # Process each hit
            for hit in data["hits"]["hits"]:
                source = hit["_source"]
                ref = source["ref"]
                heRef = source["heRef"]
                
                # Get the content snippet
                text_snippet = ""
                
                # Get highlighted text if available (this contains the search term highlighted)
                if "highlight" in hit:
                    for field_name, highlights in hit["highlight"].items():
                        if highlights and len(highlights) > 0:
                            # Join multiple highlights with ellipses
                            text_snippet = " [...] ".join(highlights)
                            break
                
                # If no highlight, use content from the source
                if not text_snippet:
                    # Try different fields that might contain content
                    for field_name in ["naive_lemmatizer", "exact"]:
                        if field_name in source and source[field_name]:
                            content = source[field_name]
                            if isinstance(content, str):
                                # Limit to a reasonable snippet length
                                text_snippet = content[:300] + ("..." if len(content) > 300 else "")
                                break
             
                # Add the formatted result
                results.append(f"Reference: {ref}\n Hebrew Reference: {heRef}\n Highlight: {text_snippet}\n")
        
        # Return a message if no results were found
        if len(results) == 0:
            return f"No results found for '{query}'."
        logging.debug(f"formated results: {results}")
        return "\n".join(results)
    
    except json.JSONDecodeError as e:
        return f"Error: Failed to parse JSON response: {str(e)}"
    except requests.exceptions.RequestException as e:
        return f"Error during search API request: {str(e)}"
        
async def get_name_autocomplete(name: str, limit: int = None, type_filter: str = None) -> str:
    """
    Get autocomplete information for a name from Sefaria's name API.
    
    Args:
        name (str): The text string to match against Sefaria's data collections
        limit (int, optional): Number of results to return (0 indicates no limit)
        type_filter (str, optional): Filter results to a specific type (ref, Collection, Topic, etc.)
        
    Returns:
        str: JSON response from the name API
    """
    try:
        # URL encode the name
        encoded_name = urllib.parse.quote(name)
        
        # Build the URL with parameters
        url = f"{SEFARIA_API_BASE_URL}/api/name/{encoded_name}"
        params = []
        
        if limit is not None:
            params.append(f"limit={limit}")
            
        if type_filter is not None:
            params.append(f"type={type_filter}")
            
        if params:
            url += "?" + "&".join(params)
            
        logging.debug(f"Name API request URL: {url}")
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        logging.debug(f"Name API response: {json.dumps(data)}")
        
        # Return the raw JSON data
        return json.dumps(data, indent=2)
    
    except json.JSONDecodeError as e:
        return f"Error: Failed to parse JSON response: {str(e)}"
    except requests.exceptions.RequestException as e:
        return f"Error during name API request: {str(e)}"

async def get_links(reference: str, with_text: str = "0") -> str:
    """
    Get links (connections) for a given textual reference.
    
    Args:
        reference (str): A valid Sefaria textual reference
        with_text (str, optional): Include the text content of linked resources. 
            Options: "0" (exclude text, default) or "1" (include text).
            Note: Individual texts can be loaded using the texts endpoint.
            
    Returns:
        str: JSON string containing links data
    """
    try:
        # URL encode the reference
        encoded_reference = urllib.parse.quote(reference)
        
        # Build the URL with parameters
        url = f"{SEFARIA_API_BASE_URL}/api/links/{encoded_reference}"
        params = [f"with_text={with_text}"]
            
        if params:
            url += "?" + "&".join(params)
            
        logging.debug(f"Links API request URL: {url}")
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        logging.debug(f"Links API response: {json.dumps(data)}")
        
        # Return the raw JSON data
        return json.dumps(data, indent=2)
    
    except json.JSONDecodeError as e:
        return f"Error: Failed to parse JSON response: {str(e)}"
    except requests.exceptions.RequestException as e:
        return f"Error during links API request: {str(e)}"

async def get_shape(name: str) -> str:
    """
    Get the shape (structure) of a text or list texts in a category/corpus.
    
    Args:
        name (str): Either a text name (e.g., "Genesis") or a category/corpus name 
            (e.g., "Tanakh", "Mishnah", "Talmud", "Midrash", "Halakhah", "Kabbalah", 
            "Liturgy", "Jewish Thought", "Tosefta", "Chasidut", "Musar", "Responsa", 
            "Reference", "Second Temple", "Yerushalmi", "Midrash Rabbah", "Bavli")
            
    Returns:
        str: JSON string containing shape data for the text or category
    """
    try:
        # URL encode the name
        encoded_name = urllib.parse.quote(name)
        
        # Build the URL
        url = f"{SEFARIA_API_BASE_URL}/api/shape/{encoded_name}"
            
        logging.debug(f"Shape API request URL: {url}")
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        logging.debug(f"Shape API response: {json.dumps(data)}")
        
        # Return the raw JSON data
        return json.dumps(data, indent=2)
    
    except json.JSONDecodeError as e:
        return f"Error: Failed to parse JSON response: {str(e)}"
    except requests.exceptions.RequestException as e:
        return f"Error during shape API request: {str(e)}"
