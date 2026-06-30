FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -e .

RUN python -m playwright install chromium

ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8200

EXPOSE 8200

CMD ["xvfb-run", "-a", "reddit-mcp"]
