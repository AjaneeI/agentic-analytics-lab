"""Load only existing local ClickHouse settings; never print credential values."""
from pathlib import Path
import os
import shlex
from urllib.parse import urlparse

ENV_FILE = Path('/Users/ajaneeigharo/Projects/agentic-analytics-lab/.env')
def load_existing_clickhouse_environment():
    allowed = {'CLICKHOUSE_URL', 'CLICKHOUSE_USER', 'CLICKHOUSE_PASSWORD'}
    found = {}
    for line in ENV_FILE.read_text().splitlines():
        text = line.strip()
        if not text or text.startswith('#') or '=' not in text:
            continue
        key, value = text.split('=', 1)
        key = key.removeprefix('export ').strip()
        if key not in allowed:
            continue
        parts = shlex.split(value.strip(), comments=True, posix=True)
        if len(parts) > 1:
            raise ValueError('Existing local setting needs explicit quoted parsing')
        found[key] = parts[0] if parts else ''
    if not {'CLICKHOUSE_USER','CLICKHOUSE_PASSWORD'} <= set(found):
        raise ValueError('Existing local credential settings are missing')
    endpoint = urlparse(found.get('CLICKHOUSE_URL', 'http://127.0.0.1:8123'))
    if endpoint.scheme != 'http' or endpoint.hostname not in {'127.0.0.1','localhost'} or endpoint.port != 8123:
        raise ValueError('Existing endpoint differs from approved local service')
    os.environ.update(found)
    return {'source': 'existing repository .env; only CLICKHOUSE_URL/USER/PASSWORD keys loaded',
            'local_endpoint_verified': True, 'credential_values_logged': False,
            'permissions_or_account_configuration_changed': False}
