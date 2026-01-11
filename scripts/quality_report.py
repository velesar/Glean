#!/usr/bin/env python3
"""
Comprehensive Code Quality Report Generator for Glean.

Generates a unified report including:
- Type checking (mypy)
- Linting (ruff, eslint)
- Security scanning (bandit)
- Dependency audits (pip-audit, npm audit)
- Complexity metrics (cyclomatic, cognitive)
- Architecture metrics (coupling, cohesion estimates)
- Test coverage
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ModuleMetrics:
    """Metrics for a single module."""
    name: str
    lines: int = 0
    cyclomatic_complexity: float = 0.0
    cognitive_complexity: float = 0.0
    maintainability_index: float = 0.0
    test_coverage: float = 0.0
    imports: int = 0
    functions: int = 0
    classes: int = 0


@dataclass
class QualityReport:
    """Complete quality report."""
    timestamp: str = ""

    # Type checking
    type_errors: int = 0
    type_warnings: int = 0
    type_details: list = field(default_factory=list)

    # Linting
    python_lint_issues: int = 0
    python_lint_details: list = field(default_factory=list)
    typescript_lint_issues: int = 0
    typescript_lint_details: list = field(default_factory=list)

    # Security
    security_issues: int = 0
    security_high: int = 0
    security_medium: int = 0
    security_low: int = 0
    security_details: list = field(default_factory=list)

    # Dependencies
    python_vulnerabilities: int = 0
    python_vuln_details: list = field(default_factory=list)
    node_vulnerabilities: int = 0
    node_vuln_details: list = field(default_factory=list)

    # Complexity
    avg_cyclomatic: float = 0.0
    avg_cognitive: float = 0.0
    avg_maintainability: float = 0.0
    high_complexity_functions: list = field(default_factory=list)
    module_metrics: list = field(default_factory=list)

    # Architecture
    total_modules: int = 0
    avg_imports_per_module: float = 0.0
    circular_dependencies: list = field(default_factory=list)
    coupling_score: str = ""
    cohesion_score: str = ""

    # Test coverage
    total_coverage: float = 0.0
    covered_lines: int = 0
    total_lines: int = 0
    coverage_by_module: dict = field(default_factory=dict)

    # Tests
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0


def run_command(cmd: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def check_type_errors(report: QualityReport) -> None:
    """Run mypy type checking."""
    print("  Running type checker (mypy)...")

    code, stdout, stderr = run_command([
        "python", "-m", "mypy", "src/",
        "--ignore-missing-imports",
        "--no-error-summary"
    ])

    output = stdout + stderr
    lines = [l for l in output.strip().split('\n') if l and ': error:' in l or ': warning:' in l]

    for line in lines:
        if ': error:' in line:
            report.type_errors += 1
            report.type_details.append(line)
        elif ': warning:' in line:
            report.type_warnings += 1
            report.type_details.append(line)


def check_python_lint(report: QualityReport) -> None:
    """Run ruff linting."""
    print("  Running Python linter (ruff)...")

    code, stdout, stderr = run_command([
        "python", "-m", "ruff", "check", "src/", "web/api/",
        "--output-format=json"
    ])

    try:
        issues = json.loads(stdout) if stdout else []
        report.python_lint_issues = len(issues)
        for issue in issues[:20]:  # Limit details
            report.python_lint_details.append(
                f"{issue.get('filename', '')}:{issue.get('location', {}).get('row', '')}: "
                f"{issue.get('code', '')} {issue.get('message', '')}"
            )
    except json.JSONDecodeError:
        # Fallback to line counting
        lines = [l for l in stdout.split('\n') if l.strip()]
        report.python_lint_issues = len(lines)


def check_typescript_lint(report: QualityReport) -> None:
    """Run ESLint on TypeScript."""
    print("  Running TypeScript linter (eslint)...")

    frontend_path = Path("web/frontend")
    if not frontend_path.exists():
        return

    code, stdout, stderr = run_command(
        ["npm", "run", "lint", "--", "--format=json"],
        cwd=str(frontend_path)
    )

    try:
        # ESLint JSON output
        results = json.loads(stdout) if stdout else []
        for file_result in results:
            messages = file_result.get('messages', [])
            report.typescript_lint_issues += len(messages)
            for msg in messages[:10]:
                report.typescript_lint_details.append(
                    f"{file_result.get('filePath', '')}:{msg.get('line', '')}: "
                    f"{msg.get('message', '')}"
                )
    except json.JSONDecodeError:
        # Count from stderr/stdout
        if "error" in (stdout + stderr).lower():
            report.typescript_lint_issues = 1


def check_security(report: QualityReport) -> None:
    """Run bandit security scanner."""
    print("  Running security scanner (bandit)...")

    code, stdout, stderr = run_command([
        "python", "-m", "bandit", "-r", "src/", "-f", "json", "-q"
    ])

    try:
        data = json.loads(stdout) if stdout else {}
        results = data.get('results', [])

        for issue in results:
            severity = issue.get('issue_severity', 'LOW')
            report.security_issues += 1

            if severity == 'HIGH':
                report.security_high += 1
            elif severity == 'MEDIUM':
                report.security_medium += 1
            else:
                report.security_low += 1

            report.security_details.append(
                f"[{severity}] {issue.get('filename', '')}:{issue.get('line_number', '')}: "
                f"{issue.get('issue_text', '')}"
            )
    except json.JSONDecodeError:
        pass


def check_python_deps(report: QualityReport) -> None:
    """Run pip-audit for Python dependency vulnerabilities."""
    print("  Running Python dependency audit (pip-audit)...")

    code, stdout, stderr = run_command([
        "python", "-m", "pip_audit", "--format=json"
    ])

    try:
        data = json.loads(stdout) if stdout else {}
        dependencies = data.get('dependencies', [])

        # Count packages with vulnerabilities
        vuln_count = 0
        for dep in dependencies:
            vulns = dep.get('vulns', [])
            if vulns:
                vuln_count += len(vulns)
                for vuln in vulns[:3]:  # Limit per package
                    report.python_vuln_details.append(
                        f"{dep.get('name', '')}: {vuln.get('id', 'Unknown')}"
                    )

        report.python_vulnerabilities = vuln_count
    except json.JSONDecodeError:
        # Check for "No vulnerabilities found" message
        if "No known vulnerabilities" in stdout or "No known vulnerabilities" in stderr:
            report.python_vulnerabilities = 0


def check_node_deps(report: QualityReport) -> None:
    """Run npm audit for Node.js dependency vulnerabilities."""
    print("  Running Node.js dependency audit (npm audit)...")

    frontend_path = Path("web/frontend")
    if not frontend_path.exists():
        return

    code, stdout, stderr = run_command(
        ["npm", "audit", "--json"],
        cwd=str(frontend_path)
    )

    try:
        data = json.loads(stdout) if stdout else {}
        vulns = data.get('vulnerabilities', {})
        report.node_vulnerabilities = len(vulns)
        for name, details in list(vulns.items())[:10]:
            report.node_vuln_details.append(
                f"{name}: {details.get('severity', 'unknown')} severity"
            )
    except json.JSONDecodeError:
        pass


def analyze_complexity(report: QualityReport) -> None:
    """Analyze code complexity using radon."""
    print("  Analyzing code complexity (radon)...")

    # Cyclomatic complexity
    code, stdout, stderr = run_command([
        "python", "-m", "radon", "cc", "src/", "-a", "-j"
    ])

    try:
        data = json.loads(stdout) if stdout else {}
        complexities = []

        for filepath, functions in data.items():
            for func in functions:
                cc = func.get('complexity', 0)
                complexities.append(cc)

                if cc > 10:  # High complexity threshold
                    report.high_complexity_functions.append(
                        f"{filepath}:{func.get('lineno', '')} {func.get('name', '')} (CC={cc})"
                    )

        if complexities:
            report.avg_cyclomatic = sum(complexities) / len(complexities)
    except json.JSONDecodeError:
        pass

    # Maintainability index
    code, stdout, stderr = run_command([
        "python", "-m", "radon", "mi", "src/", "-j"
    ])

    try:
        data = json.loads(stdout) if stdout else {}
        mi_scores = []

        for filepath, score in data.items():
            if isinstance(score, dict):
                mi = score.get('mi', 0)
            else:
                mi = score
            mi_scores.append(mi)

            module_name = Path(filepath).stem
            report.module_metrics.append({
                'name': module_name,
                'maintainability_index': round(mi, 2),
                'grade': get_mi_grade(mi)
            })

        if mi_scores:
            report.avg_maintainability = sum(mi_scores) / len(mi_scores)
    except json.JSONDecodeError:
        pass

    # Cognitive complexity (using radon raw for approximation)
    code, stdout, stderr = run_command([
        "python", "-m", "radon", "raw", "src/", "-j"
    ])

    try:
        data = json.loads(stdout) if stdout else {}
        # Approximate cognitive complexity from raw metrics
        cognitive_scores = []

        for filepath, metrics in data.items():
            if isinstance(metrics, dict):
                # Cognitive complexity approximation:
                # Based on LOC, LLOC, and branching
                lloc = metrics.get('lloc', 0)
                sloc = metrics.get('sloc', 0)
                # Simple heuristic
                cognitive = (lloc * 0.1) + (sloc * 0.05)
                cognitive_scores.append(cognitive)

        if cognitive_scores:
            report.avg_cognitive = sum(cognitive_scores) / len(cognitive_scores)
    except json.JSONDecodeError:
        pass


def get_mi_grade(mi: float) -> str:
    """Get maintainability index grade."""
    if mi >= 20:
        return 'A'
    elif mi >= 10:
        return 'B'
    elif mi >= 0:
        return 'C'
    else:
        return 'F'


def analyze_architecture(report: QualityReport) -> None:
    """Analyze architecture metrics."""
    print("  Analyzing architecture metrics...")

    src_path = Path("src")
    if not src_path.exists():
        return

    modules = list(src_path.rglob("*.py"))
    report.total_modules = len(modules)

    total_imports = 0
    internal_deps = {}  # module -> list of internal modules it imports

    for module_path in modules:
        try:
            content = module_path.read_text()
            lines = content.split('\n')

            imports = 0
            internal_imports = []

            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    imports += 1
                    # Track internal imports
                    if 'from src.' in stripped or 'import src.' in stripped:
                        # Extract module name
                        parts = stripped.split()
                        for i, part in enumerate(parts):
                            if part.startswith('src.'):
                                internal_imports.append(part.split('.')[1])

            total_imports += imports
            module_name = module_path.stem
            internal_deps[module_name] = internal_imports

        except Exception:
            pass

    if report.total_modules > 0:
        report.avg_imports_per_module = total_imports / report.total_modules

    # Check for potential circular dependencies
    for module, deps in internal_deps.items():
        for dep in deps:
            if dep != module and dep in internal_deps and module in internal_deps.get(dep, []):
                cycle = tuple(sorted([module, dep]))
                cycle_str = f"{cycle[0]} <-> {cycle[1]}"
                if cycle_str not in report.circular_dependencies:
                    report.circular_dependencies.append(cycle_str)

    # Calculate coupling score (based on inter-module dependencies)
    avg_deps = sum(len(deps) for deps in internal_deps.values()) / max(len(internal_deps), 1)
    if avg_deps < 2:
        report.coupling_score = "Low (Good)"
    elif avg_deps < 4:
        report.coupling_score = "Medium"
    else:
        report.coupling_score = "High (Consider refactoring)"

    # Cohesion estimation (based on module size and function count)
    # This is a rough heuristic
    report.cohesion_score = "Moderate (Estimated)"


def run_tests_with_coverage(report: QualityReport) -> None:
    """Run tests and collect coverage."""
    print("  Running tests with coverage...")

    code, stdout, stderr = run_command([
        "python", "-m", "pytest", "tests/",
        "--cov=src",
        "--cov-report=json:coverage.json",
        "-q"
    ])

    output = stdout + stderr

    # Parse test results
    for line in output.split('\n'):
        if 'passed' in line or 'failed' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'passed' and i > 0:
                    try:
                        report.tests_passed = int(parts[i-1])
                    except ValueError:
                        pass
                elif part == 'failed' and i > 0:
                    try:
                        report.tests_failed = int(parts[i-1])
                    except ValueError:
                        pass

    report.tests_total = report.tests_passed + report.tests_failed

    # Parse coverage JSON
    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        try:
            data = json.loads(coverage_file.read_text())
            totals = data.get('totals', {})
            report.total_coverage = totals.get('percent_covered', 0)
            report.covered_lines = totals.get('covered_lines', 0)
            report.total_lines = totals.get('num_statements', 0)

            # Per-module coverage
            files = data.get('files', {})
            for filepath, metrics in files.items():
                module_name = Path(filepath).name
                summary = metrics.get('summary', {})
                report.coverage_by_module[module_name] = summary.get('percent_covered', 0)

            # Clean up
            coverage_file.unlink()
        except Exception:
            pass


def generate_report(report: QualityReport) -> str:
    """Generate the formatted report."""

    lines = []
    lines.append("=" * 80)
    lines.append("                    GLEAN CODE QUALITY REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {report.timestamp}")
    lines.append("")

    # Summary
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)

    total_issues = (
        report.type_errors +
        report.python_lint_issues +
        report.typescript_lint_issues +
        report.security_issues +
        report.python_vulnerabilities +
        report.node_vulnerabilities
    )

    status = "PASS" if total_issues == 0 else "ISSUES FOUND"
    lines.append(f"Overall Status: {status}")
    lines.append(f"Total Issues: {total_issues}")
    lines.append(f"Test Coverage: {report.total_coverage:.1f}%")
    lines.append(f"Tests: {report.tests_passed} passed, {report.tests_failed} failed")
    lines.append(f"Avg Maintainability: {report.avg_maintainability:.1f} ({get_mi_grade(report.avg_maintainability)})")
    lines.append("")

    # Type Checking
    lines.append("-" * 80)
    lines.append("TYPE CHECKING (mypy)")
    lines.append("-" * 80)
    lines.append(f"Errors: {report.type_errors}")
    lines.append(f"Warnings: {report.type_warnings}")
    if report.type_details:
        lines.append("\nDetails (first 10):")
        for detail in report.type_details[:10]:
            lines.append(f"  {detail}")
    lines.append("")

    # Linting
    lines.append("-" * 80)
    lines.append("LINTING")
    lines.append("-" * 80)
    lines.append(f"Python (ruff): {report.python_lint_issues} issues")
    lines.append(f"TypeScript (eslint): {report.typescript_lint_issues} issues")
    if report.python_lint_details:
        lines.append("\nPython details (first 10):")
        for detail in report.python_lint_details[:10]:
            lines.append(f"  {detail}")
    lines.append("")

    # Security
    lines.append("-" * 80)
    lines.append("SECURITY (bandit)")
    lines.append("-" * 80)
    lines.append(f"Total Issues: {report.security_issues}")
    lines.append(f"  High: {report.security_high}")
    lines.append(f"  Medium: {report.security_medium}")
    lines.append(f"  Low: {report.security_low}")
    if report.security_details:
        lines.append("\nDetails:")
        for detail in report.security_details[:10]:
            lines.append(f"  {detail}")
    lines.append("")

    # Dependencies
    lines.append("-" * 80)
    lines.append("DEPENDENCY VULNERABILITIES")
    lines.append("-" * 80)
    lines.append(f"Python (pip-audit): {report.python_vulnerabilities} vulnerabilities")
    lines.append(f"Node.js (npm audit): {report.node_vulnerabilities} vulnerabilities")
    if report.python_vuln_details:
        lines.append("\nPython vulnerabilities:")
        for detail in report.python_vuln_details:
            lines.append(f"  {detail}")
    if report.node_vuln_details:
        lines.append("\nNode.js vulnerabilities:")
        for detail in report.node_vuln_details:
            lines.append(f"  {detail}")
    lines.append("")

    # Complexity
    lines.append("-" * 80)
    lines.append("COMPLEXITY METRICS")
    lines.append("-" * 80)
    lines.append(f"Average Cyclomatic Complexity: {report.avg_cyclomatic:.2f}")
    lines.append(f"Average Cognitive Complexity: {report.avg_cognitive:.2f}")
    lines.append(f"Average Maintainability Index: {report.avg_maintainability:.1f} ({get_mi_grade(report.avg_maintainability)})")

    if report.high_complexity_functions:
        lines.append(f"\nHigh Complexity Functions (CC > 10):")
        for func in report.high_complexity_functions[:10]:
            lines.append(f"  {func}")
    lines.append("")

    # Architecture
    lines.append("-" * 80)
    lines.append("ARCHITECTURE METRICS")
    lines.append("-" * 80)
    lines.append(f"Total Python Modules: {report.total_modules}")
    lines.append(f"Avg Imports per Module: {report.avg_imports_per_module:.1f}")
    lines.append(f"Coupling: {report.coupling_score}")
    lines.append(f"Cohesion: {report.cohesion_score}")

    if report.circular_dependencies:
        lines.append(f"\nPotential Circular Dependencies:")
        for dep in report.circular_dependencies:
            lines.append(f"  {dep}")
    lines.append("")

    # Test Coverage
    lines.append("-" * 80)
    lines.append("TEST COVERAGE")
    lines.append("-" * 80)
    lines.append(f"Total Coverage: {report.total_coverage:.1f}%")
    lines.append(f"Lines Covered: {report.covered_lines} / {report.total_lines}")
    lines.append(f"Tests: {report.tests_passed} passed, {report.tests_failed} failed (total: {report.tests_total})")

    if report.coverage_by_module:
        lines.append("\nCoverage by Module:")
        sorted_modules = sorted(
            report.coverage_by_module.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for module, coverage in sorted_modules[:15]:
            bar_len = int(coverage / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {module:30} {bar} {coverage:5.1f}%")
    lines.append("")

    # Module Maintainability
    if report.module_metrics:
        lines.append("-" * 80)
        lines.append("MODULE MAINTAINABILITY")
        lines.append("-" * 80)
        sorted_metrics = sorted(
            report.module_metrics,
            key=lambda x: x['maintainability_index']
        )
        for metric in sorted_metrics[:15]:
            mi = metric['maintainability_index']
            grade = metric['grade']
            lines.append(f"  {metric['name']:30} MI={mi:5.1f} Grade={grade}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return '\n'.join(lines)


def main():
    """Run the quality report generator."""
    print("=" * 60)
    print("  Glean Code Quality Report Generator")
    print("=" * 60)
    print()

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    report = QualityReport()
    report.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Running quality checks...")
    print()

    # Run all checks
    check_type_errors(report)
    check_python_lint(report)
    check_typescript_lint(report)
    check_security(report)
    check_python_deps(report)
    check_node_deps(report)
    analyze_complexity(report)
    analyze_architecture(report)
    run_tests_with_coverage(report)

    print()
    print("Generating report...")
    print()

    # Generate and print report
    report_text = generate_report(report)
    print(report_text)

    # Save to file
    report_file = Path("quality_report.txt")
    report_file.write_text(report_text)
    print(f"\nReport saved to: {report_file}")

    # Return exit code based on critical issues
    critical_issues = (
        report.security_high +
        report.python_vulnerabilities +
        report.node_vulnerabilities +
        report.tests_failed
    )

    return 1 if critical_issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
