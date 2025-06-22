"""
Content Analyzers - PRD-010
Content analysis implementations for knowledge enrichment.

Provides content analysis, relationship mapping, and tag generation
capabilities as specified in PRD-010.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from .models import ContentRelationship, EnrichmentType
from .exceptions import AnalysisError, RelationshipMappingError, TagGenerationError

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Core content analyzer for enrichment operations.
    
    Performs deep analysis of documentation structure and content
    as specified in PRD-010.
    """
    
    def __init__(self):
        """Initialize content analyzer."""
        self.patterns = {
            'heading': re.compile(r'^#+\s+(.+)$', re.MULTILINE),
            'code_block': re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL),
            'inline_code': re.compile(r'`([^`]+)`'),
            'link': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            'list_item': re.compile(r'^[\s]*[-*+]\s+(.+)$', re.MULTILINE),
            'api_endpoint': re.compile(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)'),
            'function_def': re.compile(r'def\s+(\w+)\s*\('),
            'class_def': re.compile(r'class\s+(\w+)'),
            'import_stmt': re.compile(r'(?:from\s+(\S+)\s+)?import\s+([^\n]+)')
        }
        
        logger.info("ContentAnalyzer initialized")
    
    async def analyze_content(self, content: str, content_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive content analysis.
        
        Args:
            content: Content to analyze
            content_id: Content identifier
            metadata: Existing content metadata
            
        Returns:
            Analysis results with structure and semantic information
            
        Raises:
            AnalysisError: If analysis fails
        """
        try:
            logger.debug(f"Starting content analysis for {content_id}")
            
            analysis_result = {
                'content_id': content_id,
                'structure_analysis': await self._analyze_structure(content),
                'semantic_analysis': await self._analyze_semantics(content),
                'code_analysis': await self._analyze_code_elements(content),
                'link_analysis': await self._analyze_links(content),
                'complexity_metrics': await self._calculate_complexity(content),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            logger.debug(f"Content analysis completed for {content_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Content analysis failed for {content_id}: {e}")
            raise AnalysisError(
                f"Content analysis failed: {str(e)}",
                content_id=content_id,
                analysis_type="content_analysis"
            )
    
    async def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """
        Analyze document structure.
        
        Args:
            content: Content to analyze
            
        Returns:
            Structure analysis results
        """
        headings = self.patterns['heading'].findall(content)
        code_blocks = self.patterns['code_block'].findall(content)
        list_items = self.patterns['list_item'].findall(content)
        
        # Calculate heading hierarchy
        heading_levels = []
        for line in content.split('\n'):
            if line.strip().startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_levels.append(level)
        
        return {
            'headings': {
                'count': len(headings),
                'titles': headings[:10],  # Limit for storage
                'levels': heading_levels
            },
            'code_blocks': {
                'count': len(code_blocks),
                'languages': list(set([lang for lang, _ in code_blocks if lang]))
            },
            'lists': {
                'count': len(list_items),
                'items': list_items[:5]  # Sample items
            },
            'document_sections': len(headings),
            'has_toc': 'table of contents' in content.lower() or 'toc' in content.lower()
        }
    
    async def _analyze_semantics(self, content: str) -> Dict[str, Any]:
        """
        Perform semantic analysis of content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Semantic analysis results
        """
        # Extract key terms and concepts
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        word_freq = {}
        for word in words:
            if word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'say', 'each', 'which', 'their', 'time', 'will', 'about', 'there', 'many', 'some', 'what', 'would', 'make']:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get most frequent terms
        top_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Identify technical concepts
        technical_patterns = [
            r'\b(?:API|REST|HTTP|JSON|XML|SQL|NoSQL|Docker|Kubernetes)\b',
            r'\b(?:function|method|class|object|variable|parameter)\b',
            r'\b(?:database|server|client|endpoint|request|response)\b'
        ]
        
        technical_terms = []
        for pattern in technical_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            technical_terms.extend(matches)
        
        return {
            'top_terms': [term for term, freq in top_terms],
            'term_frequencies': dict(top_terms[:10]),
            'technical_terms': list(set(technical_terms)),
            'content_density': len(words) / max(1, len(content.split('\n'))),
            'readability_score': await self._calculate_readability(content)
        }
    
    async def _analyze_code_elements(self, content: str) -> Dict[str, Any]:
        """
        Analyze code elements in content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Code analysis results
        """
        functions = self.patterns['function_def'].findall(content)
        classes = self.patterns['class_def'].findall(content)
        imports = self.patterns['import_stmt'].findall(content)
        api_endpoints = self.patterns['api_endpoint'].findall(content)
        inline_code = self.patterns['inline_code'].findall(content)
        
        return {
            'functions': {
                'count': len(functions),
                'names': functions[:10]
            },
            'classes': {
                'count': len(classes),
                'names': classes[:10]
            },
            'imports': {
                'count': len(imports),
                'modules': [imp[1] if imp[0] else imp[1] for imp in imports[:10]]
            },
            'api_endpoints': {
                'count': len(api_endpoints),
                'endpoints': [f"{method} {path}" for method, path in api_endpoints[:10]]
            },
            'inline_code_count': len(inline_code),
            'has_code_examples': len(self.patterns['code_block'].findall(content)) > 0
        }
    
    async def _analyze_links(self, content: str) -> Dict[str, Any]:
        """
        Analyze links and references in content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Link analysis results
        """
        links = self.patterns['link'].findall(content)
        
        external_links = []
        internal_links = []
        
        for text, url in links:
            if url.startswith('http'):
                external_links.append((text, url))
            else:
                internal_links.append((text, url))
        
        return {
            'total_links': len(links),
            'external_links': {
                'count': len(external_links),
                'urls': [url for _, url in external_links[:10]]
            },
            'internal_links': {
                'count': len(internal_links),
                'refs': [url for _, url in internal_links[:10]]
            }
        }
    
    async def _calculate_complexity(self, content: str) -> Dict[str, Any]:
        """
        Calculate content complexity metrics.
        
        Args:
            content: Content to analyze
            
        Returns:
            Complexity metrics
        """
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            'line_count': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'sentence_count': len(sentences),
            'avg_sentence_length': sum(len(s.split()) for s in sentences) / max(1, len(sentences)),
            'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
            'complexity_score': await self._calculate_complexity_score(content)
        }
    
    async def _calculate_readability(self, content: str) -> float:
        """
        Calculate basic readability score.
        
        Args:
            content: Content to analyze
            
        Returns:
            Readability score (0.0-1.0)
        """
        words = re.findall(r'\b\w+\b', content)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s for s in sentences if s.strip()]
        
        if not words or not sentences:
            return 0.0
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Simple readability score based on sentence length
        if avg_words_per_sentence <= 15:
            return 0.9
        elif avg_words_per_sentence <= 20:
            return 0.7
        elif avg_words_per_sentence <= 25:
            return 0.5
        else:
            return 0.3
    
    async def _calculate_complexity_score(self, content: str) -> float:
        """
        Calculate content complexity score.
        
        Args:
            content: Content to analyze
            
        Returns:
            Complexity score (0.0-1.0)
        """
        # Factors that increase complexity
        code_blocks = len(self.patterns['code_block'].findall(content))
        headings = len(self.patterns['heading'].findall(content))
        links = len(self.patterns['link'].findall(content))
        
        # Normalize by content length
        content_length = len(content.split())
        
        if content_length == 0:
            return 0.0
        
        complexity = (code_blocks * 10 + headings * 5 + links * 2) / content_length
        return min(1.0, complexity * 100)  # Scale and cap at 1.0


class RelationshipAnalyzer:
    """
    Analyzer for identifying relationships between documents.
    
    Maps content relationships and connections as specified in PRD-010.
    """
    
    def __init__(self):
        """Initialize relationship analyzer."""
        self.similarity_threshold = 0.3
        
        logger.info("RelationshipAnalyzer initialized")
    
    async def analyze_relationships(self, content_id: str, content: str, existing_content: List[Dict[str, Any]]) -> List[ContentRelationship]:
        """
        Identify relationships with existing content.
        
        Args:
            content_id: Current content ID
            content: Content text
            existing_content: List of existing content items
            
        Returns:
            List of identified relationships
            
        Raises:
            RelationshipMappingError: If relationship analysis fails
        """
        try:
            logger.debug(f"Analyzing relationships for {content_id}")
            
            relationships = []
            
            for existing in existing_content:
                if existing['content_id'] == content_id:
                    continue
                
                relationship = await self._calculate_relationship(
                    content_id, content, existing['content_id'], existing.get('content', '')
                )
                
                if relationship:
                    relationships.append(relationship)
            
            logger.debug(f"Found {len(relationships)} relationships for {content_id}")
            return relationships
            
        except Exception as e:
            logger.error(f"Relationship analysis failed for {content_id}: {e}")
            raise RelationshipMappingError(
                f"Relationship analysis failed: {str(e)}",
                source_content_id=content_id
            )
    
    async def _calculate_relationship(self, source_id: str, source_content: str, target_id: str, target_content: str) -> Optional[ContentRelationship]:
        """
        Calculate relationship between two content items.
        
        Args:
            source_id: Source content ID
            source_content: Source content text
            target_id: Target content ID
            target_content: Target content text
            
        Returns:
            ContentRelationship if relationship found, None otherwise
        """
        # Calculate content similarity
        similarity = await self._calculate_similarity(source_content, target_content)
        
        if similarity < self.similarity_threshold:
            return None
        
        # Determine relationship type
        relationship_type = await self._determine_relationship_type(source_content, target_content, similarity)
        
        return ContentRelationship(
            source_content_id=source_id,
            target_content_id=target_id,
            relationship_type=relationship_type,
            confidence_score=similarity,
            metadata={
                'similarity_score': similarity,
                'analyzed_at': datetime.utcnow().isoformat()
            }
        )
    
    async def _calculate_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content pieces.
        
        Args:
            content1: First content
            content2: Second content
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Simple word-based similarity
        words1 = set(re.findall(r'\b\w+\b', content1.lower()))
        words2 = set(re.findall(r'\b\w+\b', content2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _determine_relationship_type(self, content1: str, content2: str, similarity: float) -> str:
        """
        Determine the type of relationship between content items.
        
        Args:
            content1: First content
            content2: Second content
            similarity: Calculated similarity score
            
        Returns:
            Relationship type string
        """
        # High similarity suggests duplicate or similar content
        if similarity > 0.8:
            return "duplicate"
        elif similarity > 0.6:
            return "similar"
        elif similarity > 0.4:
            return "related"
        else:
            return "reference"


class TagGenerator:
    """
    Automated tag generation for content enrichment.
    
    Generates contextual tags based on content analysis as specified in PRD-010.
    """
    
    def __init__(self):
        """Initialize tag generator."""
        self.technology_tags = {
            'python', 'javascript', 'java', 'go', 'rust', 'typescript',
            'react', 'vue', 'angular', 'django', 'flask', 'fastapi',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'api', 'rest', 'graphql', 'microservices', 'serverless'
        }
        
        self.concept_tags = {
            'tutorial', 'guide', 'documentation', 'example', 'reference',
            'beginner', 'advanced', 'intermediate', 'configuration',
            'installation', 'deployment', 'troubleshooting', 'best-practices'
        }
        
        logger.info("TagGenerator initialized")
    
    async def generate_tags(self, content: str, existing_metadata: Dict[str, Any]) -> List[str]:
        """
        Generate tags for content based on analysis.
        
        Args:
            content: Content to analyze for tags
            existing_metadata: Existing content metadata
            
        Returns:
            List of generated tags
            
        Raises:
            TagGenerationError: If tag generation fails
        """
        try:
            logger.debug("Generating tags for content")
            
            tags = set()
            
            # Add technology tags
            tech_tags = await self._extract_technology_tags(content)
            tags.update(tech_tags)
            
            # Add concept tags
            concept_tags = await self._extract_concept_tags(content)
            tags.update(concept_tags)
            
            # Add content type tags
            type_tags = await self._extract_content_type_tags(content)
            tags.update(type_tags)
            
            # Add metadata-based tags
            if existing_metadata.get('technology'):
                tags.add(existing_metadata['technology'].lower())
            
            # Limit number of tags
            final_tags = list(tags)[:10]
            
            logger.debug(f"Generated {len(final_tags)} tags")
            return final_tags
            
        except Exception as e:
            logger.error(f"Tag generation failed: {e}")
            raise TagGenerationError(
                f"Tag generation failed: {str(e)}"
            )
    
    async def _extract_technology_tags(self, content: str) -> Set[str]:
        """
        Extract technology-related tags from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Set of technology tags
        """
        content_lower = content.lower()
        found_tags = set()
        
        for tag in self.technology_tags:
            if tag in content_lower:
                found_tags.add(tag)
        
        return found_tags
    
    async def _extract_concept_tags(self, content: str) -> Set[str]:
        """
        Extract concept-related tags from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Set of concept tags
        """
        content_lower = content.lower()
        found_tags = set()
        
        for tag in self.concept_tags:
            if tag in content_lower or tag.replace('-', ' ') in content_lower:
                found_tags.add(tag)
        
        return found_tags
    
    async def _extract_content_type_tags(self, content: str) -> Set[str]:
        """
        Extract content type tags based on structure.
        
        Args:
            content: Content to analyze
            
        Returns:
            Set of content type tags
        """
        tags = set()
        
        # Check for code examples
        if re.search(r'```\w*\n.*?\n```', content, re.DOTALL):
            tags.add('code-examples')
        
        # Check for API documentation
        if re.search(r'(GET|POST|PUT|DELETE)\s+/', content):
            tags.add('api-reference')
        
        # Check for step-by-step content
        if re.search(r'\d+\.\s+', content) or re.search(r'step\s+\d+', content, re.IGNORECASE):
            tags.add('step-by-step')
        
        # Check for configuration content
        if any(word in content.lower() for word in ['config', 'configuration', 'settings', '.env']):
            tags.add('configuration')
        
        return tags