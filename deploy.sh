#!/bin/bash
echo "=== Pulling latest code ==="
cd /opt/AllmaxProjects
git pull origin master

echo ""
echo "=== Restarting all services ==="
for svc in shohjahon ali-bot asilbek-bot hr-bot allmaxtg instagramdm intagratsiya; do
    systemctl restart $svc
    STATUS=$(systemctl is-active $svc)
    printf "  %-15s %s\n" "$svc" "$STATUS"
done

echo ""
echo "=== Deploy complete ==="
