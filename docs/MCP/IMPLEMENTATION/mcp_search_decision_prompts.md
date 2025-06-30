# MCP Search Decision Prompts for Text AI

This document outlines the key decision points in the search workflow where the configured Text AI model is used and provides prompt templates for each scenario.

## 1. Query Understanding

**Decision Point:** When a search query is first received, determine the intent, domain, and search strategy.

**Prompt Template:**
```
Analyze the following query to determine search parameters:

Query: "{query}"

Please identify:
1. Primary intent (information seeking, problem solving, how-to, etc.)
2. Technical domain (if applicable)
3. Expected answer type (explanation, code example, reference, etc.)
4. Key entities or concepts
5. Scope of search (specific technology, general knowledge, etc.)
6. Suggested workspaces to search in AnythingLLM

Return your analysis in JSON format.
```

## 2. Result Relevance Evaluation

**Decision Point:** After retrieving results from AnythingLLM, determine if they're relevant to the query.

**Prompt Template:**
```
Evaluate the relevance of these search results for the query:

Query: "{query}"

Search Results:
{results_json}

Please assess:
1. Overall relevance score (0-1)
2. Whether results directly answer the query (yes/no)
3. Whether results contain all necessary information (yes/no)
4. Missing information (if any)
5. Whether a refined search is needed (yes/no)
6. Suggested query refinement (if needed)

Return your evaluation in JSON format.
```

## 3. Query Refinement

**Decision Point:** When initial results are insufficient, generate a refined query.

**Prompt Template:**
```
The following query did not yield sufficiently relevant results:

Original Query: "{original_query}"
Search Results: {results_summary}
Missing Information: {missing_info}

Please generate a refined search query that:
1. Is more specific and targeted
2. Includes key technical terms
3. Focuses on the missing information
4. Is optimized for vector similarity search

Return only the refined query text.
```

## 4. External Search Decision

**Decision Point:** Decide whether to use external search when AnythingLLM results are insufficient.

**Prompt Template:**
```
Determine if external search is needed based on:

Original Query: "{original_query}"
AnythingLLM Results: {results_summary}
Relevance Score: {relevance_score}
Missing Information: {missing_info}

Consider:
1. Is this a technical topic likely found in documentation? (yes/no)
2. Is the query about recent technologies or updates? (yes/no)
3. Could the information exist in public repositories? (yes/no)
4. Is the answer likely to be found through web search? (yes/no)
5. Would external search provide significantly better results? (yes/no)

Return your decision (true/false) and reasoning in JSON format.
```

## 5. External Search Query Generation

**Decision Point:** When external search is needed, generate an effective search query.

**Prompt Template:**
```
Generate an optimal external search query based on:

Original Query: "{original_query}"
Failed AnythingLLM Results: {results_summary}
Missing Information: {missing_info}

Please create a search query that:
1. Is formatted for web search engines
2. Contains specific technical terms
3. Uses quotes for exact phrases if appropriate
4. Includes version numbers or specific technologies
5. Is focused on documentation sources
6. Prioritizes GitHub or official documentation

Return only the search query text optimized for {search_provider}.
```

## 6. Content Extraction

**Decision Point:** After retrieving documentation from external sources, extract relevant content.

**Prompt Template:**
```
Extract the most relevant content from this documentation:

User Query: "{original_query}"
Source URL: {url}
Content Type: {content_type}

Document Content:
{raw_content}

Please:
1. Extract only sections directly relevant to the query
2. Preserve code examples if present
3. Maintain formatting for technical instructions
4. Include necessary context (e.g., prerequisites)
5. Remove irrelevant sections, navigation, etc.
6. Keep reference links intact

Return the extracted content in Markdown format.
```

## 7. Response Format Selection

**Decision Point:** Based on user preference and query type, determine how to format the response.

**Prompt Template:**
```
Format the search results based on user preferences:

Query: "{query}"
Response Type: "{response_type}" (raw/answer)
Search Results: {results_json}

If response_type is "raw":
- Provide the most relevant documentation sections
- Preserve formatting, especially for code
- Include source attribution

If response_type is "answer":
- Synthesize information into a direct answer
- Include code examples if applicable
- Cite sources
- Ensure completeness

Return the formatted response in Markdown.
```

## 8. Learning Opportunity Identification

**Decision Point:** Identify if the search reveals knowledge gaps that should be filled in AnythingLLM.

**Prompt Template:**
```
Analyze this search interaction to identify knowledge gaps:

Query: "{query}"
Initial AnythingLLM Results: {initial_results}
External Search Results: {external_results}
Final Response: {final_response}

Please identify:
1. Knowledge gaps in our AnythingLLM database
2. Topics that should be added to our knowledge base
3. Priority level for ingestion (high/medium/low)
4. Suggested source documentation
5. Workspace categorization

Return your analysis in JSON format for knowledge base improvement.
```

## 9. Search Provider Selection

**Decision Point:** When multiple search providers are configured, select the most appropriate one.

**Prompt Template:**
```
Select the optimal search provider for this query:

Query: "{query}"
Available Providers: {providers_json}
Query Domain: {domain}
Previous Provider Performance: {performance_stats}

Please analyze:
1. Query type and complexity
2. Technical domain specificity
3. Provider strengths for this domain
4. Recent provider performance
5. Rate limit considerations

Return the selected provider ID and reasoning in JSON format.
```

## 10. Search Failure Analysis

**Decision Point:** When all search methods fail, analyze why to improve future searches.

**Prompt Template:**
```
Analyze this failed search to improve future performance:

Original Query: "{query}"
AnythingLLM Results: {vector_results}
External Search Attempts: {external_attempts}
Error Messages: {errors}

Please identify:
1. Likely reasons for search failure
2. Whether query was malformed or ambiguous
3. Missing knowledge domains in our system
4. Technical limitations encountered
5. Recommended system improvements
6. Alternative approaches for similar queries

Return your analysis in JSON format.
```

## Implementation Notes

1. **Prompt Variables**: Replace values in curly braces `{variable}` with actual data
2. **Response Formats**: Specify JSON output when structured data is needed
3. **Context Length**: Ensure prompts with included content don't exceed model context limits
4. **Error Handling**: Include fallback logic when model responses don't match expected format
5. **Temperature Setting**: Use lower temperature (0.1-0.3) for analytical decisions, higher (0.7) for content generation
6. **Logging**: Log both prompts and responses for audit and improvement
7. **Performance**: Monitor token usage and response times to optimize prompts