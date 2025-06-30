/**
 * MCP JavaScript/TypeScript Integration Example
 * =============================================
 * 
 * This example shows how to integrate the DocaiChe MCP server
 * with a JavaScript/TypeScript application.
 */

// For Node.js environments
const fetch = require('node-fetch');

// For TypeScript, use:
// import fetch from 'node-fetch';

class MCPClient {
    constructor(config) {
        this.endpoint = config.endpoint.replace(/\/$/, '');
        this.clientId = config.clientId;
        this.clientSecret = config.clientSecret;
        this.accessToken = null;
        this.tokenExpires = null;
    }

    /**
     * Authenticate with the MCP server
     */
    async authenticate() {
        // Check if we have a valid token
        if (this.accessToken && this.tokenExpires && new Date() < this.tokenExpires) {
            return this.accessToken;
        }

        const params = new URLSearchParams({
            grant_type: 'client_credentials',
            client_id: this.clientId,
            client_secret: this.clientSecret,
            resource: 'urn:docaiche:api:v1',
            scope: 'search:read ingest:write collections:read feedback:write status:read'
        });

        const response = await fetch(`${this.endpoint}/oauth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params
        });

        if (!response.ok) {
            throw new Error(`Authentication failed: ${await response.text()}`);
        }

        const tokenData = await response.json();
        this.accessToken = tokenData.access_token;
        this.tokenExpires = new Date(Date.now() + (tokenData.expires_in - 60) * 1000);

        return this.accessToken;
    }

    /**
     * Call an MCP tool
     */
    async callTool(toolName, args) {
        const token = await this.authenticate();

        const response = await fetch(`${this.endpoint}/mcp/tools/call`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                id: `tool-${Date.now()}`,
                method: 'tools/call',
                params: {
                    name: toolName,
                    arguments: args
                }
            })
        });

        if (!response.ok) {
            throw new Error(`Tool call failed: ${await response.text()}`);
        }

        const result = await response.json();
        if (result.error) {
            throw new Error(`Tool error: ${JSON.stringify(result.error)}`);
        }

        return result.result;
    }

    /**
     * Read an MCP resource
     */
    async readResource(uri, params = {}) {
        const token = await this.authenticate();

        const response = await fetch(`${this.endpoint}/mcp/resources/read`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                id: `resource-${Date.now()}`,
                method: 'resources/read',
                params: {
                    uri: uri,
                    ...params
                }
            })
        });

        if (!response.ok) {
            throw new Error(`Resource read failed: ${await response.text()}`);
        }

        const result = await response.json();
        if (result.error) {
            throw new Error(`Resource error: ${JSON.stringify(result.error)}`);
        }

        return result.result;
    }
}

/**
 * Example: Search Component for React
 */
const SearchDocumentation = () => {
    const [query, setQuery] = React.useState('');
    const [results, setResults] = React.useState([]);
    const [loading, setLoading] = React.useState(false);

    const client = React.useMemo(() => new MCPClient({
        endpoint: process.env.REACT_APP_MCP_ENDPOINT || 'http://localhost:8000',
        clientId: process.env.REACT_APP_MCP_CLIENT_ID,
        clientSecret: process.env.REACT_APP_MCP_CLIENT_SECRET
    }), []);

    const handleSearch = async () => {
        if (!query.trim()) return;

        setLoading(true);
        try {
            const searchResults = await client.callTool('docaiche/search', {
                query: query,
                max_results: 10,
                include_metadata: true
            });

            setResults(searchResults.results);
        } catch (error) {
            console.error('Search failed:', error);
            alert('Search failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="search-container">
            <h2>Documentation Search</h2>
            
            <div className="search-box">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="Search documentation..."
                />
                <button onClick={handleSearch} disabled={loading}>
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </div>

            <div className="results">
                {results.map((result, index) => (
                    <div key={index} className="result-item">
                        <h3>{result.title}</h3>
                        <p className="snippet">{result.snippet}</p>
                        <div className="metadata">
                            <span>Score: {result.score.toFixed(2)}</span>
                            <span>Collection: {result.collection}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

/**
 * Example: Vue.js Integration
 */
const DocaiCheSearch = {
    data() {
        return {
            query: '',
            results: [],
            loading: false,
            client: null
        };
    },
    
    mounted() {
        this.client = new MCPClient({
            endpoint: process.env.VUE_APP_MCP_ENDPOINT || 'http://localhost:8000',
            clientId: process.env.VUE_APP_MCP_CLIENT_ID,
            clientSecret: process.env.VUE_APP_MCP_CLIENT_SECRET
        });
    },
    
    methods: {
        async search() {
            if (!this.query.trim()) return;
            
            this.loading = true;
            try {
                const searchResults = await this.client.callTool('docaiche/search', {
                    query: this.query,
                    max_results: 10
                });
                
                this.results = searchResults.results;
            } catch (error) {
                console.error('Search failed:', error);
                this.$toast.error('Search failed: ' + error.message);
            } finally {
                this.loading = false;
            }
        }
    },
    
    template: `
        <div class="docaiche-search">
            <h2>Search Documentation</h2>
            <input 
                v-model="query" 
                @keyup.enter="search"
                placeholder="Enter search query..."
            />
            <button @click="search" :disabled="loading">
                {{ loading ? 'Searching...' : 'Search' }}
            </button>
            
            <div v-for="result in results" :key="result.uri" class="result">
                <h3>{{ result.title }}</h3>
                <p>{{ result.snippet }}</p>
            </div>
        </div>
    `
};

/**
 * Example: Node.js CLI Tool
 */
async function cliExample() {
    const client = new MCPClient({
        endpoint: process.env.MCP_ENDPOINT || 'http://localhost:8000',
        clientId: process.env.MCP_CLIENT_ID || 'cli_client',
        clientSecret: process.env.MCP_CLIENT_SECRET || 'cli_secret'
    });

    // Parse command line arguments
    const args = process.argv.slice(2);
    const command = args[0];

    try {
        switch (command) {
            case 'search':
                const query = args.slice(1).join(' ');
                const results = await client.callTool('docaiche/search', {
                    query: query,
                    max_results: 5
                });
                
                console.log(`Found ${results.total_count} results:\n`);
                results.results.forEach((result, i) => {
                    console.log(`${i + 1}. ${result.title}`);
                    console.log(`   ${result.snippet}\n`);
                });
                break;

            case 'status':
                const status = await client.readResource('docaiche://status');
                console.log('System Status:', status.status);
                console.log('Version:', status.version);
                console.log('Components:');
                Object.entries(status.components).forEach(([name, info]) => {
                    console.log(`  - ${name}: ${info.status}`);
                });
                break;

            case 'collections':
                const collections = await client.readResource('docaiche://collections');
                console.log('Available Collections:\n');
                collections.collections.forEach(col => {
                    console.log(`- ${col.display_name} (${col.document_count} docs)`);
                    console.log(`  ${col.description}\n`);
                });
                break;

            default:
                console.log('Usage: node mcp-cli.js [search|status|collections] [args...]');
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

/**
 * Example: TypeScript with Type Definitions
 */

// types.d.ts
interface MCPConfig {
    endpoint: string;
    clientId: string;
    clientSecret: string;
}

interface SearchResult {
    uri: string;
    title: string;
    snippet: string;
    score: number;
    collection: string;
    metadata?: {
        author?: string;
        date_modified?: string;
        tags?: string[];
    };
}

interface SearchResponse {
    results: SearchResult[];
    total_count: number;
    query_time_ms: number;
}

interface MCPError {
    code: string;
    message: string;
    details?: any;
    request_id: string;
}

// TypeScript implementation
class TypedMCPClient {
    private endpoint: string;
    private clientId: string;
    private clientSecret: string;
    private accessToken: string | null = null;
    private tokenExpires: Date | null = null;

    constructor(config: MCPConfig) {
        this.endpoint = config.endpoint.replace(/\/$/, '');
        this.clientId = config.clientId;
        this.clientSecret = config.clientSecret;
    }

    async search(query: string, options?: {
        collection?: string;
        max_results?: number;
        include_metadata?: boolean;
    }): Promise<SearchResponse> {
        return this.callTool('docaiche/search', {
            query,
            ...options
        });
    }

    async ingest(document: {
        uri: string;
        content: string;
        metadata: {
            title: string;
            author?: string;
            tags?: string[];
            collection: string;
        };
        consent: {
            user_confirmed: boolean;
            purpose: string;
        };
    }): Promise<{
        status: 'success' | 'failed';
        document_id: string;
        validation_results: {
            content_valid: boolean;
            metadata_valid: boolean;
            consent_valid: boolean;
        };
        indexing_time_ms: number;
    }> {
        return this.callTool('docaiche/ingest', document);
    }

    private async callTool<T>(toolName: string, args: any): Promise<T> {
        // Implementation same as JavaScript version
        // but with TypeScript types
        throw new Error('Implementation needed');
    }
}

// If running as Node.js script
if (require.main === module) {
    cliExample().catch(console.error);
}

module.exports = { MCPClient, TypedMCPClient };