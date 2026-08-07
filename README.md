# Multi-Agent AI Research Platform

A production-oriented research assistant API that uses a LangGraph multi-agent workflow, TensorZero LLM routing, Redis job queues, PostgreSQL long-term memory with pgvector, AWS Bedrock Guardrails, LangSmith evaluation, and a PyRIT red-team dashboard.

The platform accepts a research topic, runs it through a search, summarization, writing, and critic loop, stores reusable context, and returns a report as text, JSON, or PDF.

## Features

- Multi-agent research workflow built with LangGraph
- TensorZero gateway for model routing and fallback
- OpenAI primary model with Groq fallback, configured in `tensorzero/tensorzero.toml`
- AWS Bedrock Guardrails for input and output safety checks
- Redis Streams background job queue
- Redis semantic cache for repeated or similar queries
- Redis-backed short-term session memory
- PostgreSQL long-term report memory using pgvector embeddings
- Report diffing against previous related research
- LLM-as-judge evaluation with LangSmith logging
- PyRIT red-team dashboard for jailbreak, XPIA, crescendo, and skeleton-key style tests
- Terraform deployment for AWS ECS Fargate, ALB, RDS, ElastiCache, ECR, Secrets Manager, and scheduled red-team runs

## Repository Layout

```text
.
+-- app/                    # Main FastAPI research API
|   +-- main.py             # API routes, worker loop, lifecycle setup
|   +-- agents.py           # LangGraph multi-agent workflow
|   +-- guardrails.py       # AWS Bedrock Guardrails checks
|   +-- memory.py           # Session memory and pgvector long-term memory
|   +-- cache.py            # Redis semantic cache
|   +-- queue.py            # Redis Streams job queue
|   +-- eval.py             # LangSmith LLM-as-judge evaluation
|   +-- output.py           # PDF, JSON, and diff helpers
+-- pyrit_dashboard/         # FastAPI dashboard for PyRIT-style red-team tests
+-- tensorzero/              # TensorZero gateway config and prompt templates
+-- terraform/               # AWS infrastructure as code
+-- index.html               # Browser UI served by the main API
+-- bootstrap.sh             # Creates Terraform S3 backend and DynamoDB lock table
+-- requirements.txt         # Python dependencies for the main app
```

## Architecture

1. A client submits a topic to `POST /research`.
2. The API validates the topic with AWS Bedrock Guardrails.
3. A Redis Stream job is created and processed asynchronously.
4. The worker checks semantic cache and long-term memory for reusable research.
5. If no match exists, LangGraph runs the research pipeline:
   `SearchAgent -> SummarizeAgent -> WriterAgent -> CriticAgent`.
6. LLM calls are sent through TensorZero, which routes to OpenAI with Groq fallback.
7. The final report is guardrail-checked, cached, stored in PostgreSQL, and evaluated.
8. The client polls `GET /result/{job_id}` until the report is ready.

## Configuration

The app expects a JSON secret named `research-agent/config` in AWS Secrets Manager. Terraform creates this secret automatically.

Important keys:

```json
{
  "OPENAI_API_KEY": "REPLACE_ME",
  "GROQ_API_KEY": "REPLACE_ME",
  "LANGSMITH_API_KEY": "REPLACE_ME",
  "LANGCHAIN_PROJECT": "research-agent",
  "LANGSMITH_DATASET": "research-agent-reports",
  "API_KEY": "",
  "AWS_REGION": "us-east-1",
  "BEDROCK_GUARDRAIL_ID": "...",
  "BEDROCK_GUARDRAIL_VERSION": "...",
  "REDIS_URL": "redis://...",
  "DATABASE_URL": "postgresql://...",
  "TENSORZERO_URL": "http://localhost:3000"
}
```

If `API_KEY` is empty, API-key authentication is disabled. If it is set, clients must send:

```http
X-API-Key: your-api-key
```

Note: `pyrit_dashboard/main.py` currently calls the research API without an API key header. Keep `API_KEY` empty for dashboard testing, or update the dashboard target wrapper to send the header.

## Local Development

This project is designed for AWS-backed configuration, so local runs still need AWS credentials that can read `research-agent/config`.

Prerequisites:

- Python 3.12 for the main API
- Python 3.11 for the PyRIT dashboard image
- Redis
- PostgreSQL with the `vector` extension
- AWS credentials with access to Secrets Manager and Bedrock Runtime
- OpenAI and/or Groq API keys for TensorZero

Install main API dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the main API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The browser UI is served at:

```text
http://localhost:8000
```

Run the PyRIT dashboard separately:

```bash
cd pyrit_dashboard
pip install -r requirements.txt
TARGET_URL=http://localhost:8000 uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## API Usage

Start a research job:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "topic": "AI agents for security operations",
    "output_format": "text"
  }'
```

Poll for the result:

```bash
curl http://localhost:8000/result/JOB_ID \
  -H "X-API-Key: your-api-key"
```

Request JSON output:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "topic": "Post-quantum cryptography adoption",
    "output_format": "json"
  }'
```

Download a PDF:

```bash
curl -L http://localhost:8000/result/JOB_ID/pdf \
  -H "X-API-Key: your-api-key" \
  -o report.pdf
```

Useful endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Serves the web UI |
| `GET` | `/health` | Checks service and Redis health |
| `POST` | `/research` | Starts a research job |
| `GET` | `/result/{job_id}` | Gets job status or completed report |
| `GET` | `/result/{job_id}/pdf` | Downloads a completed report as PDF |
| `GET` | `/session/{session_id}` | Returns recent session messages |
| `GET` | `/diff/{topic}` | Returns a diff against related previous research |
| `GET` | `/stats` | Returns Redis and runtime stats |
| `GET` | `/evaluate/{job_id}` | Runs evaluation for a completed report |
| `POST` | `/run-evaluation` | Starts a background batch evaluation |

PyRIT dashboard endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/status` | Shows target health and attack summary |
| `GET` | `/run-attacks?types=all` | Runs configured attack suites |
| `GET` | `/results` | Returns latest persisted red-team results |

## Docker Images

Build the main API image:

```bash
docker build -f app/Dockerfile -t research-agent-app .
```

Build the PyRIT dashboard image:

```bash
docker build -f pyrit_dashboard/Dockerfile -t research-agent-pyrit .
```

Build the TensorZero gateway image:

```bash
docker build -f tensorzero/Dockerfile -t research-agent-tensorzero .
```

## AWS Deployment

Bootstrap the Terraform backend once:

```bash
./bootstrap.sh us-east-1
```

Initialize and apply Terraform:

```bash
cd terraform
terraform init
terraform apply \
  -var="app_image=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-agent-app:latest" \
  -var="pyrit_image=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-agent-pyrit:latest" \
  -var="tensorzero_image=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-agent-tensorzero:latest"
```

Terraform outputs:

- `alb_dns`: public load balancer hostname for the app
- `app_ecr_url`: ECR repository for the main app image
- `pyrit_ecr_url`: ECR repository for the PyRIT image
- `tensorzero_ecr_url`: ECR repository for the TensorZero image
- `redis_endpoint`: ElastiCache Redis endpoint
- `db_endpoint`: RDS PostgreSQL endpoint

After deployment, replace the placeholder LLM keys in Secrets Manager with real values and restart the ECS tasks.

## Red-Team Testing

The PyRIT dashboard runs prompt attack suites against the research API and stores results in Redis for up to seven days.

Run all attacks:

```bash
curl http://localhost:8001/run-attacks?types=all
```

Run selected attacks:

```bash
curl "http://localhost:8001/run-attacks?types=jailbreak,xpia"
```

Check results:

```bash
curl http://localhost:8001/results
```

In AWS, Terraform also creates an EventBridge schedule for a weekly PyRIT red-team task.

## Operational Notes

- The main API starts a background Redis Stream worker inside the FastAPI process.
- Completed job results are stored in Redis under `result:{job_id}` and expire after `RESULT_TTL`.
- Session history is stored under `session:{session_id}` and trimmed to `SESSION_MAX_MESSAGES`.
- Long-term reports are stored in PostgreSQL in the `reports` table.
- The app automatically creates the `vector` extension and report indexes at startup.
- Semantic cache matching uses `all-MiniLM-L6-v2` embeddings.
- LangSmith logging is best-effort; failures are logged but do not fail user requests.

## Security Notes

- Keep `API_KEY` set for public deployments.
- Replace all `REPLACE_ME` secrets before production use.
- Use HTTPS by setting `acm_certificate_arn` in Terraform.
- The default CORS policy allows all origins. Restrict `allow_origins` in `app/main.py` for production.
- Review IAM permissions, log retention, RDS sizing, and Redis sizing before handling sensitive or high-volume workloads.
