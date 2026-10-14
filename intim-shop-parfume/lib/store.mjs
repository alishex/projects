import { DatabaseSync } from 'node:sqlite';
import { randomBytes, randomUUID, scryptSync, timingSafeEqual, createHash } from 'node:crypto';
import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
export const hash = v => createHash('sha256').update(v).digest('hex');
export function passwordHash(password,salt=randomBytes(16).toString('hex')){return salt+':'+scryptSync(password,salt,64).toString('hex');}
export function verifyPassword(password,encoded){try{const [salt,digest]=encoded.split(':');return timingSafeEqual(scryptSync(password,salt,64),Buffer.from(digest,'hex'));}catch{return false;}}
export class AppError extends Error{constructor(message,status=400){super(message);this.status=status;}}
const err=(message,status)=>{throw new AppError(message,status)};

// name is kept language-neutral; description/material/care are authored in Uzbek
// and may be overridden per-locale via `translations`.
const SEED_PRODUCTS=[
 {slug:'velvet-touch',name:'Velvet Touch',category:'vibrator',price:290000,tag:'',image:'velvet-touch.svg',
  description:'Yumshoq silikon korpusli, bir necha tebranish rejimli intim massajer. Kundalik dam olish va yaqinlik uchun qulay yo‘ldosh.',
  material:'Tibbiy silikon, suvga chidamli (IPX7).',
  care:'Ishlatishdan oldin va keyin iliq suv va maxsus tozalovchi bilan yuving. To‘g‘ridan-to‘g‘ri quyosh nuridan uzoqda saqlang.',
  translations:{ru:{description:'Массажер с мягким силиконовым корпусом и несколькими режимами вибрации. Удобный спутник для отдыха и близости.',material:'Медицинский силикон, водонепроницаемый (IPX7).',care:'Мойте тёплой водой со специальным средством до и после использования. Храните вдали от прямых солнечных лучей.'},en:{description:'A soft silicone massager with several vibration modes. A comfortable companion for relaxation and intimacy.',material:'Medical-grade silicone, waterproof (IPX7).',care:'Wash with warm water and a dedicated cleanser before and after use. Keep away from direct sunlight.'}},
  variants:[['Standart','Pushti',8],['Standart','Qizil',8],['Standart','Binafsha',8]]},
 {slug:'silk-wand-red',name:'Silk Wand Red',category:'vibrator',price:320000,tag:'',image:'silk-wand-red.svg',
  description:'Keng sirt bilan ishlaydigan, kuchli tebranishli vand uslubidagi massajer.',
  material:'Tibbiy silikon, USB orqali zaryadlanadi.',
  care:'Zaryadlashdan oldin quriting. Tozalashda spirtli eritmalardan foydalanmang.',
  translations:{ru:{description:'Массажер в форме wand с широкой рабочей поверхностью и мощной вибрацией.',material:'Медицинский силикон, зарядка через USB.',care:'Перед зарядкой просушите устройство. Не используйте спиртосодержащие средства для очистки.'},en:{description:'A wand-style massager with a broad surface and powerful vibration.',material:'Medical-grade silicone, USB rechargeable.',care:'Dry the device before charging. Do not use alcohol-based cleaners.'}},
  variants:[['Standart','Qizil',8]]},
 {slug:'onyx-pulse',name:'Onyx Pulse',category:'vibrator',price:260000,tag:'SIGNATURE',image:'onyx-pulse.svg',
  description:'Diskret shaklli, past tovushli, kundalik foydalanish uchun ixcham massajer.',
  material:'Tibbiy silikon, suvga chidamli.',
  care:'Har foydalanishdan keyin yuvib, quruq joyda saqlang.',
  translations:{ru:{description:'Компактный массажер скромной формы с низким уровнем шума для повседневного использования.',material:'Медицинский силикон, водонепроницаемый.',care:'Мойте после каждого использования и храните в сухом месте.'},en:{description:'A compact, discreetly shaped, quiet massager for everyday use.',material:'Medical-grade silicone, waterproof.',care:'Wash after every use and store in a dry place.'}},
  variants:[['Standart','Qora',8]]},
 {slug:'dual-harmony',name:'Dual Harmony',category:'vibrator',price:420000,tag:'TANLOV',image:'dual-harmony.svg',
  description:'Ikki tomonlama stimulyatsiya uchun mo‘ljallangan, egiluvchan dizaynli massajer. Bir nechta tezlik va rejimga ega.',
  material:'Tibbiy silikon, suvga chidamli (IPX7).',
  care:'Ishlatishdan so‘ng darhol yuving. Boshqa o‘yinchoqlar bilan birga saqlamang.',
  translations:{ru:{description:'Массажер гибкого дизайна для двойной стимуляции. Несколько скоростей и режимов.',material:'Медицинский силикон, водонепроницаемый (IPX7).',care:'Мойте сразу после использования. Не храните вместе с другими изделиями.'},en:{description:'A flexibly designed massager for dual stimulation, with several speeds and modes.',material:'Medical-grade silicone, waterproof (IPX7).',care:'Wash immediately after use. Do not store together with other toys.'}},
  variants:[['Standart','Pushti',8],['Standart','Binafsha',8]]},
 {slug:'noir-probe',name:'Noir Probe 10',category:'anal-probka',price:280000,tag:'',image:'noir-probe.svg',
  description:'10 xil tebranish rejimiga ega, ixcham va boshqarish qulay anal probka.',
  material:'Tibbiy silikon, simsiz pult bilan boshqariladi.',
  care:'Har safar ishlatishdan oldin va keyin yuving. Faqat suvga asoslangan lubrikant bilan ishlating.',
  translations:{ru:{description:'Компактная анальная пробка с 10 режимами вибрации и удобным беспроводным пультом.',material:'Медицинский силикон, управление беспроводным пультом.',care:'Мойте перед каждым использованием и после него. Используйте только лубрикант на водной основе.'},en:{description:'A compact anal probe with 10 vibration modes and an easy wireless remote.',material:'Medical-grade silicone, wireless remote control.',care:'Wash before and after every use. Use only water-based lubricant with it.'}},
  variants:[['Standart','Qora',8]]},
 {slug:'velvet-plug-classic',name:'Velvet Plug Classic',category:'anal-probka',price:190000,tag:'',image:'velvet-plug-classic.svg',
  description:'Silliq silikon sirtli, uchta o‘lchamda mavjud klassik anal plug.',
  material:'Tibbiy silikon, lateks tarkibisiz.',
  care:'Iliq suv bilan yuving, quritib saqlang.',
  translations:{ru:{description:'Классическая анальная пробка с гладкой силиконовой поверхностью, доступна в трёх размерах.',material:'Медицинский силикон, без латекса.',care:'Мойте тёплой водой, храните высушенной.'},en:{description:'A classic anal plug with a smooth silicone surface, available in three sizes.',material:'Medical-grade silicone, latex-free.',care:'Wash with warm water and store fully dry.'}},
  variants:[['S','Qora',8],['M','Qora',8],['L','Qora',8],['S','Pushti',8],['M','Pushti',8],['L','Pushti',8]]},
 {slug:'rose-jewel-plug',name:'Rose Jewel Plug',category:'anal-probka',price:220000,tag:'YANGI',image:'rose-jewel-plug.svg',
  description:'Metall korpusli, bezakli tosh bilan ziynatlangan plug — nafis va yengil.',
  material:'Jarrohlik po‘lati, nikel tarkibisiz qoplama.',
  care:'Yumshoq mato bilan arting, namlikdan uzoqda saqlang.',
  translations:{ru:{description:'Пробка из металла, украшенная декоративным камнем — изящная и лёгкая.',material:'Хирургическая сталь, покрытие без никеля.',care:'Протирайте мягкой тканью, храните вдали от влаги.'},en:{description:'A metal plug finished with a decorative gem — elegant and lightweight.',material:'Surgical steel, nickel-free coating.',care:'Wipe with a soft cloth and keep away from moisture.'}},
  variants:[['Standart','Pushti',8],['Standart','Qizil',8],['Standart','Oltin',8]]},
 {slug:'twilight-teaser',name:'Twilight Teaser',category:'vibrator',price:240000,tag:'',image:'twilight-teaser.svg',
  description:'Barmoqqa sig‘adigan, ovozsiz va kuchli — safarga ham qulay ixcham massajer.',
  material:'Tibbiy silikon, batareyka bilan ishlaydi.',
  care:'Foydalanishdan keyin batareyasini chiqarib saqlang.',
  translations:{ru:{description:'Миниатюрный массажер, который умещается в ладони — тихий, мощный, удобен в поездках.',material:'Медицинский силикон, работает от батарейки.',care:'После использования извлеките батарейку для хранения.'},en:{description:'A palm-sized massager — quiet, powerful, and travel-friendly.',material:'Medical-grade silicone, battery-powered.',care:'Remove the battery for storage after use.'}},
  variants:[['Standart','Qizil',8],['Standart','Binafsha',8]]},
 {slug:'kama-sutra-cards',name:'Kama Sutra Playing Cards',category:'oyinlar',price:150000,tag:'',image:'kama-sutra-cards.svg',
  description:'O‘yin shaklidagi intim kartalar to‘plami — juftlar uchun qiziqarli va yengil boshlanish.',
  material:'Qalin laminatlangan qog‘oz, 54 karta.',
  care:'Namlikdan uzoqda, quti ichida saqlang.',
  translations:{ru:{description:'Набор игральных карт для пар — лёгкое и увлекательное начало вечера.',material:'Плотная ламинированная бумага, 54 карты.',care:'Храните в коробке, вдали от влаги.'},en:{description:'A card game set for couples — a playful, easy way to start the evening.',material:'Thick laminated card stock, 54 cards.',care:'Store in the box, away from moisture.'}},
  variants:[['Standart','Standart',8]]},
 {slug:'saqlash-xaltachasi',name:'Discreet Pouch',category:'aksessuar',price:60000,tag:'',image:'saqlash-xaltachasi.svg',
  description:'Shaxsiy buyumlaringizni diskret saqlash uchun yumshoq ichki qavatli xaltacha.',
  material:'Baxmal tashqi qavat, yumshoq ichki astar.',
  care:'Quruq matoda arting, mashinada yuvmang.',
  translations:{ru:{description:'Мешочек с мягкой внутренней подкладкой для деликатного хранения личных вещей.',material:'Бархатистая внешняя ткань, мягкая подкладка.',care:'Протирайте сухой тканью, не стирайте в машине.'},en:{description:'A soft-lined pouch for discreet storage of personal items.',material:'Velvet-like outer fabric, soft inner lining.',care:'Wipe with a dry cloth; do not machine wash.'}},
  variants:[['Standart','Qora',8]]},
 {slug:'silk-glide-lubrikant',name:'Silk Glide',category:'lubrikant',price:90000,tag:'',image:'silk-glide-lubrikant.svg',
  description:'Suvga asoslangan, hidsiz va rangsiz lubrikant — silikon o‘yinchoqlar bilan ham mos.',
  material:'Suv asosida, glitserin va parabensiz.',
  care:'Salqin joyda saqlang, ochilgandan keyin 6 oy ichida ishlating.',
  translations:{ru:{description:'Лубрикант на водной основе, без запаха и цвета — совместим и с силиконовыми изделиями.',material:'На водной основе, без глицерина и парабенов.',care:'Храните в прохладном месте, используйте в течение 6 месяцев после вскрытия.'},en:{description:'A water-based, unscented, colorless lubricant — safe to use with silicone toys too.',material:'Water-based, glycerin- and paraben-free.',care:'Store in a cool place; use within 6 months of opening.'}},
  variants:[['100 ml','Standart',8],['200 ml','Standart',8]]},
 {slug:'tozalovchi-sprey',name:'Pure Mist Cleaner',category:'parvarish',price:70000,tag:'',image:'tozalovchi-sprey.svg',
  description:'Intim o‘yinchoqlar uchun antibakterial tozalovchi sprey — hidsiz va yengil formula.',
  material:'Spirtsiz antibakterial formula.',
  care:'Har foydalanishdan so‘ng purkab, quruq mato bilan arting.',
  translations:{ru:{description:'Антибактериальный спрей для очистки интим-товаров — лёгкая формула без запаха.',material:'Антибактериальная формула без спирта.',care:'Распыляйте после каждого использования и протирайте сухой тканью.'},en:{description:'An antibacterial cleaning spray for intimate products — a light, unscented formula.',material:'Alcohol-free antibacterial formula.',care:'Spray after every use and wipe with a dry cloth.'}},
  variants:[['Standart','Standart',8]]},
];

export function createStore(directory){
 mkdirSync(directory,{recursive:true});
 const db=new DatabaseSync(path.join(directory,'store.sqlite'));
 db.exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
 const MIGRATIONS=['001_initial.sql'];
 for(let v=db.prepare('PRAGMA user_version').get().user_version;v<MIGRATIONS.length;v++)db.exec(readFileSync(new URL('../migrations/'+MIGRATIONS[v],import.meta.url),'utf8'));
 const transact=fn=>{db.exec('BEGIN IMMEDIATE');try{const value=fn();db.exec('COMMIT');return value}catch(e){db.exec('ROLLBACK');throw e}};
 function seed(){if(db.prepare('SELECT COUNT(*) AS n FROM products').get().n)return;
 transact(()=>{for(const item of SEED_PRODUCTS){const id=randomUUID();db.prepare('INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,item.slug,item.name,item.category,item.price,item.description,item.material,item.care,JSON.stringify([{url:'/assets/'+item.image}]),item.tag,JSON.stringify(item.translations||{}),1,new Date().toISOString());for(const [size,color,stock] of item.variants)db.prepare('INSERT INTO variants VALUES(?,?,?,?,?)').run(randomUUID(),id,size,color,stock);}});
 }
 function ensureAdmin(email,password){if(db.prepare('SELECT id FROM admins LIMIT 1').get())return null;if(password&&password.length<12)throw new Error('ADMIN_PASSWORD kamida 12 belgidan iborat bo‘lsin.');const chosen=password||randomBytes(15).toString('base64url');db.prepare('INSERT INTO admins VALUES(?,?,?)').run(randomUUID(),email.toLowerCase(),passwordHash(chosen));return password?null:chosen;}
 function listProducts(all=false){return db.prepare('SELECT * FROM products '+(all?'':'WHERE active=1')+' ORDER BY rowid').all().map(p=>({...p,active:!!p.active,images:JSON.parse(p.images),translations:JSON.parse(p.translations||'{}'),variants:db.prepare('SELECT * FROM variants WHERE product_id=? ORDER BY rowid').all(p.id)}));}
 function validTranslationBlock(block){if(block===undefined)return true;if(typeof block!=='object'||block===null)return false;for(const locale of ['ru','en']){const t=block[locale];if(t===undefined)continue;if(typeof t!=='object'||t===null)return false;for(const [key,max] of [['description',2000],['material',300],['care',400]]){if(t[key]===undefined)continue;if(typeof t[key]!=='string'||t[key].length>max)return false;}}return true;}
 function saveProduct(input){
 const {name,category,description,material,care}=input;
 if([name,category,description,material,care].some(v=>typeof v!=='string')||name.trim().length<2||name.length>100||category.length>50||description.length>2000||material.length>300||care.length>400)err('Mahsulot ma’lumotlarini tekshiring.');
 if(!Number.isSafeInteger(input.price)||input.price<1000||input.price>100000000)err('Narxni to‘g‘ri kiriting.');
 if(!Array.isArray(input.images)||input.images.length<1||input.images.length>6||input.images.some(im=>!im||typeof im.url!=='string'||!/^\/(assets|uploads)\/[a-zA-Z0-9._-]+$/.test(im.url)))err('Rasmni yuklang.');
 if(!Array.isArray(input.variants)||input.variants.length<1||input.variants.length>50)err('Kamida bitta variant kerak.');
 if(!validTranslationBlock(input.translations))err('Tarjima maydonlarini tekshiring.');
 const seen=new Set();for(const v of input.variants){if(typeof v.size!=='string'||!v.size.trim()||v.size.length>15||typeof v.color!=='string'||!v.color.trim()||v.color.length>30||!Number.isSafeInteger(v.stock)||v.stock<0||v.stock>100000)err('Variant va qoldiqni tekshiring.');const key=v.size.trim()+'|'+v.color.trim();if(seen.has(key))err('Variantlar takrorlanmasin.');seen.add(key);}
 const id=input.id||randomUUID(),existing=db.prepare('SELECT id FROM products WHERE id=?').get(id);if(input.id&&!existing)err('Mahsulot topilmadi.',404);
 return transact(()=>{
 const slug=existing?db.prepare('SELECT slug FROM products WHERE id=?').get(id).slug:name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,55)+'-'+id.slice(0,6);
 const translations=JSON.stringify(input.translations||{});
 db.prepare(`INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,price=excluded.price,description=excluded.description,material=excluded.material,care=excluded.care,images=excluded.images,tag=excluded.tag,translations=excluded.translations,active=excluded.active`).run(id,slug,name.trim(),category.trim(),input.price,description,material,care,JSON.stringify(input.images),String(input.tag||'').slice(0,30),translations,input.active===false?0:1,new Date().toISOString());
 // Keep old variants for order history, setting omitted variants out of stock.
 db.prepare('UPDATE variants SET stock=0 WHERE product_id=?').run(id);
 for(const v of input.variants)db.prepare('INSERT INTO variants VALUES(?,?,?,?,?) ON CONFLICT(product_id,size,color) DO UPDATE SET stock=excluded.stock').run(randomUUID(),id,v.size.trim(),v.color.trim(),v.stock);
 return listProducts(true).find(p=>p.id===id);
 });
 }
 function orderDetails(id){const order=db.prepare('SELECT * FROM orders WHERE id=?').get(id);if(!order)return null;return {...order,items:db.prepare('SELECT * FROM order_items WHERE order_id=?').all(id),notification:db.prepare('SELECT status,attempts,error FROM notifications WHERE order_id=?').get(id)};}
 function createOrder(body){
 if(!body||typeof body!=='object')err('Buyurtma noto‘g‘ri.');
 const {customer,address,note='',requestKey}=body;const phone=typeof body.phone==='string'?body.phone.replace(/[\s()-]/g,''):'';
 if(typeof customer!=='string'||customer.trim().length<2||customer.length>80||!/^\+998\d{9}$/.test(phone)||typeof address!=='string'||address.trim().length<5||address.length>250||typeof note!=='string'||note.length>500||typeof requestKey!=='string'||!/^[0-9a-f-]{36}$/.test(requestKey)||!Array.isArray(body.items)||!body.items.length||body.items.length>30)err('Ism, telefon, manzil va savatni tekshiring.');
 let lat=null,lng=null;if(body.lat!==undefined&&body.lat!==null||body.lng!==undefined&&body.lng!==null){lat=Number(body.lat);lng=Number(body.lng);if(!Number.isFinite(lat)||!Number.isFinite(lng)||lat<-90||lat>90||lng<-180||lng>180)err('Joylashuv noto‘g‘ri.');}
 const quantities=new Map();for(const item of body.items){if(typeof item.variantId!=='string'||!Number.isInteger(item.quantity)||item.quantity<1||item.quantity>10)err('Mahsulot miqdori noto‘g‘ri.');quantities.set(item.variantId,(quantities.get(item.variantId)||0)+item.quantity);}
 const normalized={customer:customer.trim(),phone,address:address.trim(),note:note.trim(),items:[...quantities].sort()};const digest=hash(JSON.stringify(normalized));
 return transact(()=>{
 const existing=db.prepare('SELECT * FROM orders WHERE request_key=?').get(requestKey);if(existing){if(existing.payload_hash!==digest)err('Bu buyurtma kaliti boshqa ma’lumot uchun ishlatilgan.',409);return {id:existing.id,token:existing.tracking_token,duplicate:true};}
 let total=0;const items=[];for(const [variantId,quantity]of quantities){if(quantity>10)err('Bitta variantdan ko‘pi bilan 10 ta.');const p=db.prepare('SELECT v.*,p.name,p.price,p.active FROM variants v JOIN products p ON p.id=v.product_id WHERE v.id=?').get(variantId);if(!p||!p.active)err('Mahsulot sotuvda emas.',409);if(p.stock<quantity)err(p.name+': tanlangan variantda yetarli qoldiq yo‘q.',409);items.push({...p,quantity});total+=p.price*quantity;}
 const id=randomUUID(),token=randomBytes(32).toString('base64url');db.prepare('INSERT INTO orders(id,request_key,payload_hash,tracking_token,customer,phone,address,note,lat,lng,total,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,requestKey,digest,token,normalized.customer,phone,normalized.address,normalized.note,lat,lng,total,'new',new Date().toISOString());
 for(const item of items){const update=db.prepare('UPDATE variants SET stock=stock-? WHERE id=? AND stock>=?').run(item.quantity,item.id,item.quantity);if(!update.changes)err('Qoldiq o‘zgardi. Savatni tekshiring.',409);db.prepare('INSERT INTO order_items(order_id,variant_id,name,size,color,quantity,price) VALUES(?,?,?,?,?,?,?)').run(id,item.id,item.name,item.size,item.color,item.quantity,item.price);}
 db.prepare('INSERT INTO notifications(order_id) VALUES(?)').run(id);return {id,token,duplicate:false};
 });
 }
 function status(id,next){const transitions={new:['confirmed','cancelled'],confirmed:['preparing','cancelled'],preparing:['delivered','cancelled'],delivered:[],cancelled:[]};return transact(()=>{const o=db.prepare('SELECT status FROM orders WHERE id=?').get(id);if(!o)err('Buyurtma topilmadi.',404);if(next===o.status)return;if(!transitions[o.status]?.includes(next))err('Bu holatga o‘tish mumkin emas.',409);if(next==='cancelled'){for(const item of db.prepare('SELECT variant_id,quantity FROM order_items WHERE order_id=?').all(id))db.prepare('UPDATE variants SET stock=stock+? WHERE id=?').run(item.quantity,item.variant_id);}db.prepare('UPDATE orders SET status=? WHERE id=?').run(next,id);});}
 function rateLimit(key,maximum,windowMs){const now=Date.now();db.prepare('DELETE FROM limits WHERE until < ?').run(now);return transact(()=>{const row=db.prepare('SELECT * FROM limits WHERE key=?').get(key);if(row){if(row.count>=maximum)return false;db.prepare('UPDATE limits SET count=count+1 WHERE key=?').run(key);}else db.prepare('INSERT INTO limits VALUES(?,1,?)').run(key,now+windowMs);return true;});}
 function login(email,password){const a=db.prepare('SELECT * FROM admins WHERE email=?').get(email.toLowerCase());const dummy=passwordHash('dummy-password-for-timing','00112233445566778899aabbccddeeff');if(!verifyPassword(password,a?.password||dummy)||!a)return null;const token=randomBytes(32).toString('base64url');db.prepare('DELETE FROM sessions WHERE expires<?').run(Date.now());db.prepare('INSERT INTO sessions VALUES(?,?,?)').run(hash(token),a.id,Date.now()+86400000);return token;}
 function admin(token){if(!token)return null;return db.prepare('SELECT a.id,a.email FROM sessions s JOIN admins a ON a.id=s.admin_id WHERE s.hash=? AND s.expires>?').get(hash(token),Date.now())||null;}
 function claimNotification(){return transact(()=>{db.prepare("UPDATE notifications SET status='pending' WHERE status='processing' AND locked_at<?").run(Date.now()-120000);const job=db.prepare("SELECT * FROM notifications WHERE status='pending' AND next_at<=? ORDER BY id LIMIT 1").get(Date.now());if(!job)return null;db.prepare("UPDATE notifications SET status='processing',locked_at=? WHERE id=?").run(Date.now(),job.id);return job;});}
 function setNotificationMessage(orderId,messageId){db.prepare('UPDATE notifications SET message_id=? WHERE order_id=?').run(messageId,orderId);}
 function notificationMessage(orderId){return db.prepare('SELECT message_id FROM notifications WHERE order_id=?').get(orderId)?.message_id||null;}
 function setVariantStock(variantId,stock){if(!Number.isSafeInteger(stock)||stock<0||stock>100000)err('Qoldiqni to‘g‘ri kiriting.');const r=db.prepare('UPDATE variants SET stock=? WHERE id=?').run(stock,variantId);if(!r.changes)err('Variant topilmadi.',404);}
 function setProductPrice(productId,price){if(!Number.isSafeInteger(price)||price<1000||price>100000000)err('Narxni to‘g‘ri kiriting.');const r=db.prepare('UPDATE products SET price=? WHERE id=?').run(price,productId);if(!r.changes)err('Mahsulot topilmadi.',404);}
 function toggleProductActive(productId){const p=db.prepare('SELECT active FROM products WHERE id=?').get(productId);if(!p)err('Mahsulot topilmadi.',404);const next=p.active?0:1;db.prepare('UPDATE products SET active=? WHERE id=?').run(next,productId);return !!next;}
 function stats(){const o=db.prepare("SELECT COUNT(*) FILTER (WHERE status='new') AS newOrders, COALESCE(SUM(total) FILTER (WHERE status='delivered'),0) AS delivered FROM orders").get();const p=db.prepare('SELECT COUNT(*) FILTER (WHERE active=1) AS activeProducts FROM products').get();return {newOrders:o.newOrders,delivered:o.delivered,activeProducts:p.activeProducts};}
 return {db,seed,ensureAdmin,listProducts,saveProduct,createOrder,orderDetails,status,rateLimit,login,admin,claimNotification,setNotificationMessage,notificationMessage,setVariantStock,setProductPrice,toggleProductActive,stats,transact};
}
