import test from 'node:test';
import assert from 'node:assert/strict';
import { formatTime } from '../src/utils/format.ts';

const format = iso => formatTime(String(Date.parse(iso)));

test('Colorado winter time includes the year and MST', () => {
  assert.equal(format('2026-01-15T19:30:45Z'), 'Jan 15, 2026, 12:30:45 PM MST');
});
test('Colorado summer time uses MDT', () => {
  assert.equal(format('2026-07-15T19:30:45Z'), 'Jul 15, 2026, 01:30:45 PM MDT');
});
test('UTC midnight can fall on the previous Colorado date and year', () => {
  assert.equal(format('2026-01-01T02:00:00Z'), 'Dec 31, 2025, 07:00:00 PM MST');
});
test('spring forward skips the nonexistent local hour', () => {
  assert.equal(format('2026-03-08T08:59:59Z'), 'Mar 8, 2026, 01:59:59 AM MST');
  assert.equal(format('2026-03-08T09:00:00Z'), 'Mar 8, 2026, 03:00:00 AM MDT');
});
test('fall back distinguishes the repeated hour by its timezone', () => {
  assert.equal(format('2026-11-01T07:30:00Z'), 'Nov 1, 2026, 01:30:00 AM MDT');
  assert.equal(format('2026-11-01T08:30:00Z'), 'Nov 1, 2026, 01:30:00 AM MST');
});
test('missing, malformed and out-of-range values stay unknown', () => {
  for (const value of ['', ' ', 'bad', 'NaN', 'Infinity', '99999999999999999']) {
    assert.equal(formatTime(value), '—');
  }
});
test('an explicit Unix epoch is valid, unlike an empty value', () => {
  assert.equal(formatTime('0'), 'Dec 31, 1969, 05:00:00 PM MST');
});
