import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("neuralpulse.ingestion.rss_parser")


class RSSParser:
    @staticmethod
    def parse_datetime(date_str: Optional[str]) -> datetime:
        """Parse common RSS/Atom publication date formats to standard datetime."""
        if not date_str:
            return datetime.utcnow()
        
        try:
            # RSS 2.0 format (e.g. "Wed, 23 May 2026 20:00:00 GMT" or "Wed, 23 May 2026 20:00:00 +0000")
            return parsedate_to_datetime(date_str).replace(tzinfo=None)
        except Exception:
            pass

        # Try parsing ISO 8601 Atom formats (e.g. "2026-05-23T20:00:00Z" or "2026-05-23T20:00:00+00:00")
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=None)
            except ValueError:
                continue

        logger.warning(f"Could not parse datetime string: '{date_str}'. Defaulting to current UTC datetime.")
        return datetime.utcnow()

    @classmethod
    def parse_xml_feed(cls, xml_content: str) -> List[Dict[str, Any]]:
        """Parse raw XML content string into normalized article dictionaries."""
        articles = []
        try:
            # Parse XML document tree
            root = ET.fromstring(xml_content)
            
            # Check if RSS format (contains 'channel' element)
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item"):
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    date_elem = item.find("pubDate")
                    creator_elem = item.find("{http://purl.org/dc/elements/1.1/}creator") # dc:creator tag namespace
                    
                    title = title_elem.text if title_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""
                    description = desc_elem.text if desc_elem is not None else ""
                    pub_date_str = date_elem.text if date_elem is not None else None
                    author = creator_elem.text if creator_elem is not None else "Unknown"

                    if title and link:
                        articles.append({
                            "title": title.strip(),
                            "url": link.strip(),
                            "summary": description.strip() if description else "",
                            "published_at": cls.parse_datetime(pub_date_str),
                            "author": author.strip()
                        })
                return articles

            # Check if Atom format (e.g. starts with feed/entry)
            # Remove namespace prefixes from tags to simplify element querying
            # By parsing XML tags directly or using custom searches
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            if entries:
                for entry in entries:
                    title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
                    link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                    summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
                    content_elem = entry.find("{http://www.w3.org/2005/Atom}content")
                    date_elem = entry.find("{http://www.w3.org/2005/Atom}published") or entry.find("{http://www.w3.org/2005/Atom}updated")
                    
                    title = title_elem.text if title_elem is not None else ""
                    
                    # Atom links use href attribute e.g. <link href="..."/>
                    link = ""
                    if link_elem is not None:
                        link = link_elem.attrib.get("href", "")
                    
                    # Fallback Atom summary/content
                    description = ""
                    if summary_elem is not None and summary_elem.text:
                        description = summary_elem.text
                    elif content_elem is not None and content_elem.text:
                        description = content_elem.text
                        
                    pub_date_str = date_elem.text if date_elem is not None else None
                    
                    # Author parsing
                    author = "Unknown"
                    author_elem = entry.find("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name")
                    if author_elem is not None and author_elem.text:
                        author = author_elem.text

                    if title and link:
                        articles.append({
                            "title": title.strip(),
                            "url": link.strip(),
                            "summary": description.strip() if description else "",
                            "published_at": cls.parse_datetime(pub_date_str),
                            "author": author.strip()
                        })
                return articles

            logger.warning("XML root tag does not match standard RSS or Atom namespaces")
            
        except ET.ParseError as pe:
            logger.error(f"Failed to parse XML string structure: {pe}")
        except Exception as e:
            logger.error(f"Unexpected error parsing feed content: {e}")
            
        return articles
