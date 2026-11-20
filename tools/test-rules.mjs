// ランキングのルールが本当に効くかを、GitHub の上で確かめる（試しの記録は最後に消す）
import { token, api, DBURL } from './fb.mjs';
const KEY = 'AIzaSyAcJgJLVbuvx85_qEGJe1WhwsOelidxeYk';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const j = await (await fetch('https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=' + KEY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ returnSecureToken: true }) })).json();
if (!j.localId) { console.log('名前なしのログインができません', JSON.stringify(j).slice(0, 200)); process.exit(1); }
const uid = j.localId, tk = j.idToken, U = p => DBURL + '/kubi/' + p + '.json?auth=' + encodeURIComponent(tk);
const put = async (p, b) => { const r = await fetch(U(p), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }); return { ok: r.ok, body: await r.text() }; };
const TS = { '.sv': 'timestamp' }, dk = Math.floor((Date.now() + 32400000) / 86400000);
const out = []; let bad = 0; const want = (name, got, exp) => { out.push((got === exp ? '○ ' : '× ') + name + '（' + (got ? '通った' : 'はじかれた') + '）'); if (got !== exp) bad++; };
const run = await put('run/' + uid, { st: TS }); want('始まりの時刻を書く', run.ok, true); const st = JSON.parse(run.body).st;
const rec = t => ({ n: 'てすと', t, sk: t, st, v: 1, at: TS }), recD = t => ({ ...rec(t), dk, ds: dk * 100000 + t });
want('始めてすぐの記録', (await put('b/all/' + uid, rec(2134))).ok, false);
await sleep(2200);
want('ふつうの記録 0.2134秒（全期間）', (await put('b/all/' + uid, rec(2134))).ok, true);
want('ふつうの記録 0.2134秒（今日）', (await put('b/d/' + uid, recD(2134))).ok, true);
want('おそい記録で上書き', (await put('b/all/' + uid, rec(3000))).ok, false);
want('はやい記録で上書き', (await put('b/all/' + uid, rec(1500))).ok, true);
want('人間を超えた 0.0082秒', (await put('b/all/' + uid, rec(82))).ok, true);
want('0秒', (await put('b/all/' + uid, rec(0))).ok, false);
want('小数の記録', (await put('b/all/' + uid, rec(12.5))).ok, false);
want('1.5秒より長い記録（今日）', (await put('b/d/' + uid, recD(20000))).ok, false);
want('ちがう始まりの時刻', (await put('b/d/' + uid, { ...recD(1000), st: st - 5000 })).ok, false);
want('長すぎる名前', (await put('b/d/' + uid, { ...recD(1000), n: 'あいうえおかきくけこさしす' })).ok, false);
const a = await (await fetch(DBURL + '/kubi/b/all.json?orderBy="sk"&limitToFirst=100')).json(); want('全期間のランキングを読む', !!(a && a[uid] && a[uid].sk === 82), true);
const base = dk * 100000, d = await (await fetch(DBURL + `/kubi/b/d.json?orderBy="ds"&startAt=${base}&endAt=${base + 99999}&limitToFirst=100`)).json(); want('今日のランキングを読む', !!(d && d[uid] && d[uid].sk === 2134), true);
// 試しの記録を消す
const adm = await token(); for (const p of ['b/all/', 'b/d/', 'run/']) await api('DELETE', '/kubi/' + p + uid + '.json', undefined, adm);
await fetch('https://identitytoolkit.googleapis.com/v1/accounts:delete?key=' + KEY, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idToken: tk }) }).catch(() => { });
const left = await (await fetch(DBURL + '/kubi/b/all/' + uid + '.json')).json(); want('試しの記録を消した', left === null, true);
console.log(out.join('\n')); console.log(bad ? '× ' + bad + '個 合いません' : '○ ぜんぶ合いました'); if (bad) process.exit(1);
