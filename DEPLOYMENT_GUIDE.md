Setup & Deployment GuideThis guide provides step-by-step instructions to build, configure, and deploy the AI Documentation Cache system on a local machine using Docker.PrerequisitesDocker: Latest version installed and running.Docker Compose: Latest version installed (typically included with Docker Desktop).Git: For cloning the project repository.Operating System: Linux, macOS, or Windows with WSL2.Step 1: Clone the Project RepositoryOpen your terminal and clone the repository to your local machine.git clone <your-repository-url>
cd <repository-directory>
Step 2: Configure the EnvironmentThe system is configured using an .env file in the project root. An example is provided.Copy the example file:cp .env.example .env
Review the Configuration:Open the .env file in a text editor. The default settings are designed to work out-of-the-box with Docker Compose's internal networking.# .env
# Application Settings
DOC_CACHE_APP__DEBUG=False
DOC_CACHE_APP__LOG_LEVEL=INFO

# Service Endpoints (using Docker's internal DNS)
DOC_CACHE_SERVICES__ANYTHINGLLM__ENDPOINT=http://anythingllm:3001
DOC_CACHE_AI__OLLAMA__ENDPOINT=http://ollama:11434

# GitHub API Key (optional but recommended for higher rate limits)
# DOC_CACHE_SERVICES__GITHUB__API_KEY=your_github_personal_access_token
If you have a GitHub Personal Access Token, uncomment the last line and paste your token. This is highly recommended to avoid hitting public rate limits when sourcing documentation.Step 3: Launch the Application StackThis single command will build the custom docs-cache Docker image and start all three required containers (docs-cache, anythingllm, ollama) in the background.docker-compose up --build -d
The first build may take several minutes as it downloads the base images and installs dependencies. Subsequent builds will be much faster.Step 4: Perform One-Time AI Model SetupAfter the containers are running, you need to pull the required AI models into the Ollama service. This only needs to be done once.Pull the Main LLM (Llama 3.1 8B):docker-compose exec ollama ollama pull llama3.1:8b
Pull the Embedding Model (Nomic Embed Text):docker-compose exec ollama ollama pull nomic-embed-text
You can verify the models were installed by running docker-compose exec ollama ollama list.Step 5: Verify System Health and Access UIsYour system is now running. You can access its different parts through your web browser.Admin Web UI: http://localhost:8081This is the main interface for managing the system. Check the Dashboard here to see if all services report a "healthy" status.API Documentation (Swagger): http://localhost:8080/docsAn interactive API documentation page where you can explore and test all API endpoints.AnythingLLM UI: http://localhost:3001The native user interface for the AnythingLLM vector database. You can use this to see the workspaces and content that have been created by the system.Step 6: Perform Initial Content ImportThe system starts with an empty knowledge base. Use the Admin UI or the API to perform a bulk import of the documentation you need.Navigate to the Admin Web UI at http://localhost:8081.Go to the "Content" or "Import" page.Trigger a "Bulk Import" for a technology defined in the database (e.g., react).Alternatively, use curl to call the API endpoint:curl -X POST http://localhost:8080/api/v1/admin/import-technology \
     -H "Content-Type: application/json" \
     -d '{"technology_name": "react"}'
This will run as a background task. You can monitor the application logs to see the progress: docker-compose logs -f docs-cache.Common OperationsStop the application:docker-compose down
View logs:# View all logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f docs-cache
Run a backup:./backup.sh
Your AI Documentation Cache is now fully deployed and ready for use.