from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

SIGNALS = ("mismatch", "provenance_gap", "source_conflict")
TARGETS = ("record_present", "verification_recorded", "correction_recorded")
OUTCOMES = ("SUPPORTED", "CONTRADICTED", "INCONCLUSIVE")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)


def exact(obj, fields, name):
    if not isinstance(obj, dict) or set(obj) != set(fields):
        raise ValueError(f"{name}: exact fields required: {sorted(fields)}")


def text_id(value, name, *, blank=False):
    if (
        not isinstance(value, str)
        or value != value.strip()
        or (not value and not blank)
    ):
        raise ValueError(f"{name}: nonblank unpadded string required")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{name}: control characters prohibited")


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name}: integer in [{low}, {high}] required")


def instant(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError("whole-second timestamp with explicit offset required")
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError("invalid timestamp offset")
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid timestamp") from exc


def evidence_hash(event):
    material = f"{event['record_id']}:{event['version']}:{canonical(event['payload'])}"
    return hashlib.sha256(material.encode()).hexdigest()


def validate_bundle(bundle: dict) -> dict:
    exact(
        bundle,
        ("schema_version", "synthetic", "actors", "records", "events", "labels"),
        "bundle",
    )
    if bundle["schema_version"] != "1.0" or bundle["synthetic"] is not True:
        raise ValueError("only schema 1.0 synthetic bundles supported")
    actors, records, ids, sequences, labels = {}, {}, {}, {}, set()
    for key in ("actors", "records", "events", "labels"):
        if not isinstance(bundle[key], list):
            raise ValueError(f"{key} must be a list")
    for row in bundle["actors"]:
        exact(row, ("actor_id", "roles", "synthetic"), "actor")
        text_id(row["actor_id"], "actor_id")
        roles = row["roles"]
        if (
            row["actor_id"] in actors
            or row["synthetic"] is not True
            or not isinstance(roles, list)
            or not roles
            or len(roles) != len(set(roles))
            or not set(roles) <= {"SUBMITTER", "VERIFIER", "OFFICER", "REPORTER"}
        ):
            raise ValueError("duplicate actor or invalid role contract")
        actors[row["actor_id"]] = set(roles)
    for row in bundle["records"]:
        exact(
            row,
            (
                "record_id",
                "submitter_id",
                "cohort",
                "split",
                "observed_at",
                "synthetic",
            ),
            "record",
        )
        text_id(row["record_id"], "record_id")
        if (
            row["record_id"] in records
            or row["synthetic"] is not True
            or row["cohort"] not in ("COHORT_A", "COHORT_B")
            or row["split"] not in ("CALIBRATION", "HOLDOUT", "OPERATIONS")
            or "SUBMITTER" not in actors.get(row["submitter_id"], set())
        ):
            raise ValueError("invalid record catalog")
        if instant(row["observed_at"]) != row["observed_at"]:
            raise ValueError("bundle timestamps must use canonical UTC")
        records[row["record_id"]] = row
    if not records or not actors:
        raise ValueError("empty record or actor catalog")
    for e in bundle["events"]:
        exact(
            e,
            (
                "event_id",
                "seq",
                "recorded_at",
                "record_id",
                "kind",
                "version",
                "actor_id",
                "payload",
                "synthetic",
            ),
            "event",
        )
        text_id(e["event_id"], "event_id")
        integer(e["seq"], 1, 2**31 - 1, "seq")
        integer(e["version"], 1, 2**31 - 1, "version")
        if (
            e["record_id"] not in records
            or e["actor_id"] not in actors
            or e["synthetic"] is not True
        ):
            raise ValueError("event has unknown record/actor or nonsynthetic flag")
        if (
            instant(e["recorded_at"]) != e["recorded_at"]
            or e["recorded_at"] < records[e["record_id"]]["observed_at"]
        ):
            raise ValueError("event chronology violates catalog")
        p = e["payload"]
        if e["kind"] == "EVIDENCE":
            exact(p, (*SIGNALS, "statement_id"), "evidence payload")
            text_id(p["statement_id"], "statement_id")
            for signal in SIGNALS:
                if p[signal] is not None:
                    integer(p[signal], 0, 100, signal)
        elif e["kind"] in ("WITHDRAW", "VERIFY", "CORRECT", "CLAIM"):
            fields = ["evidence_hash"]
            if e["kind"] == "VERIFY":
                fields += ["outcome", "expires_at"]
            elif e["kind"] == "CORRECT":
                fields += ["verification_event_id"]
            elif e["kind"] == "CLAIM":
                fields += ["target", "verification_event_id", "correction_event_id"]
            exact(p, fields, "action payload")
            if not isinstance(p["evidence_hash"], str) or not re.fullmatch(
                r"[a-f0-9]{64}", p["evidence_hash"]
            ):
                raise ValueError("canonical SHA256 evidence witness required")
            if e["kind"] == "VERIFY":
                if (
                    p["outcome"] not in OUTCOMES
                    or instant(p["expires_at"]) != p["expires_at"]
                ):
                    raise ValueError("invalid verification outcome/expiry")
            if e["kind"] in ("CORRECT", "CLAIM"):
                text_id(
                    p["verification_event_id"],
                    "verification_event_id",
                    blank=e["kind"] == "CLAIM",
                )
            if e["kind"] == "CLAIM":
                text_id(p["target"], "target")
                text_id(p["correction_event_id"], "correction_event_id", blank=True)
        else:
            raise ValueError("unknown event kind")
        if e["event_id"] in ids and ids[e["event_id"]] != canonical(e):
            raise ValueError("conflicting duplicate event_id")
        if e["seq"] in sequences and sequences[e["seq"]] != e["event_id"]:
            raise ValueError("delivery sequence collision")
        ids[e["event_id"]] = canonical(e)
        sequences[e["seq"]] = e["event_id"]
    unique = sorted(
        {e["event_id"]: e for e in bundle["events"]}.values(), key=lambda e: e["seq"]
    )
    if any(a["recorded_at"] > b["recorded_at"] for a, b in zip(unique, unique[1:])):
        raise ValueError("sequence must agree with nondecreasing arrival time")
    for row in bundle["labels"]:
        exact(row, ("record_id", "needs_review", "recorded_at", "synthetic"), "label")
        if (
            row["record_id"] not in records
            or row["record_id"] in labels
            or type(row["needs_review"]) is not bool
            or row["synthetic"] is not True
            or instant(row["recorded_at"]) != row["recorded_at"]
            or row["recorded_at"] < records[row["record_id"]]["observed_at"]
        ):
            raise ValueError("invalid/duplicate synthetic label")
        labels.add(row["record_id"])
    return bundle
