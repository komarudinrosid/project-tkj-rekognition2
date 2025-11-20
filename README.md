# TKJ Rekognition Web

Aplikasi Flask sederhana untuk ambil foto dari kamera HP, upload ke S3, dan cocokkan wajah dengan AWS Rekognition.

## Fitur
- Ambil foto via kamera (browser HP)
- Upload ke `S3`
- Pencocokan wajah dengan `Rekognition` (Face Collection)

## Prasyarat
- `Python 3.10+`
- Akun `AWS` aktif
- Bucket `S3` di region yang sama dengan Rekognition

## Konfigurasi
Isi `.env`:
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=...
REKOGNITION_COLLECTION_ID=...
PORT=5000
```
Instal & jalankan lokal:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a
python app.py
```
Akses dari HP (satu jaringan Wi‑Fi): `http://<IP-LAN-laptop>:5000`

## Setup AWS Rekognition
1. Buat koleksi (sekali saja):
```
aws rekognition create-collection --collection-id my-collection --region ap-southeast-1
```
Set `REKOGNITION_COLLECTION_ID=my-collection` di `.env`.
2. Index wajah ke koleksi (contoh):
```
aws rekognition index-faces \
  --collection-id my-collection \
  --image '{"S3Object":{"Bucket":"NAMA_BUCKET","Name":"path/to/image.jpg"}}' \
  --external-image-id "nama-orang-unik" \
  --region ap-southeast-1
```

## IAM Minimal
Berikan akses menulis ke prefix `uploads/` dan Rekognition search.
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::S3_BUCKET_NAME/uploads/*"
    },
    {
      "Effect": "Allow",
      "Action": ["rekognition:SearchFacesByImage"],
      "Resource": "*"
    }
  ]
}
```
Ganti `S3_BUCKET_NAME` sesuai bucket.

## Deploy Produksi (Gunicorn + Nginx + HTTPS)
1. Siapkan server (Ubuntu):
```
sudo apt update && sudo apt install -y python3-venv nginx
```
2. Copy kode ke `/opt/tkj-rekognition`, instal deps:
```
cd /opt/tkj-rekognition
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Buat `.env` produksi di `/opt/tkj-rekognition/.env`.
4. Uji Gunicorn:
```
source .venv/bin/activate
set -a && source .env && set +a
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```
5. Buat service systemd:
```
sudo tee /etc/systemd/system/tkj-rekognition.service >/dev/null <<'UNIT'
[Unit]
Description=TKJ Rekognition Flask App
After=network.target

[Service]
WorkingDirectory=/opt/tkj-rekognition
EnvironmentFile=/opt/tkj-rekognition/.env
ExecStart=/opt/tkj-rekognition/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now tkj-rekognition
```
6. Konfigurasi Nginx + HTTPS:
```
sudo tee /etc/nginx/sites-available/tkj-rekognition >/dev/null <<'NGINX'
server {
  listen 80;
  server_name your.domain.com;
  location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
NGINX
sudo ln -s /etc/nginx/sites-available/tkj-rekognition /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

## Verifikasi
- Ambil foto di halaman utama, upload.
- Respons berisi `bucket`, `key`, dan jika koleksi di-set, `matches` dengan `similarity`.
- Pastikan file muncul di `S3` prefix `uploads/`.

## Troubleshooting
- Kamera HP butuh HTTPS; gunakan domain + TLS atau tunnel (`cloudflared`/`ngrok`).
- `AccessDenied` S3: cek IAM dan region.
- `ResourceNotFoundException` Rekognition: cek `REKOGNITION_COLLECTION_ID`.

## Keamanan
- Jangan hardcode kredensial; pakai `.env`/AWS Profile.
- Objek S3 tetap private.
- IAM minimal sesuai kebutuhan.