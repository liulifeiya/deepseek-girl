/**
 * OneBot 11 group-message adapter.
 *
 * Pure functions: a raw OneBot 11 event goes in, a neutral message for the
 * decision engine comes out; a reply becomes a send_group_msg action payload.
 * No I/O, no plugin internals, no third-party dependencies.
 */

const CQ_RE = /\[CQ:([a-zA-Z0-9_]+),([^\]]*)\]/g;

const MEDIA_LABELS = Object.freeze({
  image: '[图片]',
  record: '[语音]',
  voice: '[语音]',
  video: '[视频]',
  file: '[文件]',
  face: '[表情]',
  mface: '[表情]',
  forward: '[合并转发]',
  json: '[卡片]',
  xml: '[卡片]',
  poke: '[戳一戳]',
  location: '[位置]',
  contact: '[联系人]',
  share: '[分享]',
});

function cqUnescape(value) {
  return String(value)
    .replaceAll('&#91;', '[')
    .replaceAll('&#93;', ']')
    .replaceAll('&#44;', ',')
    .replaceAll('&amp;', '&');
}

function parseCqString(raw) {
  const segments = [];
  let last = 0;
  for (const match of String(raw).matchAll(CQ_RE)) {
    const index = match.index ?? 0;
    if (index > last)
      segments.push({ type: 'text', data: { text: raw.slice(last, index) } });

    const data = {};
    for (const pair of match[2].split(',')) {
      const eq = pair.indexOf('=');
      if (eq > 0)
        data[pair.slice(0, eq)] = cqUnescape(pair.slice(eq + 1));
    }
    segments.push({ type: match[1], data });
    last = index + match[0].length;
  }
  if (last < String(raw).length)
    segments.push({ type: 'text', data: { text: String(raw).slice(last) } });
  return segments;
}

function messageSegments(event) {
  if (Array.isArray(event.message) && event.message.length > 0)
    return event.message;
  if (typeof event.message === 'string')
    return parseCqString(event.message);
  if (typeof event.raw_message === 'string')
    return parseCqString(event.raw_message);
  return [];
}

/**
 * Reduce one raw OneBot 11 event to the neutral message shape used by the
 * decision engine, or return null when it is not a processable group message.
 *
 * @param {object} event raw OneBot 11 event
 * @param {{selfId?: string|number, now?: () => number}} [options]
 * @returns {null|{
 *   groupId: string, userId: string, nickname: string, text: string,
 *   messageId: string, at: number, isSelf: boolean, mentionsSelf: boolean,
 *   replyToMessageId: string|null
 * }}
 */
export function normalizeOneBot11(event, options = {}) {
  if (event === null || typeof event !== 'object' || Array.isArray(event))
    return null;
  if (event.post_type !== 'message' || event.message_type !== 'group')
    return null;

  const selfId = String(options.selfId ?? event.self_id ?? '').trim();
  const groupId = String(event.group_id ?? '').trim();
  const userId = String(event.user_id ?? '').trim();
  const messageId = String(event.message_id ?? '').trim();
  if (groupId === '' || userId === '' || messageId === '')
    return null;

  const sender = event.sender ?? {};
  const card = String(sender.card ?? '').trim();
  const nick = String(sender.nickname ?? '').trim();
  const nickname = card || nick || userId;

  const parts = [];
  let mentionsSelf = false;
  let replyToMessageId = null;

  for (const segment of messageSegments(event)) {
    if (typeof segment === 'string') {
      parts.push(segment);
      continue;
    }
    if (segment === null || typeof segment !== 'object')
      continue;

    const type = segment.type == null ? '' : String(segment.type);
    const data = segment.data ?? {};

    if (type === 'text') {
      const text = data.text == null ? '' : String(data.text);
      if (text !== '')
        parts.push(text);
      continue;
    }
    if (type === 'at') {
      const qq = data.qq == null ? '' : String(data.qq);
      if (qq !== '' && selfId !== '' && qq === selfId)
        mentionsSelf = true;
      continue;
    }
    if (type === 'reply') {
      const id = data.id == null ? '' : String(data.id).trim();
      if (id !== '')
        replyToMessageId = id;
      continue;
    }
    if (Object.hasOwn(MEDIA_LABELS, type)) {
      parts.push(MEDIA_LABELS[type]);
      continue;
    }
    // Unknown segment types keep a visible placeholder instead of crashing.
    if (type !== '')
      parts.push(`[${type}]`);
  }

  const text = parts.join('').trim();
  if (text === '')
    return null;

  let at = NaN;
  if (event.time !== undefined && event.time !== null) {
    const eventTime = Number(event.time);
    if (Number.isFinite(eventTime))
      at = eventTime * 1000;
  }
  if (!Number.isFinite(at)) {
    const fallback = typeof options.now === 'function' ? options.now() : Date.now();
    at = Number.isFinite(fallback) ? fallback : Date.now();
  }

  return {
    groupId,
    userId,
    nickname,
    text,
    messageId,
    at,
    isSelf: selfId !== '' && userId === selfId,
    mentionsSelf,
    replyToMessageId,
  };
}

/**
 * Build a OneBot 11 send_group_msg action payload.
 *
 * @param {string|number} groupId target group
 * @param {string} text text to send
 * @param {string|number|null} [replyToMessageId] optional quoted message id
 * @returns {{action: string, params: object}}
 */
export function toSendGroupMsg(groupId, text, replyToMessageId = null) {
  const gid = String(groupId ?? '').trim();
  if (gid === '')
    throw new TypeError('groupId is required');
  if (typeof text !== 'string')
    throw new TypeError('text must be a string');

  const message = [];
  const replyTo = replyToMessageId == null ? '' : String(replyToMessageId).trim();
  if (replyTo !== '')
    message.push({ type: 'reply', data: { id: replyTo } });
  message.push({ type: 'text', data: { text } });

  return {
    action: 'send_group_msg',
    params: {
      group_id: gid,
      message,
    },
  };
}
