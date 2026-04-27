from scripts.interview import InterviewConfig, config_from_answers


def test_config_dataclass_round_trip():
    c = InterviewConfig(
        project_name="demo",
        project_description="d",
        wiki_dir="wiki",
        preset="software-project",
        overlay="hexagonal",
        custom_entity_types=None,
        i18n_languages=["en"],
        hooks="all",
        ci=True,
        schema_evolve_mode="gated",
    )
    assert c.preset == "software-project"
    assert c.obsidian is True


def test_config_from_answers_minimal():
    answers = {
        "project_name": "demo",
        "project_description": "d",
        "wiki_dir": "wiki",
        "preset": "software-project",
        "overlay": "none",
        "i18n": "en",
        "hooks": "all",
        "ci": True,
        "schema_evolve_mode": "gated",
    }
    c = config_from_answers(answers)
    assert c.preset == "software-project"
    assert c.overlay == "none"
