import {createStore,passwordHash} from '../lib/store.mjs';
import {randomBytes} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
try{process.loadEnvFile(path.join(root,'.env'))}catch(e){if(e.code!=='ENOENT')throw e}
const store=createStore(process.env.DATA_DIR||path.join(root,'data'));
const password=randomBytes(15).toString('base64url');
const admin=store.db.prepare('SELECT id,email FROM admins LIMIT 1').get();
if(!admin){console.error('Avval npm start bilan serverni bir marta ishga tushiring.');process.exit(1)}
store.transact(()=>{store.db.prepare('UPDATE admins SET password=? WHERE id=?').run(passwordHash(password),admin.id);store.db.prepare('DELETE FROM sessions').run()});
console.log('Email:',admin.email,'\nYangi parol (saqlab oling):',password);
store.db.close();
