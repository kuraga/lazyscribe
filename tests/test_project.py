"""Test the project class."""

import json
import logging
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import time_machine

from lazyscribe import Project
from lazyscribe.exception import ReadOnlyError, SaveError
from lazyscribe.experiment import Experiment, ReadOnlyExperiment
from lazyscribe.test import ReadOnlyTest, Test

CURR_DIR = Path(__file__).resolve().parent
DATA_DIR = CURR_DIR / "data"


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@pytest.mark.parametrize(
    "project_kwargs",
    [
        {
            "fpath": "project.json",
            "mode": "w",
            "author": "root"
        },
        {
            "fpath": "file://" + (DATA_DIR / "external_fs_project.json").as_posix(),
            "mode": "w",
            "author": "root"
        },
    ],
)
def test_logging_experiment(project_kwargs):
    """Test logging an experiment to a project."""
    project = Project(**project_kwargs)
    today = datetime.now()
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    assert "my-experiment" in project
    assert f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}" in project
    assert len(project.experiments) == 1
    assert isinstance(project.experiments[0], Experiment)
    assert project.experiments[0].to_dict() == {
        "name": "My experiment",
        "author": "root",
        "last_updated_by": "root",
        "metrics": {"name": 0.5},
        "parameters": {},
        "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "dependencies": [],
        "short_slug": "my-experiment",
        "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
        "tests": [],
        "tags": [],
    }
    assert project["my-experiment"] == project.experiments[0]
    assert (
        project[f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"]
        == project.experiments[0]
    )
    assert project["my-experiment"].dirty is True
    with pytest.raises(KeyError):
        project["not a real experiment"]


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
@pytest.mark.parametrize(
    "project_kwargs",
    [
        {
            "fpath": "project.json",
            "mode": "w",
            "author": "root"
        },
        {
            "fpath": "file://" + (DATA_DIR / "external_fs_project.json").as_posix(),
            "mode": "w",
            "author": "root"
        },
    ],
)
def test_logging(caplog, project_kwargs):
    """Test logging to a project."""
    project = Project(**project_kwargs)
    today = datetime.now()
    caplog.set_level(logging.WARNING)
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    with project.log(name="My experiment") as exp:
        exp.last_updated = datetime.min
        exp.created_at = today - timedelta(days=1)
        exp.log_metric("name", 1.0)

    assert project["my-experiment"] == project.experiments[-1]
    assert (
        project[f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"]
        == project.experiments[-1]
    )
    assert project["my-experiment"].dirty is True

    assert (
        caplog.text == ""
    )  # If log_metric, then last_updated is overwritten to timestamp at logging hence no warning

    with project.log(name="My experiment") as exp:
        exp.last_updated = datetime.min
        exp.created_at = today - timedelta(days=1)

    assert project["my-experiment"] == project.experiments[-1]
    assert (
        project[f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}"]
        == project.experiments[-1]
    )
    assert project["my-experiment"].dirty is True

    assert (
        f"Returning experiment last saved, with ``last_updated`` manually set as {project.experiments[-1].last_updated}. \
                            The latest ``last_updated`` timestamp is {today}."
        in caplog.text
    )


def test_invalid_project_mode():
    """Test instantiating a project with an invalid mode."""
    with pytest.raises(ValueError):
        _ = Project("project.json", mode="fake-mode", author="root")


def test_not_logging_experiment():
    """Test not logging an experiment when raising an error."""
    project = Project("project.json", mode="w", author="root")
    with pytest.raises(ValueError), project.log(name="My experiment") as exp:
        raise ValueError("An error.")
        exp.log_metric("name", 0.5)

    assert len(project.experiments) == 0


def test_not_logging_experiment_readonly():
    """Test trying to log an experiment in read only mode."""
    project = Project(DATA_DIR / "project.json", mode="r")
    context_manager = project.log(name="New experiment")
    with pytest.raises(ReadOnlyError):
        _ = context_manager.__enter__()

    context_manager.__exit__(None, None, None)

    assert len(project.experiments) == 1
    assert "new-experiment" not in project


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_save_project(tmp_path):
    """Test saving a project to an output JSON."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"
    today = datetime.now()
    project = Project(project_location, mode="w", author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)
        with exp.log_test("My test") as test:
            test.log_metric("name-subpop", 0.3)
            test.log_parameter("features", ["col3", "col4"])

    project.save()

    assert project_location.is_file()
    assert project["my-experiment"].dirty is False

    with open(project_location, "rt") as infile:
        serialized = json.load(infile)

    assert serialized == [
        {
            "name": "My experiment",
            "author": "root",
            "last_updated_by": "root",
            "metrics": {"name": 0.5},
            "parameters": {},
            "created_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "last_updated": today.strftime("%Y-%m-%dT%H:%M:%S"),
            "dependencies": [],
            "short_slug": "my-experiment",
            "slug": f"my-experiment-{today.strftime('%Y%m%d%H%M%S')}",
            "tests": [
                {
                    "name": "My test",
                    "description": None,
                    "metrics": {"name-subpop": 0.3},
                    "parameters": {"features": ["col3", "col4"]},
                }
            ],
            "tags": [],
        }
    ]


def test_save_project_metric_transaction(tmp_path):
    """Test not saving a project due to errors in writing a parameter."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"

    project = Project(project_location, mode="w", author="root")
    with project.log(name="My experiment") as exp:
        exp.log_parameter("data-type", int)

    with pytest.raises(SaveError):
        project.save()

    assert not project_location.is_file()


@time_machine.travel(
    datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
)
def test_update_project_transaction(tmp_path):
    """Test failing to update a project and rolling back the change."""
    location = tmp_path / "my-project"
    project_location = location / "project.json"

    project = Project(project_location, mode="w", author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("metric", 0.5)

    project.save()

    # Re-open the project, compare it to the first version
    project_w = Project(project_location, mode="w+")

    assert project.experiments == project_w.experiments

    # Fail to log
    with project_w.log(name="My second experiment") as exp:
        with project_w.log(name="My experiment") as exp:
            exp.log_metric("should-not-work", int)

    with pytest.raises(SaveError):
        project_w.save()

    # Re-open the project, compare it to the first version
    project_w2 = Project(project_location, mode="w+")

    assert project.experiments == project_w2.experiments


def test_load_project():
    """Test loading a project back into python."""
    project = Project(DATA_DIR / "project.json", mode="w+")

    expected = Experiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0),
        tests=[
            Test(
                name="My test",
                metrics={"name-subpop": 0.3},
                parameters={"param": "value"},
            )
        ],
    )

    assert project.experiments == [expected]


def test_load_project_edit(tmp_path):
    """Test loading a project and editing an experiment."""
    location = tmp_path / "my-location"
    project_location = location / "project.json"
    project = Project(project_location, mode="w", author="root")
    with project.log(name="My experiment") as exp:
        exp.log_metric("name", 0.5)

    project.save()

    # Load the project back
    project = Project(project_location, mode="w+", author="friend")
    exp = project["my-experiment"]

    assert exp.dirty is False

    last_updated = exp.last_updated
    exp.log_metric("name", 0.6)

    assert exp.dirty is True

    project.save()

    assert exp.last_updated > last_updated
    assert exp.last_updated_by == "friend"


def test_load_project_readonly():
    """Test loading a project in read-only or append mode."""
    project = Project(DATA_DIR / "project.json", mode="r")

    expected = ReadOnlyExperiment(
        name="My experiment",
        project=DATA_DIR / "project.json",
        author="root",
        metrics={"name": 0.5},
        created_at=datetime(2022, 1, 1, 9, 30, 0),
        last_updated=datetime(2022, 1, 1, 9, 30, 0),
        tests=[
            ReadOnlyTest(
                name="My test",
                metrics={"name-subpop": 0.3},
                parameters={"param": "value"},
            )
        ],
    )

    assert project.experiments == [expected]
    with pytest.raises(ReadOnlyError):
        project.save()


def test_load_project_dependencies():
    """Test loading a project where an experiment has dependencies."""
    project = Project(DATA_DIR / "down-project.json", mode="a")

    expected = ReadOnlyExperiment(
        name="My downstream experiment",
        project=DATA_DIR / "down-project.json",
        author="root",
        created_at=datetime(2022, 1, 15, 9, 30, 0),
        last_updated=datetime(2022, 1, 15, 9, 30, 0),
        dependencies={
            "my-experiment": ReadOnlyExperiment(
                name="My experiment",
                project=DATA_DIR / "project.json",
                author="root",
                metrics={"name": 0.5},
                created_at=datetime(2022, 1, 1, 9, 30, 0),
                last_updated=datetime(2022, 1, 1, 9, 30, 0),
            )
        },
    )

    assert project.experiments == [expected]


def test_merge_append():
    """Test merging a project with one that has an extra experiment."""
    current = Project(DATA_DIR / "project.json", mode="r")
    newer = Project(DATA_DIR / "merge_append.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "project.json",
            author="root",
            metrics={"name": 0.5},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 1, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_append.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_merge_distinct():
    """Test merging two projects with the no overlapping data."""
    current = Project(DATA_DIR / "project.json", mode="r")
    newer = Project(DATA_DIR / "merge_distinct.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "project.json",
            author="root",
            metrics={"name": 0.5},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 1, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_distinct.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_merge_update():
    """Test merging projects with an updated experiment."""
    current = Project(DATA_DIR / "project.json", mode="r")
    newer = Project(DATA_DIR / "merge_update.json", mode="r")

    new = current.merge(newer)

    assert new.experiments == [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            last_updated_by="friend",
            metrics={"name": 0.5},
            parameters={"features": ["col1", "col2", "col3"]},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 10, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
        ReadOnlyExperiment(
            name="My second experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            parameters={"features": ["col1", "col2"]},
            created_at=datetime(2022, 1, 1, 10, 30, 0),
            last_updated=datetime(2022, 1, 1, 10, 30, 0),
        ),
    ]


def test_filter_project():
    """Test iterating through experiments based on a filter."""
    project = Project(DATA_DIR / "merge_update.json", mode="r")
    out = list(project.filter(func=lambda x: x.last_updated_by == "friend"))

    expected = [
        ReadOnlyExperiment(
            name="My experiment",
            project=DATA_DIR / "merge_update.json",
            author="root",
            last_updated_by="friend",
            metrics={"name": 0.5},
            parameters={"features": ["col1", "col2", "col3"]},
            created_at=datetime(2022, 1, 1, 9, 30, 0),
            last_updated=datetime(2022, 1, 10, 9, 30, 0),
            tests=[
                ReadOnlyTest(
                    name="My test",
                    metrics={"name-subpop": 0.3},
                    parameters={"param": "value"},
                )
            ],
        ),
    ]

    assert out == expected
