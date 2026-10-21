import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeOneBot11, toSendGroupMsg } from '../src/onebot.js';

const BASE = {
  post_type: 'message',
  message_type: 'group',
  self_id: 10001,
  group_id: 123,
  user_id: 456,
  message_id: 9001,
  time: 1700000000,
  sender: { card: '小明', nickname: 'ming' },
};

test('AC-12 normalizes group text, @self, reply, and media placeholders', () => {
  const message = normalizeOneBot11({
    ...BASE,
    message: [
      { type: 'text', data: { text: 'hi ' } },
      { type: 'at', data: { qq: '10001' } },
      { type: 'text', data: { text: ' there' } },
      { type: 'reply', data: { id: 77 } },
      { type: 'image', data: { file: 'x.jpg' } },
      { type: 'record', data: { file: 'v.amr' } },
    ],
  }, { selfId: '10001' });

  assert.equal(message.groupId, '123');
  assert.equal(message.userId, '456');
  assert.equal(message.nickname, '小明');
  assert.equal(message.messageId, '9001');
  assert.equal(message.text, 'hi  there[图片][语音]');
  assert.equal(message.mentionsSelf, true);
  assert.equal(message.replyToMessageId, '77');
  assert.equal(message.at, 1700000000000);
  assert.equal(message.isSelf, false);
});

test('AC-12 ignores private, non-message, incomplete, and pure-@ events', () => {
  assert.equal(normalizeOneBot11({ ...BASE, message_type: 'private', message: [] }), null);
  assert.equal(normalizeOneBot11({ ...BASE, post_type: 'notice', message: [] }), null);
  assert.equal(normalizeOneBot11({
    ...BASE,
    message_id: undefined,
    message: [{ type: 'text', data: { text: 'x' } }],
  }), null);
  assert.equal(normalizeOneBot11({
    ...BASE,
    message: [{ type: 'at', data: { qq: '10001' } }],
  }), null);
});

test('AC-12 handles self, nickname fallback, and timestamp fallback', () => {
  const self = normalizeOneBot11({
    ...BASE,
    user_id: 10001,
    sender: {},
    message: [{ type: 'text', data: { text: '我' } }],
  }, { selfId: '10001' });
  assert.equal(self.isSelf, true);
  assert.equal(self.nickname, '10001');

  const fallback = normalizeOneBot11({
    ...BASE,
    time: null,
    message: [{ type: 'text', data: { text: 'x' } }],
  }, { now: () => 123456 });
  assert.equal(fallback.at, 123456);
});

test('AC-12 parses CQ raw fallback and does not treat @all as self', () => {
  const message = normalizeOneBot11({
    ...BASE,
    message: undefined,
    raw_message: '[CQ:at,qq=10001]hello[CQ:reply,id=88][CQ:image,file=a.jpg]',
  });
  assert.equal(message.text, 'hello[图片]');
  assert.equal(message.mentionsSelf, true);
  assert.equal(message.replyToMessageId, '88');

  const all = normalizeOneBot11({
    ...BASE,
    message: [
      { type: 'at', data: { qq: 'all' } },
      { type: 'text', data: { text: '全体成员' } },
    ],
  }, { selfId: '10001' });
  assert.equal(all.mentionsSelf, false);
});

test('AC-13 builds send_group_msg with optional reply segment', () => {
  const withReply = toSendGroupMsg(123, '收到', 77);
  assert.deepEqual(withReply, {
    action: 'send_group_msg',
    params: {
      group_id: '123',
      message: [
        { type: 'reply', data: { id: '77' } },
        { type: 'text', data: { text: '收到' } },
      ],
    },
  });

  const plain = toSendGroupMsg('123', '收到');
  assert.deepEqual(plain.params.message, [{ type: 'text', data: { text: '收到' } }]);
  assert.throws(() => toSendGroupMsg('', 'x'), TypeError);
  assert.throws(() => toSendGroupMsg('1', null), TypeError);
});
