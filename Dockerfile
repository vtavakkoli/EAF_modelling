FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

CMD ["python", "-m", "eaf_model.cli", "simulate", "--output-dir", "/app/results"]
