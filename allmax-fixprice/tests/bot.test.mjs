import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {createStore} from '../lib/store.mjs';
import {handleUpdate} from '../lib/bot.mjs';

function fixture(){const dir=mkdtempSync(path.join(tmpdir(),'allmaxfixprice-bot-test-'));const store=createStore(dir);store.seed();return {store,dir,cleanup(){store.db.close();rmSync(dir,{recursive:true,force:true})}};}
const telegram={token:'test-token',chatId:'12345'};
function mockFetch(calls){return async(url,opt)=>{const method=url.split('/bot')[1].split('/')[1];const body=JSON.parse(opt.body);calls.push({method,body});const result=method==='sendMessage'?{message_id:calls.length}:{};return {ok:true,json:async()=>({ok:true,result})};};}
function callbackUpdate(data,messageId=1,chatId=telegram.chatId){return {callback_query:{id:'cb'+Math.random(),data,message:{message_id:messageId,chat:{id:chatId}}}};}
function messageUpdate(text,chatId=telegram.chatId){return {message:{text,chat:{id:chatId}}};}
function order(store,variant,extra={}){return store.createOrder({requestKey:randomUUID(),customer:'Test Customer',phone:'+998901234567',address:'Toshkent, test ko‘chasi 1',items:[{variantId:variant.id,quantity:1}],...extra});}

test('/start shows the main menu only to the configured admin chat',async()=>{
 const f=fixture();try{
 const calls=[];global.fetch=mockFetch(calls);
 await handleUpdate(f.store,telegram,new Map(),messageUpdate('/start'));
 assert.equal(calls.length,1);
 assert.equal(calls[0].method,'sendMessage');
 assert(calls[0].body.text.includes('Admin menyu'));
 assert.equal(calls[0].body.reply_markup.inline_keyboard.length,3);
 calls.length=0;
 await handleUpdate(f.store,telegram,new Map(),messageUpdate('/start','99999999'));
 assert.equal(calls.length,1);
 assert.equal(calls[0].body.chat_id,'99999999');
 assert(calls[0].body.text.includes('99999999'));
 assert(!calls[0].body.text.includes('Admin menyu'));
 }finally{f.cleanup()}
});

test('orders list and detail reflect real data; status transition updates the store',async()=>{
 const f=fixture();try{
 const v=f.store.listProducts()[0].variants[0];
 const o=order(f.store,v);
 const calls=[];global.fetch=mockFetch(calls);
 const pending=new Map();
 await handleUpdate(f.store,telegram,pending,callbackUpdate('orders:0'));
 assert.equal(calls[0].method,'editMessageText');
 assert(calls[0].body.reply_markup.inline_keyboard[0][0].text.includes(o.id.slice(0,8).toUpperCase()));
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`order:${o.id}:0`));
 assert(calls[0].body.text.includes('Test Customer'));
 assert(calls[0].body.text.includes('🆕 Yangi'));
 const confirmButton=calls[0].body.reply_markup.inline_keyboard.find(r=>r[0].callback_data.startsWith('ostatus')&&r[0].callback_data.includes('confirmed'));
 assert(confirmButton,'expected a confirm transition button from new status');
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`ostatus:${o.id}:confirmed:0`));
 assert.equal(f.store.orderDetails(o.id).status,'confirmed');
 assert(calls.some(c=>c.body.text?.includes('✅ Tasdiqlangan')));
 }finally{f.cleanup()}
});

test('the original notification message is kept in sync when status changes via the bot menu',async()=>{
 const f=fixture();try{
 const v=f.store.listProducts()[0].variants[0];
 const o=order(f.store,v);
 f.store.setNotificationMessage(o.id,777);
 const calls=[];global.fetch=mockFetch(calls);
 await handleUpdate(f.store,telegram,new Map(),callbackUpdate(`ostatus:${o.id}:confirmed:0`,42));
 const notifEdit=calls.find(c=>c.method==='editMessageText'&&c.body.message_id===777);
 assert(notifEdit,'expected the stored notification message_id to be edited too');
 assert.deepEqual(notifEdit.body.reply_markup,{inline_keyboard:[]});
 }finally{f.cleanup()}
});

test('confirm/cancel callback_data (from the order notification buttons) is handled',async()=>{
 const f=fixture();try{
 const v=f.store.listProducts()[0].variants[0];
 const o=order(f.store,v);
 const calls=[];global.fetch=mockFetch(calls);
 await handleUpdate(f.store,telegram,new Map(),callbackUpdate(`cancel:${o.id}`,5));
 assert.equal(f.store.orderDetails(o.id).status,'cancelled');
 assert.equal(f.store.db.prepare('SELECT stock FROM variants WHERE id=?').get(v.id).stock,v.stock);
 }finally{f.cleanup()}
});

test('products list, detail, archive toggle, and quick price/stock edits via text replies',async()=>{
 const f=fixture();try{
 const p=f.store.listProducts()[0];
 const calls=[];global.fetch=mockFetch(calls);
 const pending=new Map();
 await handleUpdate(f.store,telegram,pending,callbackUpdate('products:0'));
 assert(calls[0].body.reply_markup.inline_keyboard[0][0].text.includes(p.name));
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`product:${p.id}:0`));
 assert(calls[0].body.text.includes('Faol'));
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`ptoggle:${p.id}:0`));
 assert.equal(f.store.listProducts(true).find(x=>x.id===p.id).active,false);
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`pprice:${p.id}:0`));
 assert.equal(pending.get(String(telegram.chatId)).type,'price');
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,messageUpdate('350000'));
 assert.equal(f.store.listProducts(true).find(x=>x.id===p.id).price,350000);
 assert(!pending.has(String(telegram.chatId)));
 const variantId=p.variants[0].id;
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,callbackUpdate(`pstock:${variantId}:${p.id}:0`));
 assert.equal(pending.get(String(telegram.chatId)).type,'stock');
 calls.length=0;
 await handleUpdate(f.store,telegram,pending,messageUpdate('5 ta'));
 assert.equal(f.store.db.prepare('SELECT stock FROM variants WHERE id=?').get(variantId).stock,5);
 }finally{f.cleanup()}
});

test('stats view reports real counts',async()=>{
 const f=fixture();try{
 const calls=[];global.fetch=mockFetch(calls);
 await handleUpdate(f.store,telegram,new Map(),callbackUpdate('stats'));
 const s=f.store.stats();
 assert(calls[0].body.text.includes(String(s.newOrders)));
 assert(calls[0].body.text.includes(String(s.activeProducts)));
 }finally{f.cleanup()}
});
