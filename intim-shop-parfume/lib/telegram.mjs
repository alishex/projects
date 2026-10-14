const STATUS_LABEL={new:'🆕 Yangi',confirmed:'✅ Tasdiqlangan',preparing:'📦 Tayyorlanmoqda',delivered:'🚚 Yetkazilgan',cancelled:'❌ Bekor qilingan'};

function orderText(o){
 const lines=[`✅ Yangi buyurtma!`,'',`📦 Buyurtma: #${o.id.slice(0,8).toUpperCase()}`,`🕒 ${o.created_at}`,'',`👤 Mijoz: ${o.customer}`,`📱 Telefon: ${o.phone}`,`📍 Manzil: ${o.address}`];
 if(o.lat!=null&&o.lng!=null)lines.push(`🗺 https://maps.google.com/?q=${o.lat},${o.lng}`);
 if(o.note)lines.push(`📝 Izoh: ${o.note}`);
 lines.push('','🛍 Mahsulot(lar):');
 for(const i of o.items)lines.push(` • ${i.name} · ${i.color} / ${i.size} × ${i.quantity} — ${i.price*i.quantity} so‘m`);
 lines.push('',`💰 Jami: ${o.total} so‘m`,`💳 To‘lov: Yetkazilganda (naqd)`);
 return lines.join('\n');
}

export async function apiCall(token,method,payload,fetchImpl=fetch){
 const response=await fetchImpl(`https://api.telegram.org/bot${token}/${method}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(10000)});
 const data=await response.json();
 return {ok:response.ok&&data.ok,data};
}

export async function sendNext(store,{token,chatId,fetchImpl=fetch}){
 if(!token||!chatId)return false;
 const job=store.claimNotification();if(!job)return false;
 const o=store.orderDetails(job.order_id);
 try{
 const keyboard={inline_keyboard:[[{text:'✓ Tasdiqlash',callback_data:`confirm:${o.id}`},{text:'✗ Rad etish',callback_data:`cancel:${o.id}`}]]};
 const sent=await apiCall(token,'sendMessage',{chat_id:chatId,text:orderText(o),reply_markup:keyboard},fetchImpl);
 if(!sent.ok)throw Error('Telegram javobi muvaffaqiyatsiz');
 if(sent.data.result?.message_id)store.setNotificationMessage(o.id,sent.data.result.message_id);
 if(o.lat!=null&&o.lng!=null)await apiCall(token,'sendLocation',{chat_id:chatId,latitude:o.lat,longitude:o.lng},fetchImpl).catch(()=>{});
 store.db.prepare("UPDATE notifications SET status='sent',attempts=attempts+1,error='' WHERE id=?").run(job.id);
 }catch{
 const attempts=job.attempts+1;
 store.db.prepare('UPDATE notifications SET status=?,attempts=?,next_at=?,error=? WHERE id=?').run(attempts>=5?'failed':'pending',attempts,Date.now()+Math.min(3600000,15000*2**attempts),'Telegram bilan aloqa o‘rnatilmadi. Bot va chat sozlamalarini tekshiring.',job.id);
 }
 return true;
}

// Reflects a status change back onto the originally sent Telegram notification message (text updated,
// buttons cleared), regardless of whether the change was triggered by those buttons or the bot admin menu.
export async function reflectStatus(store,{token,chatId,fetchImpl=fetch},orderId,messageId,nextStatus){
 if(!token||!chatId||!messageId)return;
 const o=store.orderDetails(orderId);if(!o)return;
 const text=orderText(o)+`\n\n${STATUS_LABEL[nextStatus]||nextStatus}`;
 await apiCall(token,'editMessageText',{chat_id:chatId,message_id:messageId,text,reply_markup:{inline_keyboard:[]}},fetchImpl).catch(()=>{});
}

export async function setWebhook(token,url,secret,fetchImpl=fetch){
 return apiCall(token,'setWebhook',{url,secret_token:secret,allowed_updates:['callback_query','message']},fetchImpl);
}
