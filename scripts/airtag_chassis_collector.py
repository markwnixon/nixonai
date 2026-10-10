#!/usr/bin/env python3
"""Read Apple's local Find My item cache and publish chassis observations."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import plistlib
import sys
from pathlib import Path

import requests


DEFAULT_CACHE = Path.home() / 'Library/Caches/com.apple.findmy.fmipcore/Items.data'


def load_cache(path: Path):
    try:
        raw = path.read_bytes()
    except PermissionError as exc:
        raise RuntimeError(
            f'macOS denied access to {path}. Grant Full Disk Access to the Python runtime used by this launch agent.'
        ) from exc
    for loader in (plistlib.loads, lambda value: json.loads(value.decode('utf-8'))):
        try:
            return loader(raw)
        except (ValueError, TypeError, UnicodeDecodeError, plistlib.InvalidFileException):
            continue
    raise RuntimeError(f'Unsupported Find My cache format: {path}')


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def first_value(mapping, keys):
    for key in keys:
        if mapping.get(key) not in (None, ''):
            return mapping[key]
    return None


def parse_timestamp(value):
    if isinstance(value, datetime.datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        parsed = datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc)
    elif isinstance(value, str):
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('missing observation timestamp')
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def extract_items(cache):
    items = {}
    for candidate in walk(cache):
        location = candidate.get('location') if isinstance(candidate.get('location'), dict) else candidate
        name = first_value(candidate, ('name', 'itemName', 'deviceName', 'displayName'))
        latitude = first_value(location, ('latitude', 'lat'))
        longitude = first_value(location, ('longitude', 'lon', 'lng'))
        timestamp = first_value(location, ('timeStamp', 'timestamp', 'locationTimestamp', 'date'))
        if not name or latitude is None or longitude is None or timestamp is None:
            continue
        try:
            items[str(name)] = {
                'airtag_name': str(name),
                'latitude': float(latitude),
                'longitude': float(longitude),
                'observed_at': parse_timestamp(timestamp),
            }
        except (TypeError, ValueError, OverflowError):
            continue
    return items


def load_mapping(path: Path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not data:
        raise RuntimeError('mapping must be a non-empty JSON object of chassis ID to AirTag name')
    return {str(chassis).strip(): str(tag).strip() for chassis, tag in data.items() if str(chassis).strip() and str(tag).strip()}


def build_observations(items, mapping):
    observations = []
    missing = []
    for chassis_id, airtag_name in mapping.items():
        item = items.get(airtag_name)
        if item is None:
            missing.append({'chassis_id': chassis_id, 'airtag_name': airtag_name})
            continue
        observations.append({'chassis_id': chassis_id, **item})
    return observations, missing


def fetch_token(session, base_url, client_id, client_secret):
    response = session.post(
        f'{base_url.rstrip("/")}/api_bot_token',
        json={'client_id': client_id, 'client_secret': client_secret},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()['access_token']


def publish(session, base_url, token, observations):
    response = session.post(
        f'{base_url.rstrip("/")}/bot/chassis/locations',
        headers={'Authorization': f'Bearer {token}'},
        json={'observations': observations},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=Path(os.getenv('FINDMY_ITEMS_CACHE', DEFAULT_CACHE)))
    parser.add_argument('--mapping', type=Path, default=Path(os.getenv('CHASSIS_AIRTAG_MAPPING', Path.home() / '.config/class8/chassis_airtags.json')))
    parser.add_argument('--base-url', default=os.getenv('BOT_API_BASE_URL', ''))
    parser.add_argument('--client-id', default=os.getenv('BOT_CLIENT_ID', ''))
    parser.add_argument('--client-secret', default=os.getenv('BOT_CLIENT_SECRET', ''))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    items = extract_items(load_cache(args.cache))
    observations, missing = build_observations(items, load_mapping(args.mapping))
    result = {'found_items': len(items), 'observations': observations, 'missing': missing}
    if args.dry_run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if not args.base_url or not args.client_id or not args.client_secret:
        raise RuntimeError('BOT_API_BASE_URL, BOT_CLIENT_ID, and BOT_CLIENT_SECRET are required')
    if observations:
        session = requests.Session()
        token = fetch_token(session, args.base_url, args.client_id, args.client_secret)
        result['upload'] = publish(session, args.base_url, token, observations)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
