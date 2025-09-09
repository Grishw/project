// Вспомогательные парсеры времени
function parseCompactYYYYMMDDTHHMM(s) {
const m = /^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})$/.exec(String(s));
if (!m) return null;
const [, y, mo, d, h, mi] = m;
return new Date(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi));
}

// Простой парсер форматов вида %Y-%m-%d %H:%M:%S, %Y%m%dT%H%M и т.п.
function parseByFormat(input, fmt) {
if (!fmt || input == null) return null;
const s = String(input);
const map = {
    '%Y': '(?<Y>\\d{4})',
    '%m': '(?<m>\\d{2})',
    '%d': '(?<d>\\d{2})',
    '%H': '(?<H>\\d{2})',
    '%M': '(?<M>\\d{2})',
    '%S': '(?<S>\\d{2})',
};
const escapeRe = (t) => t.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
let reStr = '';
for (let i = 0; i < fmt.length; ) {
    if (fmt[i] === '%' && i + 1 < fmt.length) {
    const tok = fmt.slice(i, i + 2);
    if (map[tok]) { reStr += map[tok]; i += 2; continue; }
    }
    reStr += escapeRe(fmt[i]);
    i += 1;
}
const re = new RegExp('^' + reStr + '$');
const m = re.exec(s);
if (!m || !m.groups) return null;
const Y = Number(m.groups.Y ?? '1970');
const mo = Number(m.groups.m ?? '1');
const d = Number(m.groups.d ?? '1');
const H = Number(m.groups.H ?? '0');
const M = Number(m.groups.M ?? '0');
const S = Number(m.groups.S ?? '0');
return new Date(Y, (mo || 1) - 1, d || 1, H || 0, M || 0, S || 0);
}

export default {parseCompactYYYYMMDDTHHMM, parseByFormat};