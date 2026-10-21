#!/usr/bin/env node
/**
 * T2 smoke demo: normalize four handwritten OneBot 11 events and build a send
 * payload. No network, no QQ, no plugin files touched.
 *
 *   node examples/onebot-demo.js
 */

import { normalizeOneBot11, toSendGroupMsg } from '../src/onebot.js';

const SELF_ID = '10001';
const BASE = {
  post_type: 'message',
  message_type: 'group',
  self_id: 10001,
  group_id: 123,
  user_id: 456,
  time: 1700000000,
  sender: { card: '小明', nickname: 'ming' },
};

const events = [
  {
    ...BASE,
    message_id: 9001,
    message: [
      { type: 'text', data: { text: '大家 ' } },
      { type: 'at', data: { qq: '10001' } },
      { type: 'text', data: { text: ' 怎么看？' } },
    ],
    raw_message: '大家 [CQ:at,qq=10001] 怎么看？',
  },
  {
    ...BASE,
    message_id: 9002,
    message: [
      { type: 'reply', data: { id: '700' } },
      { type: 'text', data: { text: '这张图' } },
      { type: 'image', data: { file: 'a.jpg' } },
    ],
    raw_message: '[CQ:reply,id=700]这张图[CQ:image,file=a.jpg]',
  },
  {
    ...BASE,
    message_id: 9003,
    message_type: 'private',
    message: [{ type: 'text', data: { text: '私聊不应进入群决策' } }],
  },
  {
    ...BASE,
    message_id: 9004,
    user_id: 789,
    message: undefined,
    raw_message: '[CQ:at,qq=10001] hi [CQ:image,file=a.jpg] [CQ:reply,id=701]',
  },
];

console.log('== OneBot 11 normalization demo ==');
for (const event of events) {
  const normalized = normalizeOneBot11(event, { selfId: SELF_ID, now: () => 1700000000000 });
  console.log('\nraw event', event.message_id, '=>');
  console.log(normalized === null ? 'null (ignored)' : JSON.stringify(normalized, null, 2));
}

const second = normalizeOneBot11(events[1], { selfId: SELF_ID });
console.log('\n== send_group_msg payload ==');
console.log(JSON.stringify(toSendGroupMsg(second.groupId, '收到，展开说说', second.messageId), null, 2));
