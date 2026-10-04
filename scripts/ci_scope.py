"""Select expensive PR checks; main, manual and scheduled runs check everything."""

import os
import subprocess


def select_checks(paths):
    shared = any((path.startswith(('.github/', 'scripts/')) or '/' not in path)
                 and not path.endswith('.md')
                 for path in paths)
    return {
        'services': shared or any(path.startswith(('wealth-agent/', 'business-analytics-agent/'))
                                  and not path.endswith('.md') for path in paths),
        'database': shared or any(path.startswith('investment-risk-monitor-unified/')
                                  and not path.endswith('.md') for path in paths),
    }


if __name__ == '__main__':
    base, head = os.environ.get('BASE_SHA'), os.environ.get('HEAD_SHA')
    checks = {'services': True, 'database': True}
    if base and head:
        paths = subprocess.check_output(
            ['git', 'diff', '--name-only', '-z', f'{base}...{head}'], text=True
        ).split('\0')
        checks = select_checks([path for path in paths if path])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for name, enabled in checks.items():
            output.write(f'{name}={str(enabled).lower()}\n')
