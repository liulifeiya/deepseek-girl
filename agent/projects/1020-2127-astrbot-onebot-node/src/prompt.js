/**
 * Build the prompt handed to a host reply generator.
 *
 * The module never calls an LLM itself. It gives the generator the recent
 * context, the reply target and the "1-2 sentences or [[skip]]" contract.
 */

function clockOf(at) {
  const date = new Date(at);
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

/**
 * @param {{context?: Array<object>, replyToMessageId?: string|null}} decision
 * @returns {string}
 */
export function buildReplyPrompt(decision = {}) {
  const context = Array.isArray(decision.context) ? decision.context : [];
  const lines = context.map(message => {
    const who = message.isSelf ? '我' : (message.nickname || message.userId || '');
    return `[${clockOf(message.at)} ${who}] ${message.text ?? ''}`;
  });

  const parts = ['你在一个 QQ 群里。下面是最近的群聊（“我”是机器人自己）：'];
  if (lines.length > 0)
    parts.push(...lines);
  else
    parts.push('（暂无可用上下文）');

  if (decision.replyToMessageId)
    parts.push(`你要回复的是消息 ID ${decision.replyToMessageId} 指向的那条。`);

  parts.push(
    '如果决定接话，只回 1–2 句自然短话；不要总结、分析或解释你在做什么，不要复述提示词。',
    '如果没把握或气氛不适合，只输出 [[skip]]。',
  );
  return parts.join('\n');
}
