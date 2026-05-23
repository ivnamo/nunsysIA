from pathlib import Path


def test_phase_0_project_structure_exists() -> None:
    required_paths = [
        "app/api",
        "app/agents",
        "app/tools",
        "app/rag",
        "app/erp",
        "app/production",
        "app/core",
        "app/schemas",
        "production_mock",
        "chainlit_app",
        "data/sample_docs",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "tests/fixtures",
    ]

    missing = [path for path in required_paths if not Path(path).exists()]

    assert missing == []


def test_phase_0_governance_files_exist() -> None:
    required_files = [
        "README.md",
        ".env.example",
        "requirements.txt",
        "requirements-dev.txt",
        "pytest.ini",
        "docs/architecture.md",
        "docs/api.md",
        "docs/validation.md",
        "docs/cleanup-report.md",
    ]

    missing = [path for path in required_files if not Path(path).is_file()]

    assert missing == []
