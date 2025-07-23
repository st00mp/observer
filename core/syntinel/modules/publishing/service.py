import os
import httpx
from core.syntinel.db import Article, Draft
from typing import Dict, Any

# External service URLs
WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://writer-agent:8000")

async def generate_content(article: Article, style: str) -> str:
    """
    Generate content for a draft based on an article and style
    
    Args:
        article: Article to base the content on
        style: Style of the content (serious, sarcastic, troll)
        
    Returns:
        Generated content as string
    """
    try:
        # Call Writer-Agent to generate content
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for generation
            response = await client.post(
                f"{WRITER_AGENT_URL}/generate",
                json={
                    "title": article.title,
                    "content": article.markdown_content or article.content,
                    "style": style
                }
            )
            
            if response.status_code != 200:
                # Fallback to template-based generation
                return generate_fallback_content(article, style)
            
            result = response.json()
            return result.get("content", "Content generation failed.")
    
    except Exception as e:
        # Fallback in case of exception
        return generate_fallback_content(article, style)

def generate_fallback_content(article: Article, style: str) -> str:
    """
    Generate fallback content when Writer-Agent is unavailable
    
    Args:
        article: Article to base the content on
        style: Style of the content
        
    Returns:
        Template-based content as string
    """
    title = article.title
    source = article.source
    
    if style == "serious":
        return f"Breaking News: {title} - More details available from {source}. This appears to be an important development."
    elif style == "sarcastic":
        return f"Oh great, another wonderful piece of news: '{title}' - straight from the ever-reliable {source}. Just what we needed today!"
    elif style == "troll":
        return f"YOU WON'T BELIEVE WHAT JUST HAPPENED!! {title.upper()}!!! This changes EVERYTHING! {source} strikes again!!!"
    else:
        return f"News Update: {title} - Source: {source}"

async def publish_draft_to_platforms(draft: Draft) -> Dict[str, Any]:
    """
    Publish a draft to various social media platforms
    
    Args:
        draft: Draft to publish
        
    Returns:
        Dictionary with status of each platform
    """
    # This would connect to social media APIs
    # For now it's a placeholder
    
    platforms = {
        "telegram": "success",
        "x": "not_implemented",
        "mastodon": "not_implemented"
    }
    
    # In a real implementation, we would call the respective APIs here
    
    return platforms
