import http from 'node:http';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import { randomUUID, randomBytes } from 'node:crypto';
import { createStore,AppError,hash } from './lib/store.mjs';
import { sendNext, reflectStatus, setWebhook } from './lib/telegram.mjs';
import { handleUpdate } from './lib/bot.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
try{process.loadEnvFile(path.join(root,'.env'))}catch(e){if(e.code!=='ENOENT')throw e}
const brand=JSON.parse(fs.readFileSync(path.join(root,'public/brand.json'),'utf8'));
const port=Number(process.env.PORT||3000),host=process.env.HOST||'127.0.0.1';
const publicUrl=(process.env.PUBLIC_URL||`http://localhost:${port}`).replace(/\/$/,'');
const origin=new URL(publicUrl).origin,secure=process.env.COOKIE_SECURE==='true';
const directory=process.env.DATA_DIR||path.join(root,'data');
const store=createStore(directory);store.seed();fs.mkdirSync(path.join(directory,'uploads'),{recursive:true});
const generated=store.ensureAdmin(process.env.ADMIN_EMAIL||'admin@intimshop.local',process.env.ADMIN_PASSWORD||'');
const webhookSecret=randomBytes(24).toString('base64url');
const pendingInputs=new Map();
const telegram={token:process.env.TELEGRAM_BOT_TOKEN,chatId:process.env.TELEGRAM_CHAT_ID,publicUrl,brandName:brand.name};
const configured=!!(telegram.token&&telegram.chatId);
const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
function cookies(req){const raw=req.headers.cookie||'';return Object.fromEntries(raw.split(';').map(c=>{const i=c.indexOf('=');return i<0?['','']:[c.slice(0,i).trim(),c.slice(i+1)]}));}
function readBody(req,limit=25000){return new Promise((resolve,reject)=>{if(!String(req.headers['content-type']||'').startsWith('application/json')){reject(new AppError('JSON so‘rov talab qilinadi.',415));req.resume();return;}let size=0,chunks=[],tooLarge=false;req.on('data',chunk=>{size+=chunk.length;if(size>limit){tooLarge=true;chunks=[];}else if(!tooLarge)chunks.push(chunk)});req.on('end',()=>{if(tooLarge)return reject(new AppError('So‘rov juda katta.',413));try{resolve(JSON.parse(Buffer.concat(chunks).toString()))}catch{reject(new AppError('JSON noto‘g‘ri.'))}});req.on('error',reject);});}
function requireAdmin(req){const a=store.admin(cookies(req).session);if(!a)throw new AppError('Administrator sifatida kiring.',401);return a;}
function limiter(req,prefix,max,ms){const ip=process.env.TRUST_PROXY==='true'?String(req.headers['x-forwarded-for']||req.socket.remoteAddress).split(',')[0].trim():req.socket.remoteAddress;if(!store.rateLimit(hash(prefix+':'+ip),max,ms))throw new AppError('Ko‘p urinish bo‘ldi. Birozdan keyin qayta urinib ko‘ring.',429);}
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.woff2':'font/woff2','.ico':'image/x-icon'};
async function applyStatus(id,next){store.status(id,next);const messageId=store.notificationMessage(id);if(messageId)await reflectStatus(store,telegram,id,messageId,next).catch(()=>{});}
const server=http.createServer(async(req,res)=>{
 res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('Permissions-Policy','camera=(), microphone=(), geolocation=(self)');res.setHeader('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self' https://*.telegram.org; form-action 'self'");
 try{
 const url=new URL(req.url,publicUrl),route=url.pathname;
 if(route==='/api/telegram/webhook'&&req.method==='POST'){
 if(req.headers['x-telegram-bot-api-secret-token']!==webhookSecret)throw new AppError('Ruxsat yo‘q.',403);
 const update=await readBody(req,50000);
 handleUpdate(store,telegram,pendingInputs,update).catch(e=>console.error('Telegram update failed:',e.message));
 return json(res,{ok:true});
 }
 if(['POST','PUT','PATCH','DELETE'].includes(req.method)&&req.headers.origin!==origin)throw new AppError('So‘rov manbasi ruxsat etilmagan. PUBLIC_URL ni tekshiring.',403);
 if(route==='/api/health'&&req.method==='GET')return json(res,{ok:true});
 if(route==='/api/products'&&req.method==='GET')return json(res,{products:store.listProducts(),demo:process.env.DEMO_MODE!=='false',telegram:configured});
 if(route==='/api/orders'&&req.method==='POST'){limiter(req,'order',20,3600000);const order=store.createOrder(await readBody(req));return json(res,{...order,telegram:configured?'pending':'unconfigured'},order.duplicate?200:201);}
 if(route==='/api/track'&&req.method==='POST'){limiter(req,'track',60,60000);const {token}=await readBody(req);if(typeof token!=='string'||token.length!==43)throw new AppError('Kuzatish kodi noto‘g‘ri.',404);const found=store.db.prepare('SELECT id FROM orders WHERE tracking_token=?').get(token);if(!found)throw new AppError('Buyurtma topilmadi.',404);const o=store.orderDetails(found.id);return json(res,{id:o.id,created_at:o.created_at,total:o.total,status:o.status,items:o.items.map(({name,size,color,quantity,price})=>({name,size,color,quantity,price})),telegram:configured?o.notification.status:'unconfigured'});}
 if(route==='/api/admin/login'&&req.method==='POST'){limiter(req,'login',8,900000);const body=await readBody(req);if(typeof body.email!=='string'||body.email.length>150||typeof body.password!=='string'||body.password.length>200)throw new AppError('Kirish ma’lumotlari noto‘g‘ri.',401);const token=store.login(body.email,body.password);if(!token)throw new AppError('Email yoki parol noto‘g‘ri.',401);res.setHeader('Set-Cookie',`session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400${secure?'; Secure':''}`);return json(res,{ok:true});}
 if(route==='/api/admin/logout'&&req.method==='POST'){store.db.prepare('DELETE FROM sessions WHERE hash=?').run(hash(cookies(req).session||''));res.setHeader('Set-Cookie','session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0');return json(res,{ok:true});}
 if(route.startsWith('/api/admin/')){
 const admin=requireAdmin(req);
 if(route==='/api/admin/data'&&req.method==='GET'){const orders=store.db.prepare('SELECT id FROM orders ORDER BY created_at DESC LIMIT 500').all().map(o=>{const d=store.orderDetails(o.id);delete d.tracking_token;delete d.request_key;delete d.payload_hash;return d});return json(res,{admin,products:store.listProducts(true),orders,telegram:configured,demo:process.env.DEMO_MODE!=='false'});}
 if(route==='/api/admin/products'&&req.method==='POST')return json(res,{product:store.saveProduct(await readBody(req))});
 if(route==='/api/admin/status'&&req.method==='POST'){const {id,status}=await readBody(req);if(typeof id!=='string'||typeof status!=='string')throw new AppError('Holat noto‘g‘ri.');await applyStatus(id,status);return json(res,{ok:true});}
 if(route==='/api/admin/retry'&&req.method==='POST'){const {id}=await readBody(req);if(typeof id!=='string')throw new AppError('Buyurtma noto‘g‘ri.');if(!configured)throw new AppError('Avval Telegram botni sozlang.');const changes=store.db.prepare("UPDATE notifications SET status='pending',attempts=0,next_at=0,error='' WHERE order_id=? AND status='failed'").run(id).changes;if(!changes)throw new AppError('Faqat xato bilan tugagan xabarni qayta yuborish mumkin.',409);return json(res,{ok:true});}
 if(route==='/api/admin/upload'&&req.method==='POST'){const {data}=await readBody(req,8000000);if(typeof data!=='string'||!/^data:image\/(png|jpeg|webp);base64,/.test(data))throw new AppError('PNG, JPEG yoki WebP yuklang.');const buffer=Buffer.from(data.split(',')[1],'base64');if(buffer.length>5*1024*1024||buffer.length<20)throw new AppError('Rasm hajmi 5 MB dan oshmasin.');let ext='';if(buffer.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))ext='png';else if(buffer[0]===255&&buffer[1]===216&&buffer[2]===255)ext='jpg';else if(buffer.toString('ascii',0,4)==='RIFF'&&buffer.toString('ascii',8,12)==='WEBP')ext='webp';else throw new AppError('Rasm formati noto‘g‘ri.');const filename=randomUUID()+'.'+ext;fs.writeFileSync(path.join(directory,'uploads',filename),buffer,{flag:'wx'});return json(res,{url:'/uploads/'+filename},201);}
 throw new AppError('Amal topilmadi.',404);
 }
 if(route.startsWith('/api/'))throw new AppError('API topilmadi.',404);
 if(!['GET','HEAD'].includes(req.method))throw new AppError('Usul qo‘llab-quvvatlanmaydi.',405);
 let file;
 if(route.startsWith('/uploads/')){const name=route.slice(9);if(!/^[a-f0-9-]+\.(png|jpg|webp)$/.test(name))throw new AppError('Fayl topilmadi.',404);file=path.join(directory,'uploads',name);}
 else if(route==='/admin'||route==='/admin/')file=path.join(root,'public/admin.html');
 else if(route==='/'||route.startsWith('/product/')||['/collection','/toplam','/track','/checkout'].includes(route))file=path.join(root,'public/index.html');
 else{const relative=decodeURIComponent(route).replace(/^\//,'');file=path.resolve(root,'public',relative);if(!file.startsWith(path.join(root,'public')+path.sep))throw new AppError('Fayl topilmadi.',404);}
 if(!fs.existsSync(file)||!fs.statSync(file).isFile())throw new AppError('Sahifa topilmadi.',404);
 const stat=fs.statSync(file),ext=path.extname(file);res.writeHead(200,{'Content-Type':types[ext]||'application/octet-stream','Content-Length':stat.size,'Cache-Control':ext==='.html'?'no-cache':'public, max-age=3600'});if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
 }catch(e){if(res.headersSent){res.end();return;}if(!(e instanceof AppError))console.error('Request failed:',e.name);json(res,{error:e instanceof AppError?e.message:'Serverda xatolik. Qayta urinib ko‘ring.'},e.status||500);}
});
let working=false;
const worker=setInterval(async()=>{if(working||!configured)return;working=true;try{for(let n=0;n<5;n++)if(!await sendNext(store,telegram))break;}catch{console.error('Notification worker failed')}finally{working=false}},5000);
server.listen(port,host,()=>{console.log(`${brand.name}: ${publicUrl}\nAdministrator: ${publicUrl}/admin\nEmail: ${process.env.ADMIN_EMAIL||'admin@intimshop.local'}`);if(generated)console.log(`Birinchi kirish paroli (saqlab oling): ${generated}`);console.log(configured?'Telegram bot ulangan.':'Telegram: hali sozlanmagan. Buyurtmalar bazada saqlanadi.');
 if(configured&&/^https:/.test(publicUrl))setWebhook(telegram.token,publicUrl+'/api/telegram/webhook',webhookSecret).then(r=>console.log(r.ok?'Telegram webhook ro‘yxatdan o‘tdi.':'Telegram webhook xato: '+JSON.stringify(r.data))).catch(()=>console.error('Telegram webhook o‘rnatilmadi.'));
 else if(configured)console.log('Telegram webhook o‘rnatilmadi: PUBLIC_URL https:// bilan boshlanishi kerak.');
});
function stop(){clearInterval(worker);server.close(()=>{store.db.close();process.exit(0)});setTimeout(()=>process.exit(0),12000).unref();}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
