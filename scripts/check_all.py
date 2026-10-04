"""Run isolated, credential-free project checks from any working directory."""
import os
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    "investment-risk-monitor-unified",
    "wealth-agent",
    "business-analytics-agent",
    "database-job-mutex",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', choices=('offline', 'services', 'integration'), default='offline')
    options = parser.parse_args()
    if options.level == 'integration' and os.environ.get('RUN_DB_INTEGRATION') != '1':
        parser.error('Integration checks require RUN_DB_INTEGRATION=1 and a configured test database')
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "ENABLE_EXTERNAL_SERVICES": "false", "ENABLE_HISTORY": "false"}
    subprocess.run([sys.executable, 'scripts/check_publishable_tree.py'], cwd=ROOT, env=env, check=True)
    for project in PROJECTS:
        print(f"\nChecking {project}", flush=True)
        for args in (("scripts/check_privacy.py",), ("-m", "unittest", "discover", "-s", "tests", "-v"), ("demo.py",)):
            subprocess.run([sys.executable, *args], cwd=ROOT / project, env=env, check=True)
    print("\nAll four projects passed their offline checks.")
    if options.level != 'offline':
        for project in ('wealth-agent', 'business-analytics-agent'):
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'service_tests', '-v'],
                           cwd=ROOT / project, env=env, check=True)
        subprocess.run([sys.executable, 'scripts/check_quality.py'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, 'evals/evaluate_contracts.py'], cwd=ROOT / 'wealth-agent', check=True)
        subprocess.run(['pnpm', 'test:e2e'], cwd=ROOT / 'business-analytics-agent',
                       env={**env, 'PYTHON': sys.executable}, check=True)
    if options.level == 'integration':
        for suite in ('integration_tests', 'adapter_tests'):
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', suite, '-v'],
                           cwd=ROOT / 'investment-risk-monitor-unified', env=env, check=True)


if __name__ == "__main__":
    main()
