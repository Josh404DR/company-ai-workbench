from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 6


class SQLiteStore:
    """Small persistence adapter with explicit migrations and append-only events."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                connection.execute("PRAGMA journal_mode = WAL")
            except sqlite3.OperationalError as error:
                if "database is locked" not in str(error).lower():
                    raise
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """
            )
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            if 1 not in applied:
                self._apply_v1(connection)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (1, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            if 2 not in applied:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(acceptances)")}
                if "verification_id" not in columns:
                    connection.execute("ALTER TABLE acceptances ADD COLUMN verification_id TEXT REFERENCES verifications(id)")
                self._backfill_acceptance_verifications(connection)
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (2, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            if 3 not in applied:
                self._backfill_acceptance_verifications(connection)
                connection.executescript(
                    """
                    CREATE TRIGGER IF NOT EXISTS verifications_no_update BEFORE UPDATE ON verifications
                    BEGIN SELECT RAISE(ABORT, 'verifications are append-only'); END;
                    CREATE TRIGGER IF NOT EXISTS verifications_no_delete BEFORE DELETE ON verifications
                    BEGIN SELECT RAISE(ABORT, 'verifications are append-only'); END;
                    CREATE TRIGGER IF NOT EXISTS acceptances_no_update BEFORE UPDATE ON acceptances
                    BEGIN SELECT RAISE(ABORT, 'acceptances are append-only'); END;
                    CREATE TRIGGER IF NOT EXISTS acceptances_no_delete BEFORE DELETE ON acceptances
                    BEGIN SELECT RAISE(ABORT, 'acceptances are append-only'); END;
                    """
                )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (3, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            if 4 not in applied:
                self._apply_v4(connection)
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (4, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            if 5 not in applied:
                self._apply_v5(connection)
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (5, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            if 6 not in applied:
                self._apply_v6(connection)
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (6, strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
                )
            connection.commit()

    @staticmethod
    def _apply_v6(connection: sqlite3.Connection) -> None:
        """Long tasks (goals) and ticket dependency hierarchy."""
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('planned','in_progress','achieved','blocked','cancelled')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        ticket_columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
        if ticket_columns and "goal_id" not in ticket_columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN goal_id TEXT REFERENCES goals(id)")
        if ticket_columns and "depends_on_ticket_id" not in ticket_columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN depends_on_ticket_id TEXT REFERENCES tickets(id)")

    @staticmethod
    def _apply_v5(connection: sqlite3.Connection) -> None:
        """Governance hardening: risk tiers, verifier independence, content-addressed evidence,
        run usage/cost, and memory expiry. Every addition is nullable or defaulted so v1-v4 rows
        survive unchanged; the only rebuild is memory_candidates, which needs a wider status CHECK.

        Defaults fail closed: legacy tickets become risk_level='high' (Josh-only acceptance), legacy
        verifications keep NULL verifier_provider/evidence_sha256 and therefore can no longer back a
        NEW acceptance, and legacy approved memories keep NULL expires_at (never expire) but carry no
        approved_at, which the active-context report surfaces as "unknown age".
        """
        ticket_columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
        if ticket_columns and "risk_level" not in ticket_columns:
            connection.execute(
                "ALTER TABLE tickets ADD COLUMN risk_level TEXT NOT NULL DEFAULT 'high' "
                "CHECK(risk_level IN ('low','medium','high'))"
            )
        run_columns = {row[1] for row in connection.execute("PRAGMA table_info(runs)")}
        for name, decl in (
            ("input_tokens", "INTEGER"), ("output_tokens", "INTEGER"),
            ("cost_usd", "REAL"), ("provider_account", "TEXT"),
        ):
            if run_columns and name not in run_columns:
                connection.execute(f"ALTER TABLE runs ADD COLUMN {name} {decl}")
        verification_columns = {row[1] for row in connection.execute("PRAGMA table_info(verifications)")}
        for name in ("verifier_provider", "evidence_sha256"):
            if verification_columns and name not in verification_columns:
                connection.execute(f"ALTER TABLE verifications ADD COLUMN {name} TEXT")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence_artifacts (
                sha256 TEXT PRIMARY KEY,
                content BLOB NOT NULL,
                byte_size INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS evidence_artifacts_no_update BEFORE UPDATE ON evidence_artifacts
            BEGIN SELECT RAISE(ABORT, 'evidence artifacts are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS evidence_artifacts_no_delete BEFORE DELETE ON evidence_artifacts
            BEGIN SELECT RAISE(ABORT, 'evidence artifacts are append-only'); END;
            """
        )
        memory_columns = {row[1] for row in connection.execute("PRAGMA table_info(memory_candidates)")}
        if memory_columns and "expires_at" not in memory_columns:
            connection.executescript(
                """
                CREATE TABLE memory_candidates_v5 (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    source_run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL CHECK(kind IN ('episodic','semantic','procedural','preference','project')),
                    statement TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','disabled','expired')),
                    created_at TEXT NOT NULL,
                    approved_at TEXT,
                    expires_at TEXT,
                    source_commit TEXT,
                    reviewed_by TEXT
                );
                INSERT INTO memory_candidates_v5
                    (id,project_id,source_run_id,kind,statement,scope,evidence_ref,status,created_at)
                SELECT id,project_id,source_run_id,kind,statement,scope,evidence_ref,status,created_at
                FROM memory_candidates;
                DROP TABLE memory_candidates;
                ALTER TABLE memory_candidates_v5 RENAME TO memory_candidates;
                """
            )

    @staticmethod
    def _apply_v4(connection: sqlite3.Connection) -> None:
        """Add process invocation identity to runs. Additive/nullable so legacy v1-v3 rows are unaffected.

        The UNIQUE index (not a plain column constraint) lets ALTER TABLE ADD COLUMN stay a cheap
        metadata-only change while still failing closed: if a corrupted database already contains
        colliding non-null invocation_id values, index creation raises and version 4 is never recorded.
        """
        columns = {row[1] for row in connection.execute("PRAGMA table_info(runs)")}
        if "invocation_id" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN invocation_id TEXT")
        if "pid" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN pid INTEGER")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS runs_invocation_id_unique ON runs(invocation_id) WHERE invocation_id IS NOT NULL"
        )

    @staticmethod
    def _backfill_acceptance_verifications(connection: sqlite3.Connection) -> None:
        connection.execute(
            """UPDATE acceptances
               SET verification_id = (
                   SELECT candidate.id
                   FROM (
                       SELECT id, status, evidence_ref, summary
                       FROM verifications
                       WHERE verifications.run_id = acceptances.run_id
                         AND verifications.created_at <= acceptances.created_at
                       ORDER BY verifications.rowid DESC LIMIT 1
                   ) AS candidate
                   WHERE candidate.status = 'passed'
                     AND length(trim(candidate.evidence_ref)) > 0
                     AND length(trim(candidate.summary)) > 0
               )
               WHERE verification_id IS NULL"""
        )
        unresolved = connection.execute(
            "SELECT COUNT(*) FROM acceptances WHERE verification_id IS NULL"
        ).fetchone()[0]
        if unresolved:
            raise sqlite3.DatabaseError(
                f"Migration requires manual repair: {unresolved} Acceptance record(s) lack passing Verification evidence"
            )
        invalid = connection.execute(
            """SELECT COUNT(*)
               FROM acceptances AS acceptance
               WHERE NOT EXISTS (
                   SELECT 1
                   FROM verifications AS verification
                   WHERE verification.id = acceptance.verification_id
                     AND verification.run_id = acceptance.run_id
                     AND verification.status = 'passed'
                     AND length(trim(verification.evidence_ref)) > 0
                     AND length(trim(verification.summary)) > 0
                     AND verification.created_at <= acceptance.created_at
                     AND verification.rowid = (
                         SELECT latest.rowid
                         FROM verifications AS latest
                         WHERE latest.run_id = acceptance.run_id
                           AND latest.created_at <= acceptance.created_at
                         ORDER BY latest.rowid DESC LIMIT 1
                     )
               )"""
        ).fetchone()[0]
        if invalid:
            raise sqlite3.DatabaseError(
                f"Migration requires manual repair: {invalid} Acceptance record(s) lack valid pinned Verification evidence"
            )

    @staticmethod
    def _apply_v1(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                root_path TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id),
                title TEXT NOT NULL,
                goal TEXT NOT NULL,
                acceptance_criteria_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ready','active','verification','accepted','blocked','archived')),
                accepted_run_id TEXT,
                accepted_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL REFERENCES tickets(id),
                runner TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','cancelled')),
                started_at TEXT,
                finished_at TEXT,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                sequence INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, sequence)
            );
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TABLE IF NOT EXISTS debug_episodes (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                symptom TEXT NOT NULL,
                reproduction TEXT NOT NULL,
                environment TEXT NOT NULL,
                error_fingerprint TEXT NOT NULL,
                hypotheses_json TEXT NOT NULL,
                attempted_fixes_json TEXT NOT NULL,
                failed_attempts_json TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                accepted_fix TEXT NOT NULL,
                regression_test TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS verifications (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                status TEXT NOT NULL CHECK(status IN ('passed','failed')),
                evidence_ref TEXT NOT NULL,
                summary TEXT NOT NULL,
                verifier TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS acceptances (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL REFERENCES tickets(id),
                run_id TEXT NOT NULL REFERENCES runs(id),
                verification_id TEXT NOT NULL REFERENCES verifications(id),
                accepted_by TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_candidates (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id),
                source_run_id TEXT NOT NULL REFERENCES runs(id),
                kind TEXT NOT NULL CHECK(kind IN ('episodic','semantic','procedural','preference','project')),
                statement TEXT NOT NULL,
                scope TEXT NOT NULL,
                evidence_ref TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','disabled')),
                created_at TEXT NOT NULL
            );
            """
        )

    def integrity_check(self) -> str:
        with self.connect() as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            return int(row[0] or 0)

    def backup_to(self, target: str | Path) -> Path:
        target_path = Path(target)
        if target_path.resolve() == self.path.resolve():
            raise ValueError("Backup target must differ from the source database")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with self.connect() as source:
                with closing(sqlite3.connect(temporary)) as destination:
                    source.backup(destination)
                    if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise sqlite3.DatabaseError("Backup integrity check failed")
            os.replace(temporary, target_path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target_path

    @staticmethod
    def decode_json(value: str):
        return json.loads(value)
