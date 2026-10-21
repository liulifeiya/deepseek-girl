#!/usr/bin/env node
/**
 * T1 MVP demo: scripted group messages, deterministic clock, no network.
 *
 * Run from the project root:
 *   node examples/demo.js
 */

import { createAutoChat } from '../src/engine.js';

const GROUP = '100';
const START = Date.parse('2026-10-20T12:00:00Z');
let now = START;
let nextId = 0;

const engine = createAutoChat({
  interestKeywords: ['AI', '游戏', '电影'],
  cooldownMs: 3 * 60 * 1000,
  activeWindowMs: 5 * 60 * 1000,
  now: () => now,
});

function clock() {
  return new Date(now).toISOString().slice(11, 16);
}

function printDecision(label, decision) {
  const replyTo = decision.replyToMessageId ?? '-';
  console.log(
    `  ${label}: ${decision.action}/${decision.reason} ` +
    `score=${decision.score.toFixed(2)} replyTo=${replyTo} ` +
    `context=${decision.context.length}`,
  );
}

function say(userId, nickname, text, extra = {}) {
  const { delayMs = 0, ...fields } = extra;
  now += delayMs;
  const messageId = `m${++nextId}`;
  const accepted = engine.observe({
    groupId: GROUP,
    userId,
    nickname,
    text,
    messageId,
    at: now,
    ...fields,
  });
  const decision = engine.decide(GROUP);
  console.log(`\n${clock()} ${nickname}: ${text}`);
  console.log(`  accepted=${accepted}`);
  printDecision('decision', decision);
  return decision;
}

console.log('== group-autochat T1 MVP demo ==');
console.log(`group=${GROUP} start=${new Date(START).toISOString()}`);

say('alice', 'Alice', '今天天气不错');
const relevant = say('bob', 'Bob', '有人玩这个 AI 游戏吗？', { delayMs: 10_000 });
engine.recordReply(GROUP);

say('alice', 'Alice', '我也在玩', { delayMs: 10_000 });

now += 4 * 60 * 1000;
const afterCooldown = say('bob', 'Bob', '这个游戏剧情怎么样？');
engine.recordReply(GROUP);

now += 6 * 60 * 1000;
console.log('\n(6 分钟没有新消息，再询问决策)');
printDecision('cold check', engine.decide(GROUP));

say('alice', 'Alice', '@bot 在吗', { mentionsSelf: true });

const empty = engine.decide('999');
console.log('\n(空群 999)');
printDecision('empty check', empty);

const summary = [
  ['relevant reply', relevant],
  ['after cooldown', afterCooldown],
  ['empty', empty],
];
console.log('\n== demo summary ==');
for (const [name, decision] of summary)
  console.log(`${name}: ${decision.action}/${decision.reason}`);
