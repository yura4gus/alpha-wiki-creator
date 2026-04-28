from tools._models import Page, Edge, LintFinding, LintSeverity


def test_page_round_trips_frontmatter():
    p = Page(slug="auth-api", title="Auth API", path="contracts/rest/auth-api.md",
             frontmatter={"version": "v2.1.0", "status": "stable"},
             body="# Auth API\n", forward_links=["module-auth"])
    assert p.slug == "auth-api"
    assert p.frontmatter["version"] == "v2.1.0"


def test_edge_typed_relation():
    e = Edge(source="modules/auth", target="contracts/rest/auth-api", relation="provides")
    assert e.relation == "provides"


def test_lint_finding_severity():
    f = LintFinding(check="broken-link", severity=LintSeverity.ERROR,
                    file="wiki/modules/m1.md", line=12, message="broken: [[m99]]",
                    fix_available=False)
    assert f.severity == LintSeverity.ERROR
