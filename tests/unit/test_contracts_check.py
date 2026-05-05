from pathlib import Path

from tools.contracts_check import check_contracts, contracts_report


def _write_page(path: Path, frontmatter: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n{body}")


def test_contracts_check_passes_consistent_contract(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "contracts" / "rest" / "auth-api.md",
        "title: Auth API\nslug: auth-api\ntransport: rest\nservice: [[auth-service]]\nconsumers: [[auth-module]]\nversion: v1\nstatus: stable",
        "# Auth API\n",
    )
    _write_page(
        wiki / "modules" / "auth-module.md",
        "title: Auth Module\nslug: auth-module\nstatus: stable\nconsumes: [[auth-api]]",
        "# Auth Module\n",
    )

    assert check_contracts(wiki) == []
    assert "PASS" in contracts_report(wiki)


def test_contracts_check_flags_owner_consumer_and_migration_gaps(tmp_path: Path):
    wiki = tmp_path / "wiki"
    _write_page(
        wiki / "contracts" / "rest" / "billing-api.md",
        "title: Billing API\nslug: billing-api\ntransport: rest\nconsumers: [[billing-module]]\nversion: v2\nstatus: stable",
        "# Billing API\n",
    )
    _write_page(
        wiki / "modules" / "billing-module.md",
        "title: Billing Module\nslug: billing-module\nstatus: stable",
        "# Billing Module\n",
    )

    checks = {finding.check for finding in check_contracts(wiki)}

    assert "contract-missing-service" in checks
    assert "contract-consumer-missing-reverse" in checks
    assert "contract-missing-migration-notes" in checks
