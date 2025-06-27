# Cross-Reference Guidelines for PRD Documentation

## Overview
This document establishes standardized cross-reference formatting across all PRD files to ensure consistency, maintainability, and improved navigation within the documentation system.

## Standard Format Specifications

### 1. File References
Use: `[ComponentName](PRD-XXX_Filename.md)` for references to entire PRD documents.

**Examples:**
- `[Configuration Management](PRD-003_Config_Mgmt_System.md)`
- `[Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md)`
- `[LLM Provider Integration](PRD-005_LLM_Provider_Integration.md)`

### 2. Specific Line References
Use: `[ComponentName](PRD-XXX_Filename.md:line)` for references to specific lines within a PRD.

**Examples:**
- `[DatabaseManager](PRD-002_DB_and_Caching_Layer.md:244)`
- `[content_metadata](PRD-002_DB_and_Caching_Layer.md:58)`
- `[EvaluationResult](PRD-005_LLM_Provider_Integration.md:266)`

### 3. Method References
Use: `[ComponentName.method()](PRD-XXX_Filename.md:line)` for references to specific methods or functions.

**Examples:**
- `[DatabaseManager.fetch_one()](PRD-002_DB_and_Caching_Layer.md:250)`
- `[ContentProcessor.process_document()](PRD-008_content_processing_pipeline.md:47)`
- `[LLMProviderClient.evaluate_search_results()](PRD-005_LLM_Provider_Integration.md:36)`

## Validation Rules

### 1. Filename Requirements
- All cross-references **must** use the full filename with extension
- Format: `PRD-XXX_Filename.md` (no `PRDs/` directory prefix)
- Filenames must match exactly as they exist in the repository

### 2. Component Name Consistency
- Component names should match exactly as defined in the target PRD
- Use the official component name from the target PRD's title or implementation section
- Maintain consistent capitalization and spacing

### 3. Line Number Accuracy
- Line numbers should be verified during updates
- When referencing specific implementations, ensure line numbers point to the correct location
- Update line numbers when target files are modified

## Cross-Reference Categories

### 1. Dependency References
References to components that the current PRD depends on:
```markdown
## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| [Configuration Management](PRD-003_Config_Mgmt_System.md) | Loads provider config and prompt templates |
| [Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md) | Caches LLM responses |
```

### 2. Cross-Reference Sections
Detailed explanations of how components interact:
```markdown
## Cross-References
- Uses [`AIConfig`](PRD-003_Config_Mgmt_System.md) from [Configuration Management](PRD-003_Config_Mgmt_System.md).
- Calls [`AnythingLLMClient`](PRD-004_AnythingLLM_Integration.md) from [AnythingLLM Integration](PRD-004_AnythingLLM_Integration.md) for search.
- Integrates with [`DatabaseManager`](PRD-002_DB_and_Caching_Layer.md:244) for content persistence.
```

### 3. Implementation References
References to specific implementations, methods, or data structures:
```markdown
- Returns validated [`ProcessedDocument`](PRD-002_DB_and_Caching_Layer.md:156) from database models.
- Uses [`process_and_store_document()`](PRD-008_content_processing_pipeline.md:61) for complete workflow integration.
```

## Line Number Maintenance

### 1. Verification Process
When updating any PRD file:
1. Check all outgoing cross-references for line number accuracy
2. Update line numbers if the referenced content has moved
3. Verify that referenced components still exist at the specified locations

### 2. Documentation of Changes
When modifying PRD files that are referenced by others:
1. Note which files reference the modified content
2. Update line numbers in referencing files
3. Ensure cross-reference accuracy is maintained

### 3. Regular Maintenance
- Perform periodic validation of cross-references
- Use automated tools where possible to verify link accuracy
- Update references during major restructuring or refactoring

## Best Practices

### 1. Descriptive Link Text
Use descriptive text that clearly indicates what is being referenced:
- ✅ `[DatabaseManager](PRD-002_DB_and_Caching_Layer.md:244)`
- ❌ `[here](PRD-002_DB_and_Caching_Layer.md:244)`

### 2. Context-Appropriate References
Choose the right level of specificity:
- For general component discussion: `[Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md)`
- For specific class reference: `[DatabaseManager](PRD-002_DB_and_Caching_Layer.md:244)`
- For method reference: `[DatabaseManager.fetch_one()](PRD-002_DB_and_Caching_Layer.md:250)`

### 3. Consistent Formatting
Maintain consistent formatting throughout all PRD files:
- Use square brackets for link text
- Use parentheses for link targets
- Include line numbers where specific implementations are referenced
- Use descriptive component names rather than generic terms

## Examples of Proper Cross-Reference Formatting

### Dependencies Table
```markdown
## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| [HTTP API Foundation](PRD-001_HTTP_API_Foundation.md) | Exposes search endpoint |
| [Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md) | Caches and retrieves search results |
| [AnythingLLM Integration](PRD-004_AnythingLLM_Integration.md) | Executes vector search |
| [LLM Provider Integration](PRD-005_LLM_Provider_Integration.md) | Evaluates search results |
```

### Cross-References Section
```markdown
## Cross-References
- Uses [`CacheManager`](PRD-002_DB_and_Caching_Layer.md) from [Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md) for caching.
- Calls [`AnythingLLMClient`](PRD-004_AnythingLLM_Integration.md) from [AnythingLLM Integration](PRD-004_AnythingLLM_Integration.md) for search.
- Triggers [`KnowledgeEnricher`](PRD-010_knowledge_enrichment_system.md) from [Knowledge Enrichment System](PRD-010_knowledge_enrichment_system.md) for enrichment.
```

### Implementation Details
```markdown
**Expected Output Schema**: [`EvaluationResult`](PRD-005_LLM_Provider_Integration.md:266)

Templates are loaded by the [`PromptManager`](PRD-005_LLM_Provider_Integration.md:307) utility class.

Complete workflow uses [`process_and_store_document()`](PRD-008_content_processing_pipeline.md:61) method.
```

## Compliance Checklist

When creating or updating PRD cross-references, verify:

- [ ] All file references use the format `[ComponentName](PRD-XXX_Filename.md)`
- [ ] Line-specific references include `:line` number
- [ ] Method references use `ComponentName.method()` format
- [ ] Component names match exactly as defined in target PRDs
- [ ] Line numbers point to correct locations
- [ ] No `PRDs/` directory prefix is used in links
- [ ] Link text is descriptive and meaningful
- [ ] Cross-references are bidirectional where appropriate
- [ ] All referenced files actually exist
- [ ] Line numbers are current and accurate

---

*This document should be reviewed and updated whenever PRD structure or cross-referencing requirements change.*