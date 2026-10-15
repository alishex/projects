import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import path from 'node:path';
import {tmpdir} from 'node:os';
import net from 'node:net';
import {randomUUID} from 'node:crypto';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
test('HTTP purchase, tracking, admin access, CSRF, product edit and durable upload',async()=>{
 const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
 const origin=`http://127.0.0.1:${port}`,dir=mkdtempSync(path.join(tmpdir(),'allmaxfixprice-http-'));
 const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:String(port),HOST:'127.0.0.1',PUBLIC_URL:origin,DATA_DIR:dir,ADMIN_EMAIL:'qa@example.test',ADMIN_PASSWORD:'Test-Password-Strong-2026',TELEGRAM_BOT_TOKEN:'',TELEGRAM_CHAT_ID:''},stdio:'pipe'});
 let log='';child.stderr.on('data',d=>log+=d);
 try{
 let live=false;for(let i=0;i<80;i++){try{const r=await fetch(origin+'/api/health');if(r.ok){live=true;break}}catch{}await delay(50)}assert(live,log);
 const request=(route,body,cookie='',customOrigin=origin)=>fetch(origin+route,{method:body===undefined?'GET':'POST',headers:{Origin:customOrigin,'Content-Type':'application/json',Cookie:cookie},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 const home=await request('/');assert.equal(home.status,200);assert((await home.text()).includes('ALLMAX Fix Price'));assert(home.headers.get('content-security-policy').includes("frame-ancestors 'self' https://*.telegram.org"));
 assert.equal((await request('/api/admin/data')).status,401);
 assert.equal((await request('/api/orders',{},'','https://wrong.example')).status,403);
 const {products}=await(await request('/api/products')).json();assert.equal(products.length,15);
 const p=products[0],v=p.variants[0],body={requestKey:randomUUID(),customer:'QA Example',phone:'+998901234567',address:'QA test address',items:[{variantId:v.id,quantity:1,price:1}]};
 let r=await request('/api/orders',body);assert.equal(r.status,201);const order=await r.json();
 r=await request('/api/orders',body);assert.equal(r.status,200);assert.equal((await r.json()).id,order.id);
 const tracked=await(await request('/api/track',{token:order.token})).json();assert.equal(tracked.total,p.price);assert.equal(tracked.customer,undefined);assert.equal(tracked.phone,undefined);
 assert.equal((await request('/api/track',{token:'x'.repeat(43)})).status,404);
 r=await request('/api/admin/login',{email:'qa@example.test',password:'Test-Password-Strong-2026'});assert.equal(r.status,200);assert(r.headers.get('set-cookie').includes('HttpOnly'));const cookie=r.headers.get('set-cookie').split(';')[0];
 const data=await(await request('/api/admin/data',undefined,cookie)).json();assert.equal(data.orders.length,1);assert.equal(data.orders[0].tracking_token,undefined);
 r=await request('/api/admin/status',{id:order.id,status:'cancelled'},cookie);assert.equal(r.status,200);
 const product=structuredClone(p);product.price+=10000;r=await request('/api/admin/products',product,cookie);assert.equal(r.status,200);assert.equal((await r.json()).product.premium,p.premium);
 assert.equal((await request('/api/admin/upload',{data:'data:image/png;base64,'+Buffer.from('<script>bad</script>').toString('base64')},cookie)).status,400);
 const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZlN4AAAAASUVORK5CYII=';
 r=await request('/api/admin/upload',{data:'data:image/png;base64,'+png},cookie);assert.equal(r.status,201);const uploaded=await r.json();assert.equal((await request(uploaded.url)).status,200);
 await request('/api/admin/logout',{},cookie);assert.equal((await request('/api/admin/data',undefined,cookie)).status,401);
 }finally{child.kill('SIGTERM');await new Promise(resolve=>{child.once('exit',resolve);setTimeout(resolve,2000).unref()});rmSync(dir,{recursive:true,force:true})}
});
