#!/usr/bin/env node
/**
 * CLI entry for the HTTP sidecar.
 *
 * Environment:
 *   AUTOCHAT_HOST / AUTOCHAT_PORT
 *   AUTOCHAT_WEBHOOK_TOKEN
 *   ONEBOT_API_BASE / ONEBOT_ACCESS_TOKEN / ONEBOT_SELF_ID
 *   AUTOCHAT_DRY_RUN
 *   AUTOCHAT_REPLY_MODULE  path to a module exporting generateReply(...)
 *   AUTOCHAT_CONFIG        optional JSON file with createAutoChat options
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createAutoChat } from './engine.js';
import { createSidecar } from './server.js';

function fail(message, code = 1) {
  console.error(`group-autochat: ${message}`);
  process.exit(code);
}

function envFlag(name) {
  const value = String(process.env[name] ?? '').toLowerCase();
  return value === '1' || value === 'true' || value === 'yes' || value === 'on';
}

let config = {};
if (process.env.AUTOCHAT_CONFIG) {
  try {
    const path = resolve(process.env.AUTOCHAT_CONFIG);
    config = JSON.parse(readFileSync(path, 'utf8'));
  }
  catch (error) {
    fail(`cannot read AUTOCHAT_CONFIG: ${error.message}`, 2);
  }
  if (config === null || typeof config !== 'object' || Array.isArray(config))
    fail('AUTOCHAT_CONFIG must contain a JSON object', 2);
  // JSON cannot carry a function; never let a config file shadow the clock.
  delete config.now;
}

let engine;
try {
  engine = createAutoChat(config);
}
catch (error) {
  fail(`invalid engine config: ${error.message}`, 2);
}

let replyGenerator = null;
if (process.env.AUTOCHAT_REPLY_MODULE) {
  try {
    const modulePath = resolve(process.env.AUTOCHAT_REPLY_MODULE);
    const module = await import(pathToFileURL(modulePath).href);
    replyGenerator = typeof module.generateReply === 'function'
      ? module.generateReply
      : typeof module.default === 'function'
        ? module.default
        : null;
    if (replyGenerator === null)
      fail('AUTOCHAT_REPLY_MODULE must export generateReply()', 2);
  }
  catch (error) {
    fail(`cannot load AUTOCHAT_REPLY_MODULE: ${error.message}`, 2);
  }
}

const dryRun = envFlag('AUTOCHAT_DRY_RUN') || replyGenerator === null;
const apiBase = String(process.env.ONEBOT_API_BASE ?? '').trim();
if (!dryRun) {
  if (apiBase === '')
    fail('ONEBOT_API_BASE is required unless dry-run', 2);
  try {
    new URL(apiBase);
  }
  catch {
    fail('ONEBOT_API_BASE must be a valid URL', 2);
  }
}

const rawPort = process.env.AUTOCHAT_PORT;
const port = rawPort === undefined || rawPort === '' ? 8787 : Number(rawPort);
if (!Number.isInteger(port) || port < 0 || port > 65535)
  fail('AUTOCHAT_PORT must be an integer between 0 and 65535', 2);

const sidecar = createSidecar({
  engine,
  apiBase,
  accessToken: process.env.ONEBOT_ACCESS_TOKEN ?? '',
  webhookToken: process.env.AUTOCHAT_WEBHOOK_TOKEN ?? '',
  replyGenerator,
  dryRun,
  host: process.env.AUTOCHAT_HOST ?? '127.0.0.1',
  port,
  selfId: process.env.ONEBOT_SELF_ID ?? '',
});

let address;
try {
  address = await sidecar.start();
}
catch (error) {
  fail(`cannot start sidecar: ${error.message}`, 1);
}

console.log(JSON.stringify({
  ts: new Date().toISOString(),
  event: 'started',
  host: address.address,
  port: address.port,
  dryRun,
}));
if (dryRun)
  console.log(JSON.stringify({ ts: new Date().toISOString(), event: 'dry-run' }));

let stopping = false;
async function shutdown(signal) {
  if (stopping)
    return;
  stopping = true;
  console.log(JSON.stringify({ ts: new Date().toISOString(), event: 'stopping', signal }));
  await sidecar.stop();
  process.exit(0);
}

process.on('SIGINT', () => { void shutdown('SIGINT'); });
process.on('SIGTERM', () => { void shutdown('SIGTERM'); });
