// Admin tools — SSH-only, never exposed over HTTP (see service.js comment on
// grantAdmin). IMPORTANT: the store is a single JSON file loaded into memory
// by whichever process opens it — this CLI and the server do not share state
// while both running. Stop the server first, or a subsequent write from the
// still-running server will silently overwrite what this CLI just wrote:
//   systemctl stop shifokor-server
//   node server/cli.mjs grant-admin <email>
//   systemctl start shifokor-server
// Usage:
//   node server/cli.mjs list-users
//   node server/cli.mjs grant-admin <email>
import { service, store, waitForPersist } from './context.mjs';

const [, , cmd, arg] = process.argv;

async function main() {
  if (cmd === 'grant-admin') {
    if (!arg) throw new Error('usage: node server/cli.mjs grant-admin <email>');
    const user = service.grantAdmin(arg);
    await waitForPersist();
    console.log(`OK — ${user.email} (${user.fullName}) is now admin.`);
    return;
  }
  if (cmd === 'list-users') {
    const users = store.all('users').map(({ passwordHash, licenseNumber, ...u }) => u);
    if (!users.length) { console.log('(no users registered yet)'); return; }
    for (const u of users) {
      console.log(`${u.email}  role=${u.role}  specialty=${u.specialty || u.studyDirection || '-'}  admin=${u.isAdmin}  verification=${u.verification}`);
    }
    return;
  }
  console.log('Usage:\n  node server/cli.mjs list-users\n  node server/cli.mjs grant-admin <email>');
}

main().catch((e) => {
  console.error('Error:', e.message);
  process.exitCode = 1;
});
