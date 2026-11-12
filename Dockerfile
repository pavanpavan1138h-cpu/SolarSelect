FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MODEL_SOURCE=local
WORKDIR /srv/solarselect
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY app/__init__.py app/__init__.py
COPY app/backend app/backend
COPY src src
COPY monitoring monitoring
COPY configs configs
COPY models/phase5/final_model_metadata.json models/phase5/final_model_metadata.json
COPY models/phase5/final/peer_cohort models/phase5/final/peer_cohort
COPY data/processed/unisolar/feature_dictionary.csv data/processed/unisolar/feature_dictionary.csv
COPY data/processed/unisolar/peer_cohort/test.csv data/processed/unisolar/peer_cohort/test.csv
RUN useradd --system --no-create-home app && chown -R app /srv/solarselect
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready').status==200 else 1)"
CMD ["python", "-m", "uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
