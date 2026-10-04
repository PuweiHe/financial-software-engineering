"""Whole-tree correctness lint plus focused formatting, lint and type gates."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FOCUSED = [
    'business-analytics-agent/metrics.py',
    'business-analytics-agent/portfolio_demo',
    'investment-risk-monitor-unified/db/query_adapter.py',
    'investment-risk-monitor-unified/dao',
    'investment-risk-monitor-unified/tests/test_dao_parameters.py',
    'investment-risk-monitor-unified/tests/test_query_adapter.py',
    'investment-risk-monitor-unified/tests/test_runner_contract.py',
    'wealth-agent/evals/evaluate_contracts.py',
]
for project in ('wealth-agent', 'business-analytics-agent'):
    FOCUSED.extend(f'{project}/{name}' for name in ('agent', 'web', 'model/ChatBody.py',
                  'main.py', 'service_tests', 'util/http_util.py', 'util/yield_util.py'))
FOCUSED.extend(['wealth-agent/util/card_util.py', 'wealth-agent/services/xunfei_iat.py'])


def main():
    commands = [
        ['ruff', 'check', '.'],
        ['ruff', 'check', '--select', 'E4,E7,E9,F', *FOCUSED],
        ['ruff', 'format', '--check', *FOCUSED],
        ['mypy', 'business-analytics-agent/metrics.py', 'wealth-agent/agent/entity_schema.py'],
    ]
    for command in commands:
        subprocess.run([sys.executable, '-m', *command], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
