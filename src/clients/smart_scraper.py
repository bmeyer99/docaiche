"""
Smart Web Scraper with LLM-powered content extraction
Fetches documentation from any web source intelligently
"""

import logging
import aiohttp
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import markdownify

from src.llm.client import LLMProviderClient
from src.search.llm_query_analyzer import QueryIntent
from src.document_processing.models import DocumentContent
from src.clients.webscraper import WebScraperClient

logger = logging.getLogger(__name__)


class SmartWebScraper(WebScraperClient):
    """Enhanced web scraper with intelligent content extraction"""
    
    def __init__(self, llm_client: LLMProviderClient, config=None):
        super().__init__(config)
        self.llm = llm_client
        
    async def fetch_docs_intelligently(
        self,
        url: str,
        intent: QueryIntent
    ) -> List[DocumentContent]:
        """
        Intelligently fetch documentation from any web URL
        
        Args:
            url: Web URL to fetch from
            intent: Query intent for context
            
        Returns:
            List of document content
        """
        try:
            # Fetch the web page
            content = await self.fetch_url(url)
            if not content:
                return []
            
            # Convert HTML to text/markdown
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Use LLM to identify main documentation content
            main_content = await self._extract_main_content(soup, intent)
            
            if not main_content:
                # Fallback to simple extraction
                main_content = self._simple_extract(soup)
            
            # Convert to markdown
            markdown_content = markdownify.markdownify(str(main_content))
            
            # Create DocumentContent
            doc = DocumentContent(
                content_id=f"web_{hash(url)}",
                title=self._extract_title(soup, intent),
                text=markdown_content,
                source_url=url,
                metadata={
                    "technology": intent.technology,
                    "doc_type": intent.doc_type,
                    "topics": intent.topics,
                    "fetched_from": "web"
                }
            )
            
            # Check if we should follow links for more content
            related_links = await self._find_related_links(soup, url, intent)
            
            docs = [doc]
            
            # Fetch related pages (limit to avoid infinite crawling)
            for link in related_links[:3]:
                try:
                    related_docs = await self.fetch_docs_intelligently(link, intent)
                    docs.extend(related_docs)
                except Exception as e:
                    logger.warning(f"Failed to fetch related link {link}: {e}")
                    
            return docs
            
        except Exception as e:
            logger.error(f"Smart web scraping failed for {url}: {e}")
            return []
    
    async def _extract_main_content(
        self,
        soup: BeautifulSoup,
        intent: QueryIntent
    ) -> Optional[Any]:
        """
        Use LLM to identify main documentation content
        """
        try:
            # Get page structure
            structure = self._get_page_structure(soup)
            
            prompt = f"""
            Analyze this web page structure for {intent.technology} documentation.
            
            Looking for: {intent.doc_type} content about {', '.join(intent.topics)}
            
            Page structure:
            {structure[:2000]}  # Limit to prevent token overflow
            
            Identify the CSS selector or HTML element that contains the main documentation content.
            Common patterns:
            - <main> or <article> tags
            - Elements with class names like: content, documentation, docs, tutorial, guide
            - Elements with id like: main, content, documentation
            
            Return the most specific CSS selector that would capture the main content.
            Example: "article.documentation", "#main-content", ".docs-content"
            
            Return ONLY the CSS selector string.
            """
            
            selector = await self.llm.generate(prompt)
            selector = selector.strip().strip('"').strip("'")
            
            # Try to find content with the selector
            if selector:
                content = soup.select_one(selector)
                if content:
                    return content
                    
        except Exception as e:
            logger.error(f"LLM content extraction failed: {e}")
            
        return None
    
    def _simple_extract(self, soup: BeautifulSoup) -> Any:
        """
        Simple fallback content extraction
        """
        # Try common content containers
        for selector in [
            'main', 'article', '[role="main"]',
            '.content', '.documentation', '.docs',
            '#content', '#documentation', '#main'
        ]:
            content = soup.select_one(selector)
            if content:
                return content
                
        # Last resort: get body
        return soup.body or soup
    
    def _extract_title(self, soup: BeautifulSoup, intent: QueryIntent) -> str:
        """
        Extract page title
        """
        # Try meta title
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
            
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
            
        return f"{intent.technology} Documentation"
    
    def _get_page_structure(self, soup: BeautifulSoup) -> str:
        """
        Get simplified page structure for LLM analysis
        """
        structure = []
        
        def extract_structure(element, level=0):
            if level > 3:  # Limit depth
                return
                
            if element.name:
                attrs = []
                if element.get('id'):
                    attrs.append(f"id='{element['id']}'")
                if element.get('class'):
                    attrs.append(f"class='{' '.join(element['class'])}'")
                    
                attr_str = f" {' '.join(attrs)}" if attrs else ""
                structure.append(f"{'  ' * level}<{element.name}{attr_str}>")
                
                # Only include structure, not content
                for child in element.children:
                    if hasattr(child, 'name'):
                        extract_structure(child, level + 1)
                        
        extract_structure(soup.body if soup.body else soup)
        return '\n'.join(structure[:100])  # Limit lines
    
    async def _find_related_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        intent: QueryIntent
    ) -> List[str]:
        """
        Find related documentation links to follow
        """
        try:
            # Get all links
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True)
                
                if href and text:
                    # Make absolute URL
                    from urllib.parse import urljoin
                    absolute_url = urljoin(base_url, href)
                    links.append({
                        'url': absolute_url,
                        'text': text
                    })
            
            if not links:
                return []
                
            # Use LLM to identify relevant links
            prompt = f"""
            From these links on a {intent.technology} documentation page,
            identify which ones lead to related {intent.doc_type} content
            about {', '.join(intent.topics)}.
            
            Links:
            {chr(10).join([f"- {link['text']}: {link['url']}" for link in links[:50]])}
            
            Return a JSON array of the most relevant URLs (max 5).
            Only include URLs that likely contain documentation content.
            Avoid: login pages, external sites, images, downloads.
            
            Example: ["https://example.com/docs/tutorial", "https://example.com/docs/async"]
            """
            
            response = await self.llm.generate(prompt)
            
            # Parse response
            import json
            try:
                relevant_urls = json.loads(response.strip())
                if isinstance(relevant_urls, list):
                    return relevant_urls[:5]
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to find related links: {e}")
            
        return []