import tempfile
import threading
import time
import unittest
import sys
from pathlib import Path

from company_workbench.runner import CodexCliRunner, ClaudeCliRunner, ProcessResult, SubprocessExecutor


class FakeExecutor:
    def __init__(self, result: ProcessResult):
        self.result = result
        self.calls = []

    def execute(self, argv, **kwargs):
        self.calls.append((tuple(argv), kwargs))
        return self.result


class FakeProcessHandle:
    def __init__(self, result: ProcessResult):
        self.pid = result.pid
        self._result = result

    def wait(self, *, timeout_seconds, cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            return ProcessResult(exit_code=None, cancelled=True, pid=self.pid)
        return self._result


class FakeStartExecutor:
    def __init__(self, result: ProcessResult):
        self.result = result
        self.calls = []

    def start(self, argv, *, cwd):
        self.calls.append((tuple(argv), cwd))
        return FakeProcessHandle(self.result)


class CodexCliRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def runner(self, result):
        executor = FakeExecutor(result)
        return CodexCliRunner(executor=executor), executor

    def test_builds_fixed_argv_without_shell_string(self):
        runner, executor = self.runner(ProcessResult(0, '{"ok":true}', pid=42))
        runner.run("hello; rm -rf ignored", cwd=self.cwd)
        argv, options = executor.calls[0]
        self.assertEqual(
            ("codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "--ephemeral", "--json", "--cd", str(self.cwd.resolve())),
            argv[:-1],
        )
        self.assertEqual("hello; rm -rf ignored", argv[-1])
        self.assertEqual(self.cwd.resolve(), options["cwd"])

        runner.run("with model", cwd=self.cwd, model="o3")
        argv_model, _ = executor.calls[1]
        self.assertIn("-m", argv_model)
        self.assertEqual(argv_model[argv_model.index("-m") + 1], "o3")

    def test_default_model_and_env_fallback(self):
        executor = FakeExecutor(ProcessResult(0, '{"ok":true}', pid=42))
        runner = CodexCliRunner(executor=executor, default_model="gpt-5.5")
        runner.run("work", cwd=self.cwd)
        argv, _ = executor.calls[0]
        self.assertIn("-m", argv)
        self.assertEqual("gpt-5.5", argv[argv.index("-m") + 1])

        # Explicit model overrides default_model
        runner.run("work override", cwd=self.cwd, model="o3")
        argv_override, _ = executor.calls[1]
        self.assertEqual("o3", argv_override[argv_override.index("-m") + 1])

    def test_rejects_unallowlisted_executable(self):
        with self.assertRaises(ValueError):
            CodexCliRunner("powershell.exe")
        with self.assertRaises(ValueError):
            CodexCliRunner(str(self.cwd / "codex.exe"))

    def test_rejects_invalid_inputs(self):
        runner, _ = self.runner(ProcessResult(0, "ok"))
        for prompt, cwd, timeout in (("", self.cwd, 10), ("x\0y", self.cwd, 10), ("x", self.cwd / "missing", 10), ("x", self.cwd, 0)):
            with self.subTest(prompt=prompt, cwd=cwd, timeout=timeout):
                with self.assertRaises(ValueError):
                    runner.run(prompt, cwd=cwd, timeout_seconds=timeout)

    def test_classifies_success(self):
        runner, _ = self.runner(ProcessResult(0, '{"ok":true}', pid=7))
        result = runner.run("work", cwd=self.cwd)
        self.assertEqual(("completed", None, 7), (result.outcome, result.error_code, result.pid))

    def test_classifies_nonzero_timeout_cancel_and_empty_output(self):
        cases = (
            (ProcessResult(2, stderr="bad"), "failed", "RUNNER-EXIT-NONZERO"),
            (ProcessResult(-9, timed_out=True), "failed", "RUNNER-TIMEOUT"),
            (ProcessResult(-15, cancelled=True), "cancelled", "RUNNER-CANCELLED"),
            (ProcessResult(0, "   "), "failed", "RUNNER-INVALID-OUTPUT"),
        )
        for process_result, outcome, error in cases:
            with self.subTest(error=error):
                runner, _ = self.runner(process_result)
                result = runner.run("work", cwd=self.cwd)
                self.assertEqual((outcome, error), (result.outcome, result.error_code))

    def test_redacts_secrets_before_returning(self):
        raw = "Authorization: Bearer secret123 api_key=abc123456789 sk-abcdefghijklmnop"
        runner, _ = self.runner(ProcessResult(1, raw, raw))
        result = runner.run("work", cwd=self.cwd)
        self.assertNotIn("secret123", result.stdout + result.stderr)
        self.assertNotIn("abc123456789", result.stdout + result.stderr)
        self.assertNotIn("sk-abcdefghijklmnop", result.stdout + result.stderr)
        self.assertIn("[REDACTED]", result.stdout)

    def test_redacts_provider_tokens_multiline_secrets_and_explicit_values(self):
        raw = (
            "AKIAABCDEFGHIJKLMNOP ghp_abcdefghijklmnopqrstuvwxyz123456 "
            "xoxb-123456789-abcdefghijkl password: two word secret\ncustom-value-789"
        )
        runner, _ = self.runner(ProcessResult(1, raw, ""))
        result = runner.run("work", cwd=self.cwd, sensitive_values=("custom-value-789",))
        for secret in ("AKIAABCDEFGHIJKLMNOP", "ghp_abcdefghijklmnopqrstuvwxyz123456", "xoxb-123456789-abcdefghijkl", "two word secret", "custom-value-789"):
            self.assertNotIn(secret, result.stdout)

    def test_bounds_stdout_and_stderr(self):
        runner, _ = self.runner(ProcessResult(1, "a" * 1000, "b" * 1000))
        result = runner.run("work", cwd=self.cwd, max_output_chars=256)
        self.assertEqual(256, len(result.stdout))
        self.assertEqual(256, len(result.stderr))
        self.assertIn("[TRUNCATED]", result.stdout)

    def test_passes_cancel_event_and_timeout_to_executor(self):
        runner, executor = self.runner(ProcessResult(0, "ok"))
        event = threading.Event()
        runner.run("work", cwd=self.cwd, timeout_seconds=12, cancel_event=event)
        options = executor.calls[0][1]
        self.assertIs(event, options["cancel_event"])
        self.assertEqual(12, options["timeout_seconds"])

    def test_subprocess_executor_cancels_running_process(self):
        cancel = threading.Event()
        timer = threading.Timer(0.1, cancel.set)
        timer.start()
        started = time.monotonic()
        try:
            result = SubprocessExecutor().execute(
                (sys.executable, "-c", "import time; time.sleep(10)"),
                cwd=self.cwd,
                timeout_seconds=5,
                cancel_event=cancel,
            )
        finally:
            timer.cancel()
        self.assertTrue(result.cancelled)
        self.assertFalse(result.timed_out)
        self.assertLess(time.monotonic() - started, 3)

    def test_subprocess_executor_times_out_running_process(self):
        started = time.monotonic()
        result = SubprocessExecutor().execute(
            (sys.executable, "-c", "import time; time.sleep(10)"),
            cwd=self.cwd,
            timeout_seconds=0.1,
            cancel_event=None,
        )
        self.assertTrue(result.timed_out)
        self.assertFalse(result.cancelled)
        self.assertLess(time.monotonic() - started, 3)

    def test_start_invocation_exposes_pid_before_wait_and_classifies_on_wait(self):
        executor = FakeStartExecutor(ProcessResult(0, '{"ok":true}', pid=99))
        runner = CodexCliRunner(executor=executor)
        invocation = runner.start_invocation("work", cwd=self.cwd)
        self.assertEqual(99, invocation.pid)
        self.assertEqual(1, len(executor.calls))
        result = invocation.wait()
        self.assertEqual(("completed", None, 99), (result.outcome, result.error_code, result.pid))

    def test_start_invocation_validates_before_spawning(self):
        executor = FakeStartExecutor(ProcessResult(0, "ok"))
        runner = CodexCliRunner(executor=executor)
        with self.assertRaises(ValueError):
            runner.start_invocation("", cwd=self.cwd)
        self.assertEqual([], executor.calls)

    def test_start_invocation_cancel_reports_cancelled_outcome(self):
        executor = FakeStartExecutor(ProcessResult(0, '{"ok":true}', pid=5))
        runner = CodexCliRunner(executor=executor)
        cancel_event = threading.Event()
        invocation = runner.start_invocation("work", cwd=self.cwd, cancel_event=cancel_event)
        cancel_event.set()
        result = invocation.wait()
        self.assertEqual(("cancelled", "RUNNER-CANCELLED"), (result.outcome, result.error_code))

    def test_start_invocation_redacts_and_bounds_like_run(self):
        raw = "Authorization: Bearer secret123 " + ("a" * 1000)
        executor = FakeStartExecutor(ProcessResult(1, raw, "", pid=1))
        runner = CodexCliRunner(executor=executor)
        result = runner.start_invocation("work", cwd=self.cwd, max_output_chars=256).wait()
        self.assertNotIn("secret123", result.stdout)
        self.assertEqual(256, len(result.stdout))

    def test_process_handle_start_then_wait_cancels_real_subprocess(self):
        cancel = threading.Event()
        timer = threading.Timer(0.1, cancel.set)
        timer.start()
        started = time.monotonic()
        try:
            handle = SubprocessExecutor().start(
                (sys.executable, "-c", "import time; time.sleep(10)"), cwd=self.cwd
            )
            self.assertGreater(handle.pid, 0)
            result = handle.wait(timeout_seconds=5, cancel_event=cancel)
        finally:
            timer.cancel()
        self.assertTrue(result.cancelled)
        self.assertLess(time.monotonic() - started, 3)


class ClaudeCliRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_fixed_argv(self):
        executor = FakeExecutor(ProcessResult(0, '{"result":"ok","usage":{"input_tokens":10,"output_tokens":5}}', pid=42))
        runner = ClaudeCliRunner(executor=executor)
        res = runner.run("hello claude", cwd=self.cwd)
        argv, options = executor.calls[0]
        self.assertEqual(
            ("claude", "-p", "hello claude", "--dangerously-skip-permissions", "--no-session-persistence", "--output-format", "json"),
            argv,
        )
        self.assertEqual("completed", res.outcome)
        self.assertEqual({"input_tokens": 10, "output_tokens": 5}, res.usage)

    def test_default_model_and_override(self):
        executor = FakeExecutor(ProcessResult(0, '{"result":"ok"}', pid=42))
        runner = ClaudeCliRunner(executor=executor, default_model="claude-sonnet-5")
        runner.run("work", cwd=self.cwd)
        argv, _ = executor.calls[0]
        self.assertIn("--model", argv)
        self.assertEqual("claude-sonnet-5", argv[argv.index("--model") + 1])

        # Explicit override
        runner.run("work override", cwd=self.cwd, model="claude-haiku-4.5")
        argv_ov, _ = executor.calls[1]
        self.assertEqual("claude-haiku-4.5", argv_ov[argv_ov.index("--model") + 1])

    def test_rejects_unallowlisted_executable(self):
        with self.assertRaises(ValueError):
            ClaudeCliRunner("bash")
        with self.assertRaises(ValueError):
            ClaudeCliRunner(str(self.cwd / "claude.exe"))


if __name__ == "__main__":
    unittest.main()
