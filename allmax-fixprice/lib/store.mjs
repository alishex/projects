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
// and may be overridden per-locale via `translations`. `image` points at a shared
// category placeholder under public/assets/cat/ — the storefront renders the matching
// inline icon for these; only a real /uploads/ photo (via the admin panel) switches a
// product to a plain <img>. See ASSETS.md.
const SEED_PRODUCTS=[
 {slug:'klassik-kurtka',name:'Klassik kurtka',category:'kurtka',price:299900,premium:false,tag:'YANGI',image:'kurtka.svg',
  description:'Kundalik kiyinish uchun mo‘ljallangan klassik kesimli kurtka. Issiq mavsumlar oralig‘ida ham qulay, har qanday obrazga mos.',
  material:'Tashqi qavat — plashovka, ichki astar — issiqlik saqlovchi vatin.',
  care:'Quruq tozalash tavsiya etiladi. 30°C da nozik rejimda mashinada yuvish mumkin.',
  translations:{ru:{description:'Куртка классического кроя для повседневной носки. Комфортна в межсезонье, сочетается с любым образом.',material:'Верх — плащёвка, подкладка — утеплитель.',care:'Рекомендуется химчистка. Машинная стирка при 30°C в деликатном режиме допустима.'},en:{description:'A classic-cut jacket for everyday wear. Comfortable through the in-between seasons, pairs with any look.',material:'Outer shell — technical weave, insulated lining.',care:'Dry cleaning recommended. Machine-washable at 30°C on a delicate cycle.'}},
  variants:[['M','Qora',8],['L','Qora',8],['XL','Qora',8],['L','Kulrang',6]]},
 {slug:'oxford-koylak',name:'Oxford ko‘ylak',category:'koylak',price:199900,premium:false,tag:'',image:'koylak.svg',
  description:'Oxford matosidan tikilgan klassik ko‘ylak — ish kuniga ham, kundalik uchun ham mos. Yumshoq, nafas oluvchi tuzilma.',
  material:'100% paxta, Oxford to‘qima.',
  care:'40°C da yuvish, dazmollash o‘rtacha haroratda.',
  translations:{ru:{description:'Классическая рубашка из ткани Oxford — подходит и для работы, и на каждый день. Мягкая, дышащая ткань.',material:'100% хлопок, плетение Oxford.',care:'Стирка при 40°C, глажка на средней температуре.'},en:{description:'A classic shirt in Oxford cloth — works for the office and everyday wear alike. Soft, breathable weave.',material:'100% cotton, Oxford weave.',care:'Wash at 40°C, iron on medium heat.'}},
  variants:[['M','Oq',12],['L','Oq',12],['XL','Oq',8],['L','Moviy',8]]},
 {slug:'trikotaj-kardigan',name:'Trikotaj kardigan',category:'kardigan',price:149900,premium:false,tag:'',image:'kardigan.svg',
  description:'Yumshoq trikotaj kardigan, tugmali old qism. Ko‘ylak yoki futbolka ustidan kiyish uchun qulay.',
  material:'70% akril, 30% jun aralashmasi.',
  care:'30°C da nozik yuvish, yoyib quritish.',
  translations:{ru:{description:'Мягкий трикотажный кардиган на пуговицах. Удобно надевать поверх рубашки или футболки.',material:'70% акрил, 30% шерсть.',care:'Деликатная стирка при 30°C, сушка в разложенном виде.'},en:{description:'A soft knit cardigan with button front. Easy to layer over a shirt or t-shirt.',material:'70% acrylic, 30% wool blend.',care:'Delicate wash at 30°C, dry flat.'}},
  variants:[['M','Kulrang',9],['L','Kulrang',9],['XL','Kulrang',6],['L','Qora',7]]},
 {slug:'bazaviy-futbolka',name:'Bazaviy futbolka',category:'futbolka',price:99900,premium:false,tag:'',image:'futbolka.svg',
  description:'Zich to‘qilgan paxta futbolka — kundalik garderobning asosi. Formasini yuvishdan keyin ham yaxshi saqlaydi.',
  material:'100% paxta, 180 g/m².',
  care:'30°C da yuvish, baland haroratda quritmaslik tavsiya etiladi.',
  translations:{ru:{description:'Футболка из плотного хлопка — основа повседневного гардероба. Хорошо держит форму после стирки.',material:'100% хлопок, 180 г/м².',care:'Стирка при 30°C, не рекомендуется сушка при высокой температуре.'},en:{description:'A dense-knit cotton t-shirt — a wardrobe staple. Holds its shape well after washing.',material:'100% cotton, 180 g/m².',care:'Wash at 30°C; avoid high-heat drying.'}},
  variants:[['M','Qora',15],['L','Qora',15],['XL','Qora',10],['M','Oq',12],['L','Oq',12]]},
 {slug:'slim-shim',name:'Slim shim',category:'shim',price:249900,premium:false,tag:'',image:'shim.svg',
  description:'Ingichka (slim) kesimli klassik shim. Cho‘ziluvchan to‘qima harakatni cheklamaydi.',
  material:'98% paxta, 2% elastan.',
  care:'30°C da yuvish, past haroratda dazmollash.',
  translations:{ru:{description:'Классические брюки зауженного кроя. Эластичная ткань не сковывает движений.',material:'98% хлопок, 2% эластан.',care:'Стирка при 30°C, глажка на низкой температуре.'},en:{description:'Classic slim-cut trousers. The stretch weave moves with you.',material:'98% cotton, 2% elastane.',care:'Wash at 30°C, iron on low heat.'}},
  variants:[['30','Qora',8],['32','Qora',10],['34','Qora',10],['32','Kulrang',8],['34','Kulrang',6]]},
 {slug:'ikki-qatlamli-kostyum',name:'Ikki qatlamli kostyum',category:'kostyum',price:399900,premium:false,tag:'TANLOV',image:'kostyum.svg',
  description:'Jaket va shimdan iborat klassik ikki qatlamli kostyum. Tadbir va ish uchrashuvlari uchun ishonchli tanlov.',
  material:'Polyester-vikoza aralashmasi, yarim yungli tuzilma.',
  care:'Faqat quruq tozalash.',
  translations:{ru:{description:'Классический костюм-двойка: пиджак и брюки. Надёжный выбор для мероприятий и деловых встреч.',material:'Смесь полиэстера и вискозы, полушерстяная структура.',care:'Только химчистка.'},en:{description:'A classic two-piece suit: jacket and trousers. A dependable choice for events and business meetings.',material:'Polyester-viscose blend, half-wool structure.',care:'Dry clean only.'}},
  variants:[['48','Qora',6],['50','Qora',6],['52','Qora',5],['50','Lojuvard',5]]},
 {slug:'premium-kashmir-dvoyka',name:'Premium kashmir dvoyka',category:'kostyum',price:690000,premium:true,tag:'PREMIUM',image:'kostyum.svg',
  description:'Kashmir aralashmali matodan tikilgan premium ikki qatlamli kostyum. Maxsus tadbirlar va muhim uchrashuvlar uchun.',
  material:'70% kashmir, 30% yun aralashmasi.',
  care:'Faqat professional quruq tozalash.',
  translations:{ru:{description:'Премиальный костюм-двойка из кашемировой смеси. Для особых случаев и важных встреч.',material:'70% кашемир, 30% шерсть.',care:'Только профессиональная химчистка.'},en:{description:'A premium two-piece suit in a cashmere blend. For special occasions and important meetings.',material:'70% cashmere, 30% wool blend.',care:'Professional dry cleaning only.'}},
  variants:[['48','Lojuvard',3],['50','Lojuvard',3],['50','Qora',4]]},
 {slug:'sport-dvoyka',name:'Sport dvoyka',category:'dvoyka',price:199900,premium:false,tag:'',image:'dvoyka.svg',
  description:'Bir xil to‘qimadan tikilgan sport kostyum-dvoyka — bezrukavka ustki va shim. Kundalik faol kiyinish uchun.',
  material:'80% paxta, 20% poliester, trikotaj.',
  care:'30°C da yuvish, mashinada sekin sikl bilan quritish mumkin.',
  translations:{ru:{description:'Спортивный костюм-двойка из единой ткани — верх и брюки. Для активной повседневной носки.',material:'80% хлопок, 20% полиэстер, трикотаж.',care:'Стирка при 30°C, допустима машинная сушка на деликатном режиме.'},en:{description:'A matching two-piece tracksuit — top and trousers in one fabric. Built for an active everyday pace.',material:'80% cotton, 20% polyester, knit.',care:'Wash at 30°C; machine drying on a gentle cycle is fine.'}},
  variants:[['M','Kulrang',8],['L','Kulrang',8],['XL','Kulrang',6],['L','Qora',8]]},
 {slug:'jun-gilet',name:'Jun jilet',category:'gilet',price:149900,premium:false,tag:'',image:'gilet.svg',
  description:'Yengil jun jilet — ko‘ylak yoki kardigan ustidan qatlama sifatida kiyish uchun qulay.',
  material:'60% jun, 40% akril aralashmasi.',
  care:'Quruq tozalash tavsiya etiladi.',
  translations:{ru:{description:'Лёгкий шерстяной жилет — удобно надевать поверх рубашки или кардигана.',material:'60% шерсть, 40% акрил.',care:'Рекомендуется химчистка.'},en:{description:'A lightweight wool gilet — easy to layer over a shirt or cardigan.',material:'60% wool, 40% acrylic blend.',care:'Dry cleaning recommended.'}},
  variants:[['M','Kulrang',7],['L','Kulrang',7],['XL','Kulrang',5]]},
 {slug:'teri-loafers',name:'Teri loafers',category:'oyoq-kiyim',price:299900,premium:false,tag:'',image:'oyoq-kiyim.svg',
  description:'Tabiiy teridan tayyorlangan klassik loafers. Kundalik va yarim rasmiy obrazlarga mos.',
  material:'Tabiiy teri, kauchuk taglik.',
  care:'Yumshoq mato va teri uchun krem bilan parvarish qiling. Namlikdan saqlang.',
  translations:{ru:{description:'Классические лоферы из натуральной кожи. Подходят к повседневным и полуофициальным образам.',material:'Натуральная кожа, резиновая подошва.',care:'Ухаживайте мягкой тканью и кремом для кожи. Берегите от влаги.'},en:{description:'Classic loafers in genuine leather. Suit both casual and smart-casual looks.',material:'Genuine leather, rubber sole.',care:'Care for with a soft cloth and leather cream. Keep away from moisture.'}},
  variants:[['41','Qora',6],['42','Qora',8],['43','Qora',8],['42','Jigarrang',6],['43','Jigarrang',5]]},
 {slug:'teri-hamyon',name:'Teri hamyon',category:'hamyon',price:99900,premium:false,tag:'',image:'hamyon.svg',
  description:'Ixcham teri hamyon, bir nechta karta bo‘limi va pul bo‘lagi bilan.',
  material:'Tabiiy teri.',
  care:'Quruq mato bilan arting, namlikdan uzoqda saqlang.',
  translations:{ru:{description:'Компактный кожаный кошелёк с несколькими отделениями для карт и купюр.',material:'Натуральная кожа.',care:'Протирайте сухой тканью, храните вдали от влаги.'},en:{description:'A compact leather wallet with several card slots and a bill compartment.',material:'Genuine leather.',care:'Wipe with a dry cloth; keep away from moisture.'}},
  variants:[['Standart','Qora',14],['Standart','Jigarrang',10]]},
 {slug:'charm-kamar',name:'Charm kamar',category:'remen',price:99900,premium:false,tag:'',image:'remen.svg',
  description:'Klassik charm kamar, metall pryajka bilan. Shim va jinsi bilan bir xilda mos tushadi.',
  material:'Tabiiy teri, metall pryajka.',
  care:'Quruq mato bilan arting.',
  translations:{ru:{description:'Классический кожаный ремень с металлической пряжкой. Одинаково хорошо сочетается с брюками и джинсами.',material:'Натуральная кожа, металлическая пряжка.',care:'Протирайте сухой тканью.'},en:{description:'A classic leather belt with a metal buckle. Works equally well with trousers or jeans.',material:'Genuine leather, metal buckle.',care:'Wipe with a dry cloth.'}},
  variants:[['100 sm','Qora',12],['110 sm','Qora',10],['100 sm','Jigarrang',8]]},
 {slug:'kundalik-sumka',name:'Kundalik sumka',category:'sumka',price:249900,premium:false,tag:'',image:'sumka.svg',
  description:'Noutbuk va kundalik buyumlar uchun bo‘lim-bo‘lim sumka, qalin tasma bilan.',
  material:'Suvga chidamli poliester, charm detallar.',
  care:'Namlangan mato bilan arting, mashinada yuvmang.',
  translations:{ru:{description:'Сумка с отделениями для ноутбука и повседневных вещей, с плотным ремнём.',material:'Водостойкий полиэстер, кожаные детали.',care:'Протирайте влажной тканью, не стирайте в машине.'},en:{description:'A compartmentalized bag for a laptop and daily essentials, with a sturdy strap.',material:'Water-resistant polyester, leather trims.',care:'Wipe with a damp cloth; do not machine wash.'}},
  variants:[['Standart','Qora',9],['Standart','Kulrang',7]]},
 {slug:'premium-aksessuar-toplami',name:'Premium aksessuar to‘plami',category:'aksessuar',price:590000,premium:true,tag:'PREMIUM',image:'aksessuar.svg',
  description:'Charm hamyon, soat va qalamdan iborat premium sovg‘a to‘plami, maxsus qutida.',
  material:'Tabiiy teri, legirlangan po‘lat.',
  care:'Har bir detal uchun alohida parvarish yo‘riqnomasi qutida beriladi.',
  translations:{ru:{description:'Премиальный подарочный набор: кожаное портмоне, часы и ручка — в фирменной коробке.',material:'Натуральная кожа, легированная сталь.',care:'Инструкция по уходу за каждым предметом — в коробке.'},en:{description:'A premium gift set — leather billfold, watch and pen — in a branded box.',material:'Genuine leather, alloyed steel.',care:'Individual care instructions for each piece are included in the box.'}},
  variants:[['Standart','Qora',4]]},
 {slug:'teri-hamyon-nugraph',name:'Yengil vetrovka',category:'vetrovka',price:199900,premium:false,tag:'',image:'vetrovka.svg',
  description:'Shamolga chidamli yengil vetrovka, qoplam ichiga yig‘iladigan kapyushon bilan.',
  material:'100% poliester, suv o‘tkazmaydigan qoplama.',
  care:'30°C da nozik rejimda yuvish, osib quritish.',
  translations:{ru:{description:'Лёгкая ветрозащитная куртка со скрытым капюшоном.',material:'100% полиэстер, водоотталкивающее покрытие.',care:'Стирка при 30°C в деликатном режиме, сушка на плечиках.'},en:{description:'A lightweight windbreaker with a stowable hood.',material:'100% polyester, water-repellent coating.',care:'Wash at 30°C on a delicate cycle; hang dry.'}},
  variants:[['M','Lojuvard',8],['L','Lojuvard',8],['XL','Lojuvard',5]]},
];

export function createStore(directory){
 mkdirSync(directory,{recursive:true});
 const db=new DatabaseSync(path.join(directory,'store.sqlite'));
 db.exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
 const MIGRATIONS=['001_initial.sql'];
 for(let v=db.prepare('PRAGMA user_version').get().user_version;v<MIGRATIONS.length;v++)db.exec(readFileSync(new URL('../migrations/'+MIGRATIONS[v],import.meta.url),'utf8'));
 const transact=fn=>{db.exec('BEGIN IMMEDIATE');try{const value=fn();db.exec('COMMIT');return value}catch(e){db.exec('ROLLBACK');throw e}};
 function seed(){if(db.prepare('SELECT COUNT(*) AS n FROM products').get().n)return;
 transact(()=>{for(const item of SEED_PRODUCTS){const id=randomUUID();db.prepare('INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id,item.slug,item.name,item.category,item.price,item.premium?1:0,item.description,item.material,item.care,JSON.stringify([{url:'/assets/cat/'+item.image}]),item.tag,JSON.stringify(item.translations||{}),1,new Date().toISOString());for(const [size,color,stock] of item.variants)db.prepare('INSERT INTO variants VALUES(?,?,?,?,?)').run(randomUUID(),id,size,color,stock);}});
 }
 function ensureAdmin(email,password){if(db.prepare('SELECT id FROM admins LIMIT 1').get())return null;if(password&&password.length<12)throw new Error('ADMIN_PASSWORD kamida 12 belgidan iborat bo‘lsin.');const chosen=password||randomBytes(15).toString('base64url');db.prepare('INSERT INTO admins VALUES(?,?,?)').run(randomUUID(),email.toLowerCase(),passwordHash(chosen));return password?null:chosen;}
 function listProducts(all=false){return db.prepare('SELECT * FROM products '+(all?'':'WHERE active=1')+' ORDER BY rowid').all().map(p=>({...p,active:!!p.active,premium:!!p.premium,images:JSON.parse(p.images),translations:JSON.parse(p.translations||'{}'),variants:db.prepare('SELECT * FROM variants WHERE product_id=? ORDER BY rowid').all(p.id)}));}
 function validTranslationBlock(block){if(block===undefined)return true;if(typeof block!=='object'||block===null)return false;for(const locale of ['ru','en']){const t=block[locale];if(t===undefined)continue;if(typeof t!=='object'||t===null)return false;for(const [key,max] of [['description',2000],['material',300],['care',400]]){if(t[key]===undefined)continue;if(typeof t[key]!=='string'||t[key].length>max)return false;}}return true;}
 function saveProduct(input){
 const {name,category,description,material,care}=input;
 if([name,category,description,material,care].some(v=>typeof v!=='string')||name.trim().length<2||name.length>100||category.length>50||description.length>2000||material.length>300||care.length>400)err('Mahsulot ma’lumotlarini tekshiring.');
 if(!Number.isSafeInteger(input.price)||input.price<1000||input.price>100000000)err('Narxni to‘g‘ri kiriting.');
 if(!Array.isArray(input.images)||input.images.length<1||input.images.length>6||input.images.some(im=>!im||typeof im.url!=='string'||!/^\/(assets|uploads)\/[a-zA-Z0-9._/-]+$/.test(im.url)))err('Rasmni yuklang.');
 if(!Array.isArray(input.variants)||input.variants.length<1||input.variants.length>50)err('Kamida bitta variant kerak.');
 if(!validTranslationBlock(input.translations))err('Tarjima maydonlarini tekshiring.');
 const seen=new Set();for(const v of input.variants){if(typeof v.size!=='string'||!v.size.trim()||v.size.length>15||typeof v.color!=='string'||!v.color.trim()||v.color.length>30||!Number.isSafeInteger(v.stock)||v.stock<0||v.stock>100000)err('Variant va qoldiqni tekshiring.');const key=v.size.trim()+'|'+v.color.trim();if(seen.has(key))err('Variantlar takrorlanmasin.');seen.add(key);}
 const id=input.id||randomUUID(),existing=db.prepare('SELECT id FROM products WHERE id=?').get(id);if(input.id&&!existing)err('Mahsulot topilmadi.',404);
 return transact(()=>{
 const slug=existing?db.prepare('SELECT slug FROM products WHERE id=?').get(id).slug:name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,55)+'-'+id.slice(0,6);
 const translations=JSON.stringify(input.translations||{});
 db.prepare(`INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,price=excluded.price,premium=excluded.premium,description=excluded.description,material=excluded.material,care=excluded.care,images=excluded.images,tag=excluded.tag,translations=excluded.translations,active=excluded.active`).run(id,slug,name.trim(),category.trim(),input.price,input.premium?1:0,description,material,care,JSON.stringify(input.images),String(input.tag||'').slice(0,30),translations,input.active===false?0:1,new Date().toISOString());
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
