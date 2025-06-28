# Docaiche Admin UI: API Endpoint Report

## 1. Introduction

This report documents all the API endpoints consumed by the Docaiche `admin-ui`. The analysis was performed by statically analyzing the codebase, focusing on the implementation of the `DocaicheApiClient` and its usage throughout the `src/features` directory.

All API calls are prefixed with `/api/v1`, as configured in the `DocaicheApiClient`.

## 2. Endpoint Documentation

### 2.1. Overview Page

The overview page (`src/features/overview/`) makes the following API calls to populate its dashboard:

*   **Get Dashboard Stats**
    *   **Method:** `GET`
    *   **Endpoint:** `/stats`
    *   **Client Method:** `apiClient.getDashboardStats()`
    *   **Data Sent:** None
    *   **Usage:** Retrieves the main statistics for the dashboard, including search, content, and system stats.

*   **Get Recent Activity**
    *   **Method:** `GET`
    *   **Endpoint:** `/admin/activity/recent`
    *   **Client Method:** `apiClient.getRecentActivity()`
    *   **Data Sent:** None
    *   **Usage:** Fetches a list of recent system events to display in the activity feed.

*   **Get Collections**
    *   **Method:** `GET`
    *   **Endpoint:** `/collections`
    *   **Client Method:** `apiClient.getCollections()`
    *   **Data Sent:** None
    *   **Usage:** Used by the `pie-graph.tsx` component to display collection statistics.

### 2.2. Health Page

The system health page (`src/features/health/`) monitors the status of the system and its services.

*   **Get System Health**
    *   **Method:** `GET`
    *   **Endpoint:** `/system/health`
    *   **Client Method:** `apiClient.getSystemHealth()`
    *   **Data Sent:** None
    *   **Usage:** Retrieves the health status of all monitored services.

*   **Get System Metrics**
    *   **Method:** `GET`
    *   **Endpoint:** `/system/metrics`
    *   **Client Method:** `apiClient.getSystemMetrics()`
    *   **Data Sent:** None
    *   **Usage:** Fetches system resource utilization metrics (CPU, memory, etc.).

### 2.3. Content Management

The content management section (`src/features/content/`) handles data sources, collections, and content searching.

*   **Get Data Sources / Collections**
    *   **Method:** `GET`
    *   **Endpoint:** `/collections`
    *   **Client Method:** `apiClient.getCollections()` (Note: The client method is `getCollections`, but it's used for "Data Sources" in the UI).
    *   **Data Sent:** None
    *   **Usage:** Retrieves the list of all configured data sources/collections.

*   **Create Collection**
    *   **Method:** `POST`
    *   **Endpoint:** `/content/collections`
    *   **Client Method:** `apiClient.createCollection()`
    *   **Data Sent:** `JSON` object with collection details.
        ```json
        {
          "name": "My Project Docs",
          "type": "github",
          "uri": "https://github.com/user/repo",
          "schedule": "daily"
        }
        ```
    *   **Usage:** Adds a new data source/collection.

*   **Delete Collection**
    *   **Method:** `DELETE`
    *   **Endpoint:** `/content/collections/{collectionId}`
    *   **Client Method:** `apiClient.deleteCollection(collectionId)`
    *   **Data Sent:** None (ID is in the URL path).
    *   **Usage:** Removes a data source/collection.

*   **Re-index Collection**
    *   **Method:** `POST`
    *   **Endpoint:** `/content/collections/{collectionId}/reindex`
    *   **Client Method:** `apiClient.reindexCollection(collectionId)`
    *   **Data Sent:** Empty `JSON` object `{}`.
    *   **Usage:** Triggers a re-indexing job for a specific collection.

*   **Search Content**
    *   **Method:** `GET`
    *   **Endpoint:** `/admin/search-content`
    *   **Client Method:** `apiClient.searchContent()`
    *   **Data Sent:** Query parameters.
        ```
        ?search_term=...&content_type=...&limit=...&offset=...
        ```
    *   **Usage:** Used by the admin search page to find specific content.

*   **Upload Content**
    *   **Method:** `POST`
    *   **Endpoint:** `/upload`
    *   **Client Method:** `apiClient.uploadContent()`
    *   **Data Sent:** `FormData` containing the file and optional metadata.
        ```
        FormData {
          "file": File,
          "collection": "collection_name" (optional)
        }
        ```
    *   **Usage:** Uploads a new document.

### 2.4. AI Configuration

The AI configuration page (`src/features/config/`) manages provider settings.

*   **Get Provider Configurations**
    *   **Method:** `GET`
    *   **Endpoint:** `/providers`
    *   **Client Method:** `apiClient.getProviderConfigurations()`
    *   **Data Sent:** None.
    *   **Usage:** Fetches the list of currently saved provider configurations.

*   **Update Provider Configuration**
    *   **Method:** `POST`
    *   **Endpoint:** `/providers/{providerId}/config`
    *   **Client Method:** `apiClient.updateProviderConfiguration(providerId, config)`
    *   **Data Sent:** `JSON` object with the provider's configuration.
        ```json
        {
          "apiKey": "...",
          "enabled": true,
          // ... other provider-specific fields
        }
        ```
    *   **Usage:** Saves the updated configuration for a specific provider.

*   **Test Provider Connection**
    *   **Method:** `POST`
    *   **Endpoint:** `/providers/{providerId}/test`
    *   **Client Method:** `apiClient.testProviderConnection(providerId, config)`
    *   **Data Sent:** `JSON` object with the provider's configuration needed for the test (e.g., API key).
        ```json
        {
          "apiKey": "..."
        }
        ```
    *   **Usage:** Tests the connection to a provider and is expected to return a list of available models upon success.

### 2.5. Analytics Page

The analytics page (`src/features/analytics/`) provides usage and performance metrics.

*   **Get Analytics Data**
    *   **Method:** `GET`
    *   **Endpoint:** `/analytics`
    *   **Client Method:** `apiClient.getAnalytics()`
    *   **Data Sent:** `timeRange` as a query parameter (e.g., `?timeRange=24h`).
    *   **Usage:** Fetches data for the analytics dashboard.

## 3. Conclusion

This report provides a comprehensive list of the API endpoints used by the Docaiche `admin-ui`. The communication is well-centralized through the `DocaicheApiClient`, and the endpoints align with a standard RESTful architecture. This documentation can serve as a reference for backend development and future frontend modifications.
