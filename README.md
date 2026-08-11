# Face Detection MEC — 5G AI Edge Testbed

Repository ini berisi backend **Face Detection MEC** yang digunakan pada testbed 5G SA berbasis **Open5GS + K3s**.

Service ini berjalan sebagai **sidecar container** pada workload Edge UPF RAN1 sehingga backend Face Detection berada pada network namespace yang sama dengan UPF dan dapat diakses langsung dari UE MEC melalui:

```text
http://172.16.49.1:5002
```

---

## 1. Arsitektur

Alur utama Face Detection MEC:

```text
UE / UERANSIM
     |
     | DNN: mec.icn.testbed
     | UE subnet: 172.16.49.0/24
     v
Edge UPF RAN1
172.16.49.1
     |
     | Sidecar container
     v
Face Detection MEC
172.16.49.1:5002
     |
     v
Detection Result
```

Komponen utama:

| Komponen | Nilai |
|---|---|
| 5G Core | `10.34.211.6` |
| RAN1 / MEC Node | `10.34.211.157` |
| Kubernetes Node | `riset-5g` |
| Namespace | `open5gs` |
| DNN | `mec.icn.testbed` |
| MEC UE Subnet | `172.16.49.0/24` |
| MEC Gateway | `172.16.49.1` |
| Face Detection Port | `5002` |
| Health Endpoint | `/health` |
| Detection Endpoint | `/detect` |

---

## 2. Repository Structure

Struktur repository:

```text
face-detection-mec/
├── backend/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── k8s/
│   └── mec-sidecar-patch.yaml
│
├── README.md
└── .gitignore
```

Repository ini hanya berisi komponen yang diperlukan untuk **Face Detection MEC**.

UE Discovery Agent dikelola terpisah pada repository UE sehingga tidak perlu disimpan di repository ini.

---

## 3. Cara Kerja

Face Detection MEC menerima image dari client atau UE melalui HTTP.

Endpoint utama:

```text
GET  /health
POST /detect
```

Service berjalan pada:

```text
http://172.16.49.1:5002
```

Karena backend dijalankan sebagai sidecar pada Edge UPF, backend dapat menggunakan interface/network yang sama dengan UPF.

Hal ini memungkinkan UE dengan DNN:

```text
mec.icn.testbed
```

untuk mengakses backend melalui:

```text
172.16.49.1:5002
```

tanpa perlu membuat Kubernetes NodePort terpisah.

---

## 4. Requirements

Environment build membutuhkan:

- Docker
- Python 3
- OpenCV dependency dari `requirements.txt`
- akses ke cluster K3s
- `kubectl`
- image runtime tersedia pada node `riset-5g`

Cek:

```bash
docker --version
python3 --version
kubectl version --client
```

---

## 5. Backend

Source backend berada di:

```text
backend/
```

Contoh isi:

```text
backend/
├── app.py
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

Backend menyediakan endpoint:

```text
/health
/detect
```

Jika implementasi juga menyediakan alias seperti:

```text
/face/health
/face/detect
```

endpoint tersebut dapat tetap digunakan sesuai implementasi `app.py`.

---

## 6. Build Docker Image

Masuk ke folder backend:

```bash
cd backend
```

Build:

```bash
docker build \
  -t face-detection-mec:v1 .
```

Cek image:

```bash
docker images | grep face-detection-mec
```

Expected:

```text
face-detection-mec   v1
```

---

## 7. Test Container Secara Lokal

Jalankan container untuk test:

```bash
docker run --rm \
  -p 5002:5002 \
  -e PORT=5002 \
  face-detection-mec:v1
```

Terminal lain:

```bash
curl \
  http://127.0.0.1:5002/health
```

Jika berhasil, backend siap digunakan.

---

## 8. Kubernetes Deployment Model

Face Detection MEC **tidak dijalankan sebagai Deployment Kubernetes terpisah**.

Service menggunakan model:

```text
Edge UPF Pod
├── UPF
├── MEC Robot
└── Face Detection MEC
```

Dengan model tersebut, Face Detection MEC share network namespace dengan Edge UPF.

Karena itu endpoint:

```text
172.16.49.1:5002
```

dapat digunakan langsung oleh UE MEC.

---

## 9. MEC Sidecar Manifest

Manifest Kubernetes berada di:

```text
k8s/mec-sidecar-patch.yaml
```

Manifest harus menambahkan container:

```yaml
- name: face-detection-mec
  image: docker.io/library/face-detection-mec:v1
  imagePullPolicy: Never

  env:
    - name: PORT
      value: "5002"

  ports:
    - name: face-http
      containerPort: 5002
      protocol: TCP
```

Health probe direkomendasikan:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 5002
  initialDelaySeconds: 5
  periodSeconds: 10

livenessProbe:
  httpGet:
    path: /health
    port: 5002
  initialDelaySeconds: 15
  periodSeconds: 20
```

> Pastikan `mec-sidecar-patch.yaml` mengikuti struktur resource Edge UPF yang sedang digunakan pada cluster.

---

## 10. Cek Edge UPF

Lihat workload:

```bash
kubectl get pods \
  -n open5gs \
  -o wide | grep upf-edge
```

Cek container di pod Edge UPF:

```bash
kubectl get pod \
  -n open5gs \
  upf-edge-icn-0 \
  -o jsonpath='{range .spec.containers[*]}{.name}{" -> "}{.image}{"\n"}{end}'
```

Expected salah satu container:

```text
face-detection-mec -> docker.io/library/face-detection-mec:v1
```

---

## 11. Apply Sidecar Configuration

Apply manifest sesuai metode deployment cluster.

Contoh:

```bash
kubectl apply \
  -f k8s/mec-sidecar-patch.yaml
```

Kemudian pantau:

```bash
kubectl get pods \
  -n open5gs \
  -o wide | grep upf-edge
```

Jika resource menggunakan StatefulSet:

```bash
kubectl rollout status \
  statefulset/upf-edge-icn \
  -n open5gs
```

---

## 12. Cek Container

Cek semua container:

```bash
kubectl get pod \
  -n open5gs \
  upf-edge-icn-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" -> "}{.ready}{"\n"}{end}'
```

Face Detection MEC harus menunjukkan:

```text
face-detection-mec -> true
```

---

## 13. Logs

Jika container berada pada pod:

```text
upf-edge-icn-0
```

lihat log:

```bash
kubectl logs \
  -n open5gs \
  upf-edge-icn-0 \
  -c face-detection-mec \
  -f
```

Last 100 lines:

```bash
kubectl logs \
  -n open5gs \
  upf-edge-icn-0 \
  -c face-detection-mec \
  --tail=100
```

---

## 14. Test Health

Dari host yang dapat mengakses network MEC:

```bash
curl \
  http://172.16.49.1:5002/health
```

Expected:

```text
HTTP 200
```

---

## 15. Test Face Detection

Contoh menggunakan image:

```bash
curl -X POST \
  http://172.16.49.1:5002/detect \
  -F "image=@test.jpg"
```

Nama multipart field dapat disesuaikan dengan implementasi `app.py`.

---

## 16. Test dari UE MEC

Pastikan UE sudah memiliki IP dari subnet MEC:

```bash
ip -br a | grep 172.16.49
```

Contoh:

```text
uesimtunX   UNKNOWN   172.16.49.x/16
```

Test health menggunakan interface UE:

```bash
curl \
  --interface 172.16.49.x \
  http://172.16.49.1:5002/health
```

Test detection:

```bash
curl \
  --interface 172.16.49.x \
  -X POST \
  http://172.16.49.1:5002/detect \
  -F "image=@test.jpg"
```

Ganti:

```text
172.16.49.x
```

dengan IP UE aktual.

---

## 17. Integrasi UE Web App

Face Detection MEC digunakan oleh UE Web App melalui base URL:

```text
http://172.16.49.1:5002
```

Contoh environment:

```bash
FACE_DETECT_BASE_URL=http://172.16.49.1:5002
```

Health URL:

```text
http://172.16.49.1:5002/health
```

Detection URL:

```text
http://172.16.49.1:5002/detect
```

---

## 18. UE Discovery Agent Allowlist

Jika request diteruskan melalui UE Discovery Agent, endpoint harus masuk exact-match allowlist.

Tambahkan:

```text
http://172.16.49.1:5002/health
http://172.16.49.1:5002/detect
```

Config agent:

```text
~/.config/ue-discovery-agent.env
```

Setelah update:

```bash
systemctl --user restart \
  ue-discovery-agent.service
```

Cek log:

```bash
journalctl --user \
  -u ue-discovery-agent.service \
  -n 50 \
  --no-pager
```

---

## 19. Update Image

Build versi baru:

```bash
cd backend
```

```bash
docker build \
  -t face-detection-mec:v2 .
```

Update image di manifest:

```yaml
image: docker.io/library/face-detection-mec:v2
```

Apply kembali:

```bash
kubectl apply \
  -f k8s/mec-sidecar-patch.yaml
```

Pantau Edge UPF:

```bash
kubectl get pods \
  -n open5gs \
  -o wide | grep upf-edge
```

---

## 20. Troubleshooting

### Health Endpoint Tidak Bisa Diakses

Cek container:

```bash
kubectl get pod \
  -n open5gs \
  upf-edge-icn-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" -> "}{.ready}{"\n"}{end}'
```

Cek log:

```bash
kubectl logs \
  -n open5gs \
  upf-edge-icn-0 \
  -c face-detection-mec \
  --tail=100
```

---

### `Connection Refused`

Pastikan backend listen pada:

```text
0.0.0.0:5002
```

bukan hanya:

```text
127.0.0.1:5002
```

---

### Image Tidak Ditemukan

Jika menggunakan:

```yaml
imagePullPolicy: Never
```

image harus tersedia secara lokal pada node tempat Edge UPF berjalan.

Cek:

```bash
docker images | grep face-detection-mec
```

---

### `/detect` Gagal tetapi `/health` Berhasil

Cek:

- request method harus `POST`
- nama multipart field
- format image
- ukuran image
- dependency OpenCV
- log backend

```bash
kubectl logs \
  -n open5gs \
  upf-edge-icn-0 \
  -c face-detection-mec \
  -f
```

---

### UE Tidak Bisa Mengakses MEC

Pastikan UE menggunakan:

```text
DNN = mec.icn.testbed
```

dan mendapat IP:

```text
172.16.49.x
```

Cek:

```bash
ip -br a | grep 172.16.49
```

Test:

```bash
curl \
  --interface 172.16.49.x \
  http://172.16.49.1:5002/health
```

---

### `target-denied`

Jika menggunakan UE Discovery Agent, tambahkan:

```text
http://172.16.49.1:5002/health
http://172.16.49.1:5002/detect
```

ke allowlist agent.

---

## 21. Quick Start

Build image:

```bash
cd backend

docker build \
  -t face-detection-mec:v1 .
```

Apply sidecar manifest:

```bash
kubectl apply \
  -f ../k8s/mec-sidecar-patch.yaml
```

Cek container:

```bash
kubectl get pod \
  -n open5gs \
  upf-edge-icn-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" -> "}{.ready}{"\n"}{end}'
```

Health:

```bash
curl \
  http://172.16.49.1:5002/health
```

Logs:

```bash
kubectl logs \
  -n open5gs \
  upf-edge-icn-0 \
  -c face-detection-mec \
  -f
```

---

## 22. Security Notes

Jangan commit:

- password
- API token
- private key
- `.env`
- credential production
- sensitive images
- runtime logs

Contoh `.gitignore`:

```gitignore
__pycache__/
*.py[cod]

.env
*.env

.venv/
venv/

*.log
*.tmp
*.pid

*.backup
*.bak

.vscode/
.idea/

.DS_Store
Thumbs.db
```

---

## Maintainer

5G AI Edge Testbed

GitHub Organization:

```text
5g-ai-edge-research
```
