import { apiCall, reflectStatus } from './telegram.mjs';

const STATUS_LABEL={new:'🆕 Yangi',confirmed:'✅ Tasdiqlangan',preparing:'📦 Tayyorlanmoqda',delivered:'🚚 Yetkazilgan',cancelled:'❌ Bekor qilingan'};
const TRANSITIONS={new:[['confirmed','✓ Tasdiqlash'],['cancelled','✗ Rad etish']],confirmed:[['preparing','📦 Tayyorlanmoqda'], ['cancelled','✗ Bekor qilish']],preparing:[['delivered','🚚 Yetkazildi'],['cancelled','✗ Bekor qilish']],delivered:[],cancelled:[]};
const PAGE_SIZE=6;
const money=n=>new Intl.NumberFormat('uz-UZ').format(n)+' so‘m';

function mainMenuView(){
 return {text:'🏪 ALLMAX Fix Price — Admin menyu\n\nKerakli bo‘limni tanlang:',keyboard:[[{text:'📦 Buyurtmalar',callback_data:'orders:0'}],[{text:'🛍 Mahsulotlar',callback_data:'products:0'}],[{text:'📊 Statistika',callback_data:'stats'}]]};
}

function pageNav(prefix,page,total){const nav=[];if(page>0)nav.push({text:'◀ Oldingi',callback_data:`${prefix}:${page-1}`});if((page+1)*PAGE_SIZE<total)nav.push({text:'Keyingi ▶',callback_data:`${prefix}:${page+1}`});return nav.length?[nav]:[];}

function ordersListView(store,page){
 const all=store.db.prepare('SELECT id,customer,status,created_at FROM orders ORDER BY created_at DESC').all();
 const slice=all.slice(page*PAGE_SIZE,page*PAGE_SIZE+PAGE_SIZE);
 if(!slice.length)return {text:'📦 Buyurtmalar\n\nHozircha buyurtma yo‘q.',keyboard:[[{text:'⬅ Bosh menyu',callback_data:'menu'}]]};
 const rows=slice.map(o=>[{text:`#${o.id.slice(0,8).toUpperCase()} · ${o.customer} · ${STATUS_LABEL[o.status]}`,callback_data:`order:${o.id}:${page}`}]);
 rows.push(...pageNav('orders',page,all.length));
 rows.push([{text:'⬅ Bosh menyu',callback_data:'menu'}]);
 return {text:`📦 Buyurtmalar (${all.length} ta)`,keyboard:rows};
}

function orderDetailView(store,id,page){
 const o=store.orderDetails(id);
 if(!o)return {text:'Buyurtma topilmadi — ehtimol o‘chirilgan.',keyboard:[[{text:'⬅ Orqaga',callback_data:`orders:${page}`}]]};
 const lines=[`📦 Buyurtma #${o.id.slice(0,8).toUpperCase()}`,STATUS_LABEL[o.status],'',`👤 ${o.customer}`,`📱 ${o.phone}`,`📍 ${o.address}`];
 if(o.lat!=null&&o.lng!=null)lines.push(`🗺 https://maps.google.com/?q=${o.lat},${o.lng}`);
 if(o.note)lines.push(`📝 ${o.note}`);
 lines.push('','🛍 Mahsulotlar:');
 for(const i of o.items)lines.push(` • ${i.name} · ${i.color} / ${i.size} × ${i.quantity} — ${money(i.price*i.quantity)}`);
 lines.push('',`💰 Jami: ${money(o.total)}`);
 const tgStatus={sent:'yuborilgan',pending:'navbatda',processing:'yuborilmoqda',failed:'xatolik'}[o.notification?.status];
 lines.push(`✉️ Telegram xabari: ${tgStatus||'—'}`);
 const rows=(TRANSITIONS[o.status]||[]).map(([next,label])=>[{text:label,callback_data:`ostatus:${id}:${next}:${page}`}]);
 if(o.notification?.status==='failed')rows.push([{text:'🔁 Qayta yuborish',callback_data:`retry:${id}:${page}`}]);
 rows.push([{text:'⬅ Orqaga',callback_data:`orders:${page}`}]);
 return {text:lines.join('\n'),keyboard:rows};
}

function productsListView(store,page){
 const all=store.listProducts(true);
 const slice=all.slice(page*PAGE_SIZE,page*PAGE_SIZE+PAGE_SIZE);
 if(!slice.length)return {text:'🛍 Mahsulotlar\n\nMahsulot topilmadi.',keyboard:[[{text:'⬅ Bosh menyu',callback_data:'menu'}]]};
 const rows=slice.map(p=>{const stock=p.variants.reduce((s,v)=>s+v.stock,0);return [{text:`${p.active?'✅':'🗄'} ${p.name} · ${money(p.price)} · ${stock} ta`,callback_data:`product:${p.id}:${page}`}]});
 rows.push(...pageNav('products',page,all.length));
 rows.push([{text:'⬅ Bosh menyu',callback_data:'menu'}]);
 return {text:`🛍 Mahsulotlar (${all.length} ta)`,keyboard:rows};
}

function productDetailView(store,id,page){
 const p=store.listProducts(true).find(p=>p.id===id);
 if(!p)return {text:'Mahsulot topilmadi.',keyboard:[[{text:'⬅ Orqaga',callback_data:`products:${page}`}]]};
 const lines=[`🛍 ${p.name}`,p.active?'✅ Faol':'🗄 Arxivda','',`💰 Narx: ${money(p.price)}`,p.premium?'⭐ Premium bo‘lim':'',  '','Variantlar va qoldiq:'];
 for(const v of p.variants)lines.push(` • ${v.size} / ${v.color}: ${v.stock} ta`);
 const rows=[[{text:p.active?'🗄 Arxivlash':'✅ Faollashtirish',callback_data:`ptoggle:${id}:${page}`}],[{text:'💰 Narxni o‘zgartirish',callback_data:`pprice:${id}:${page}`}]];
 for(const v of p.variants)rows.push([{text:`✏️ ${v.size}/${v.color}: ${v.stock} ta`,callback_data:`pstock:${v.id}:${id}:${page}`}]);
 rows.push([{text:'⬅ Orqaga',callback_data:`products:${page}`}]);
 return {text:lines.filter(Boolean).join('\n'),keyboard:rows};
}

function statsView(store){
 const s=store.stats();
 return {text:`📊 Statistika\n\n🆕 Yangi buyurtmalar: ${s.newOrders}\n✅ Faol mahsulotlar: ${s.activeProducts}\n💰 Yetkazilgan mahsulotlar summasi: ${money(s.delivered)}`,keyboard:[[{text:'⬅ Bosh menyu',callback_data:'menu'}]]};
}

async function render(telegram,chatId,messageId,view){
 const base={chat_id:chatId,text:view.text,reply_markup:{inline_keyboard:view.keyboard}};
 if(messageId)await apiCall(telegram.token,'editMessageText',{...base,message_id:messageId}).catch(()=>{});
 else await apiCall(telegram.token,'sendMessage',base);
}

async function handleCallback(store,telegram,pending,cb){
 const chatId=cb.message?.chat?.id;
 if(String(chatId)!==String(telegram.chatId)){await apiCall(telegram.token,'answerCallbackQuery',{callback_query_id:cb.id,text:'Ruxsat yo‘q.'});return;}
 const messageId=cb.message.message_id;
 const [action,...rest]=String(cb.data||'').split(':');
 try{
 if(action==='menu')await render(telegram,chatId,messageId,mainMenuView());
 else if(action==='orders')await render(telegram,chatId,messageId,ordersListView(store,Number(rest[0]||0)));
 else if(action==='order')await render(telegram,chatId,messageId,orderDetailView(store,rest[0],Number(rest[1]||0)));
 else if(action==='confirm'||action==='cancel'){const id=rest[0],next=action==='confirm'?'confirmed':'cancelled';store.status(id,next);await reflectStatus(store,telegram,id,messageId,next);}
 else if(action==='ostatus'){const [id,next,page]=rest;store.status(id,next);const mid=store.notificationMessage(id);if(mid&&mid!==messageId)await reflectStatus(store,telegram,id,mid,next);await render(telegram,chatId,messageId,orderDetailView(store,id,Number(page||0)));}
 else if(action==='retry'){const [id,page]=rest;const changes=store.db.prepare("UPDATE notifications SET status='pending',attempts=0,next_at=0,error='' WHERE order_id=? AND status='failed'").run(id).changes;await render(telegram,chatId,messageId,orderDetailView(store,id,Number(page||0)));if(!changes)throw Error('Qayta yuborib bo‘lmadi.');}
 else if(action==='products')await render(telegram,chatId,messageId,productsListView(store,Number(rest[0]||0)));
 else if(action==='product')await render(telegram,chatId,messageId,productDetailView(store,rest[0],Number(rest[1]||0)));
 else if(action==='ptoggle'){const [id,page]=rest;store.toggleProductActive(id);await render(telegram,chatId,messageId,productDetailView(store,id,Number(page||0)));}
 else if(action==='pprice'){const [id,page]=rest;pending.set(String(chatId),{type:'price',id,page:Number(page||0)});await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:'💰 Yangi narxni kiriting (so‘mda, masalan 290000):'});}
 else if(action==='pstock'){const [variantId,productId,page]=rest;pending.set(String(chatId),{type:'stock',id:variantId,productId,page:Number(page||0)});await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:'🔢 Yangi qoldiqni kiriting (masalan 10):'});}
 else if(action==='stats')await render(telegram,chatId,messageId,statsView(store));
 await apiCall(telegram.token,'answerCallbackQuery',{callback_query_id:cb.id});
 }catch(e){await apiCall(telegram.token,'answerCallbackQuery',{callback_query_id:cb.id,text:(e.message||'Xatolik yuz berdi.').slice(0,200),show_alert:true});}
}

async function handleMessage(store,telegram,pending,message){
 const chatId=message.chat?.id;
 const text=String(message.text||'').trim();
 if(String(chatId)!==String(telegram.chatId)){
 if(text==='/start')await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:`Salom! Bu do‘kon administratori uchun bot.\n\nSizning chat ID: ${chatId}\n\nAgar administrator sifatida qo‘shilishingiz kerak bo‘lsa, shu ID'ni egasiga yuboring.`});
 return;
 }
 const key=String(chatId);
 if(text==='/start'||text==='/menu'){pending.delete(key);const v=mainMenuView();await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:v.text,reply_markup:{inline_keyboard:v.keyboard}});return;}
 if(!pending.has(key))return;
 const p=pending.get(key);
 const value=Number(text.replace(/[^\d.-]/g,''));
 if(!Number.isFinite(value)){await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:'Iltimos, raqam kiriting.'});return;}
 try{
 if(p.type==='price')store.setProductPrice(p.id,Math.round(value));
 else if(p.type==='stock')store.setVariantStock(p.id,Math.round(value));
 pending.delete(key);
 const view=productDetailView(store,p.type==='price'?p.id:p.productId,p.page);
 await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:'✅ Saqlandi.\n\n'+view.text,reply_markup:{inline_keyboard:view.keyboard}});
 }catch(e){await apiCall(telegram.token,'sendMessage',{chat_id:chatId,text:'❌ '+(e.message||'Xatolik yuz berdi.')});}
}

export async function handleUpdate(store,telegram,pending,update){
 if(update.callback_query)return handleCallback(store,telegram,pending,update.callback_query);
 if(update.message)return handleMessage(store,telegram,pending,update.message);
}
