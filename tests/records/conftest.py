from copy import deepcopy
from pathlib import Path

import pytest

from record_engineering.contracts import strict_json
from record_engineering.fixtures import generate
from record_engineering.replay import replay
from record_engineering.thresholds import evaluate, fit_policy

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def base():
    bundle, expectations = generate()
    contract = strict_json((ROOT / "contracts/public_decision_policy.json").read_text())
    frozen = fit_policy(bundle, contract)
    snapshot = replay(bundle, contract["default_as_of"])
    return (
        bundle,
        contract,
        frozen,
        snapshot,
        evaluate(bundle, snapshot, frozen),
        expectations,
    )


@pytest.fixture
def bundle(base):
    return deepcopy(base[0])


@pytest.fixture
def contract(base):
    return deepcopy(base[1])
