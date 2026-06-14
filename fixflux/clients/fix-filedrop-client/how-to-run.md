## 🚀 How to run
python clients/fix-filedrop-client/watcher.py

## 🧪 How to test
drop file:
clients/fix-filedrop-client/filedrop/order1.txt

## ✅ Expected behavior

Valid file
→ moved to processed/
→ event sent to Kafka
→ system processes trade

Invalid file
→ moved to rejected/
→ error logged