/** LOCAL PATCH (persona): /persona 命令，本会话切换 dsh-persona-dafeiyu 人设。 */
const PERSONA_API_BASE = 'http://127.0.0.1:3080/api/dsh-persona-dafeiyu';
async function personaApi(path, init) {
    const response = await fetch(PERSONA_API_BASE + path, init);
    return await response.json();
}
function personaMutate(body) {
    return personaApi('/mutate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
async function handlePersonaCommand(ctx, chatId, arg) {
    const sessionId = ctx.getChat(chatId)?.sessionId ?? await ctx.sessionIdFromMapping(chatId);
    if (sessionId === undefined) {
        await ctx.sendToChat(chatId, '还没有会话，先发一条消息再切人设。');
        return;
    }
    let status;
    try {
        status = await personaApi('/status');
    }
    catch (error) {
        await ctx.sendToChat(chatId, '人设服务没响应：' + describeError(error));
        return;
    }
    const value = status?.value ?? {};
    const list = Array.isArray(value.personas) ? value.personas : [];
    const text = (arg ?? '').trim();
    if (text === '') {
        const lines = list.map((persona, index) => `${persona.id === value.current ? '★' : ' '} ${index + 1}. ${persona.name}${persona.enabled ? '' : '（停用）'}`).join('\n');
        await ctx.sendToChat(chatId, `全局：${value.currentName ?? '?'}\n本会话：${value.sessionPersona?.name ?? '跟随全局'}\n\n${lines}\n\n用法：/persona 1 或 /persona 名字；/persona global 跟随全局`);
        return;
    }
    if (text === 'global') {
        await personaMutate({ action: 'set-mode', mode: 'session' });
        const cleared = await personaMutate({ action: 'set-session-persona', sessionId, personaId: null });
        await ctx.sendToChat(chatId, cleared?.ok ? `✅ 本会话已跟随全局：${value.currentName ?? ''}` : '切换失败：' + (cleared?.error ?? '未知错误'));
        return;
    }
    const prefix = (name) => name === text || name.startsWith(text + ' ') || name.startsWith(text + '.') || name.startsWith(text + '、');
    let target = list.find((persona) => prefix(persona.name));
    if (target === undefined)
        target = list.find((persona) => persona.name.includes(text));
    if (target === undefined && /^\d+$/.test(text))
        target = list[Number(text) - 1];
    if (target === undefined) {
        await ctx.sendToChat(chatId, '没找到这个人设：' + text);
        return;
    }
    await personaMutate({ action: 'set-mode', mode: 'session' });
    const result = await personaMutate({ action: 'set-session-persona', sessionId, personaId: target.id });
    await ctx.sendToChat(chatId, result?.ok ? `✅ 本会话已切到：${target.name}` : '切换失败：' + (result?.error ?? '未知错误'));
}
