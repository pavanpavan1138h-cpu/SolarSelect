"""Static validation of container, dependency and CI/CD configuration (runs without Docker)."""
import re
import shutil
import subprocess
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

def pins(path):
    out = {}
    for line in (ROOT / path).read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([\w.]+)", line.strip())
        if m:
            out[m.group(1).lower()] = m.group(2)
    return out

def test_runtime_pins_match_project_requirements():
    main = pins("requirements.txt")
    for name, version in pins("requirements-api.txt").items():
        assert main.get(name.replace("scikit-learn", "scikit-learn")) == version, name
    for name, version in pins("requirements-ci.txt").items():
        assert main.get(name) == version, name

def test_dockerfile_hardening():
    d = (ROOT / "Dockerfile").read_text()
    assert d.startswith("FROM python:3.13") and "USER app" in d and "HEALTHCHECK" in d
    assert "--no-cache-dir" in d and "/api/v1/health/ready" in d
    assert not re.search(r"(?i)(password|token|secret|api_key)\s*=", d)

def test_every_copied_path_exists_in_the_repo():
    for line in (ROOT / "Dockerfile").read_text().splitlines():
        if line.startswith("COPY ") and not line.startswith("COPY --"):
            src = line.split()[1]
            if src.startswith(("models/", "data/")):
                continue                      # DVC-tracked: present after `dvc pull`, not in Git
            assert (ROOT / src).exists(), src

def test_image_excludes_secrets_and_bulk():
    ignore = (ROOT / ".dockerignore").read_text().split()
    for item in (".git", ".venv", "mlflow.db", "tests", "data/raw"):
        assert item in ignore

def test_image_never_installs_training_tooling():
    reqs = (ROOT / "requirements-api.txt").read_text().lower()
    for heavy in ("mlflow", "streamlit", "jupyter", "dvc", "xgboost"):
        assert heavy not in reqs

@pytest.mark.parametrize("wf", ["ci.yml", "cd.yml"])
def test_workflows_are_valid_yaml_with_least_privilege(wf):
    doc = yaml.safe_load((ROOT / ".github/workflows" / wf).read_text())
    assert doc["jobs"] and doc["permissions"]
    assert doc["permissions"].get("contents") == "read"

def test_ci_runs_tests_then_builds_and_smoke_tests_container():
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    assert ci["jobs"]["docker"]["needs"] == "test"
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "pytest" in text and "docker build" in text and "verify_deployed_endpoint.py" in text

def test_cd_is_gated_and_uses_secrets_not_literals():
    text = (ROOT / ".github/workflows/cd.yml").read_text()
    cd = yaml.safe_load(text)
    assert cd["jobs"]["deploy"]["if"] and "DEPLOY_ENABLED" in cd["jobs"]["deploy"]["if"]
    assert cd["jobs"]["deploy"]["environment"] == "production"
    assert "secrets.DEPLOY_SSH_KEY" in text and "BEGIN OPENSSH" not in text

def test_compose_files_parse_and_expose_only_api_port():
    for f in ("docker-compose.yml", "deploy/docker-compose.prod.yml"):
        assert "api" in yaml.safe_load((ROOT / f).read_text())["services"]
    prod = yaml.safe_load((ROOT / "deploy/docker-compose.prod.yml").read_text())["services"]["api"]
    assert prod["read_only"] is True and "MODEL_SOURCE" in prod["environment"]

def test_env_example_has_no_real_secrets_and_env_is_ignored():
    assert "TOKEN" not in (ROOT / ".env.example").read_text().upper().replace("MLFLOW_TRACKING_URI", "")
    assert re.search(r"^\.env$", (ROOT / ".gitignore").read_text(), re.M)

def test_verify_script_runs_against_live_app(tmp_path):
    """Starts the real app in-process-free: uvicorn subprocess, then runs the post-deploy verifier."""
    import socket, sys, time
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.backend.main:app", "--port", str(port)],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts/verify_deployed_endpoint.py"), f"http://127.0.0.1:{port}"],
                           capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "8/8 checks passed" in r.stdout
    finally:
        proc.terminate(); proc.wait(10)

@pytest.mark.skipif(not shutil.which("docker") or subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
                    reason="Docker daemon not available")
def test_docker_image_builds_runs_healthy_and_passes_smoke(tmp_path):
    import sys, time
    tag = "solarselect-api:test"
    subprocess.run(["docker", "build", "-t", tag, str(ROOT)], check=True)
    cid = subprocess.run(["docker", "run", "-d", "-p", "18000:8000", tag], capture_output=True, text=True, check=True).stdout.strip()
    try:
        for _ in range(40):
            h = subprocess.run(["docker", "inspect", "-f", "{{.State.Health.Status}}", cid], capture_output=True, text=True).stdout.strip()
            if h == "healthy":
                break
            time.sleep(3)
        assert h == "healthy"
        assert subprocess.run([sys.executable, str(ROOT / "scripts/verify_deployed_endpoint.py"), "http://127.0.0.1:18000"]).returncode == 0
    finally:
        subprocess.run(["docker", "rm", "-f", cid], capture_output=True)
