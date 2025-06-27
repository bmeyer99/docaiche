System Architecture Document1. System Purpose & VisionThe AI Documentation Cache System is an intelligent, self-improving documentation repository that reduces developer documentation lookup time from over 15 minutes to under 5 seconds. It achieves this by maintaining a locally-cached, AI-curated knowledge base sourced from authoritative repositories and documentation sites, and by learning from user interactions to improve result quality over time.2. High-Level ArchitectureThe system follows a microservices-inspired pattern, containerized via Docker. A central FastAPI application acts as the orchestrator, communicating with specialized services for vector storage (AnythingLLM) and AI decision-making (Ollama).┌─────────────────────────────────────────────────────────────────┐
│                    External Interfaces                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   REST API      │   Admin Web UI  │   GitHub API / Websites     │
│  (Port 8080)    │  (Port 8081)    │      (Content Sources)      │
└─────────────────┴─────────────────┴─────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│             Core Application (docs-cache container)             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Search    │ │   Content   │ │  Knowledge  │ │  Feedback   ││
│  │Orchestrator │ │  Processor  │ │  Enricher   │ │  Collector  ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
                           │ (Clients & Data Access Layer)
         ┌─────────────────┴─────────────────┬─────────────────┐
         ▼                                 ▼                 ▼
┌──────────────────┐             ┌──────────────────┐  ┌─────────────┐
│  AnythingLLM     │             │   Ollama / LLM   │  │   SQLite    │
│ (Vector Storage) │             │ (Decision Engine)│  │ (Metadata)  │
└──────────────────┘             └──────────────────┘  └─────────────┘
3. Component BreakdownThis architecture is composed of distinct, logical components, each specified in its own Product Requirements Document (PRD).HTTP API (PRD-001): The FastAPI server that handles all incoming requests, validation, and routing.Database & Caching (PRD-002): The persistence layer using SQLite for metadata and Redis for high-speed caching.Configuration System (PRD-003): Manages all system settings with a layered loading mechanism (file -> environment -> DB).AnythingLLM Client (PRD-004): A dedicated client for all interactions with the AnythingLLM vector database.LLM Provider Client (PRD-005): A unified client for interacting with AI models (primarily Ollama), responsible for structured prompting and response parsing.GitHub Client (PRD-006): A client for sourcing documentation directly from GitHub repositories.Web Scraping Client (PRD-007): A client for sourcing documentation from websites when a repository is not available.Content Processor (PRD-008): A pipeline that cleans, standardizes, and chunks raw content into a format ready for ingestion.Search Orchestrator (PRD-009): The core "brain" that manages the entire search workflow.Knowledge Enricher (PRD-010): The system that acts on AI-driven strategies to acquire new content.Feedback Collector (PRD-011): The system that gathers user feedback to improve content quality scores.Admin Web UI (PRD-012): A simple interface for monitoring and managing the system.Operations (PRD-013): Defines the Docker packaging and deployment procedures.4. Data Flow DiagramsSearch Workflow1. User Query -> API (PRD-001)
2. API -> Search Orchestrator (PRD-009)
3. Orchestrator -> Cache Check (Redis via PRD-002)
   (if miss)
4. Orchestrator -> AnythingLLM Client (PRD-004) -> Search
5. Orchestrator -> LLM Client (PRD-005) -> Evaluate Results
6. Orchestrator -> Decides to enrich
   (if yes) -> Background Task -> Knowledge Enricher (PRD-010)
7. Orchestrator -> Compiles & Caches Response -> Returns to API
Enrichment Workflow (Background)1. Knowledge Enricher receives AI Strategy
2. Enricher -> GitHub Client (PRD-006) OR Web Scraper (PRD-007)
3. Raw Content -> Content Processor (PRD-008)
4. Processed Chunks -> AnythingLLM Client (PRD-004) -> Upload
5. Document Metadata -> DB Layer (PRD-002) -> Insert into content_metadata
5. Deployment ModelThe entire system is designed for simplicity and portability using Docker Compose.docs-cache service: The main Python application, containing all components from PRD-001 to PRD-012.anythingllm service: A standard container for the vector database.ollama service: A standard container for running local LLMs.Volumes: Named Docker volumes are used for persistent storage of the SQLite database, AnythingLLM vectors, and Ollama models.This architecture ensures clear separation of concerns, allows for independent component development, and results in a self-contained, easy-to-deploy system.