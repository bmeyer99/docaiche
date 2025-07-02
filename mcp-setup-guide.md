# MCP Setup Guide for DocaiChe

The MCP endpoint is now properly configured and working. To use it in Claude Code:

## 1. Connect to the MCP Server

Run this command in Claude Code:
```
/mcp
```

## 2. When prompted, enter:
- Server name: `docaiche` (or keep existing)
- Server type: `http`
- URL: `http://192.168.4.199:4080/api/v1/mcp`

## 3. Available Tools

Once connected, you'll have access to these tools with the `mcp__docaiche__` prefix:

- **mcp__docaiche__docaiche_search** - Search documentation
  - Parameters: query (required), technology, limit, offset
  
- **mcp__docaiche__docaiche_ingest** - Ingest new documentation
  - Parameters: source_url (required), technology
  
- **mcp__docaiche__docaiche_feedback** - Submit feedback
  - Parameters: content_id (required), rating (required), comment

## 4. Testing

After connecting, you can test with:
```
Use the mcp__docaiche__docaiche_search tool to search for "python documentation"
```

## Current Status

✅ MCP endpoint is running at: http://192.168.4.199:4080/api/v1/mcp
✅ Initialize method implemented
✅ Tools/list method returns proper schemas
✅ Tools/call method executes properly
✅ No authentication required

The server is ready for Claude Code to connect!