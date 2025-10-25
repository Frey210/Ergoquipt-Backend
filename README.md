# ⚙️ Ergoquipt Reaction-Time System

Ergoquipt adalah sistem terintegrasi untuk **praktikum laboratorium ergonomi dan fisiologi** yang mengukur **reaksi waktu, suhu tubuh (tympanic), dan data vital (HR/HRV/SpO₂)**. Sistem ini menghubungkan **perangkat ESP32**, **backend FastAPI**, serta **aplikasi mobile dan web dashboard** untuk otomatisasi eksperimen.

---

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph Frontend Applications
        A[Mobile App<br/>Flutter/React Native]
        B[Web Dashboard<br/>React/Next.js]
    end

    subgraph Cloud Infrastructure
        C[FastAPI Backend<br/>Raspberry Pi]
        D[PostgreSQL Database]
        E[Cloudflare Tunnel<br/>HTTPS Secure Access]
    end

    subgraph Reaction Time System
        F[ESP32 Server<br/>WiFi WebSocket]
        G[ESP32 Client 1<br/>LED/Sound Test]
        H[ESP32 Client 2<br/>Visual Test]
    end

    subgraph Medical Devices
        I[Tympanic Thermometer<br/>BLE Connection]
        J[HRV Band<br/>BLE Connection]
    end

    %% Mobile App Connections
    A -->|WebSocket<br/>WiFi Local| F
    A -->|BLE Connection| I
    A -->|BLE Connection| J
    
    %% ESP32 Internal Network
    F -->|WebSocket/HTTP<br/>WiFi Local| G
    F -->|WebSocket/HTTP<br/>WiFi Local| H
    
    %% Cloud Connections
    A -->|HTTPS via<br/>Cloudflare Tunnel| C
    B -->|HTTPS via<br/>Cloudflare Tunnel| C
    C --> D

    style A fill:#e1f5fe
    style B fill:#e1f5fe
    style C fill:#f3e5f5
    style D fill:#f3e5f5
    style E fill:#f3e5f5
    style F fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#e8f5e8
    style I fill:#fff3e0
    style J fill:#fff3e0
```

---

## 🔄 Complete Data Flow

```mermaid
sequenceDiagram
    participant O as Operator Mobile App
    participant RT as Reaction Time System
    participant TY as Tympanic Thermometer
    participant HR as HRV Band
    participant B as Backend API
    participant DB as Database

    Note over O,DB: Session Initialization
    O->>B: POST /sessions (Create New Session)
    B->>DB: Store Session Data
    B->>O: Return Session ID & Config
    
    Note over O,DB: Device Connection Phase
    O->>RT: WebSocket Connect (WiFi Local)
    O->>TY: BLE Connect & Pair
    O->>HR: BLE Connect & Pair
    
    Note over O,DB: Measurement Phase
    O->>RT: Start Reaction Test
    RT->>RT: Trigger Stimulus (LED/Sound/Visual)
    RT->>O: Send Reaction Times via WebSocket
    
    O->>TY: Request Temperature Reading
    TY->>O: Send Temperature Data via BLE
    
    O->>HR: Start Vital Monitoring
    HR->>O: Stream HR/HRV/SpO₂ via BLE
    
    Note over O,DB: Data Synchronization
    O->>B: POST /sessions/{id}/events/reaction
    O->>B: POST /sessions/{id}/events/tympani
    O->>B: POST /sessions/{id}/events/vitals
    B->>DB: Store All Measurement Data
    B->>O: Acknowledgement
    
    Note over O,DB: Session Completion
    O->>B: PATCH /sessions/{id}/end
    O->>RT: WebSocket Disconnect
    O->>TY: BLE Disconnect
    O->>HR: BLE Disconnect
```

---

## 📡 Communication Protocols

| Komponen | Protocol | Kecepatan | Jarak | Use Case |
|----------|----------|-----------|--------|----------|
| **ESP32 Network** | WebSocket/WiFi | High (~150 Mbps) | Medium (~50m) | Real-time reaction data |
| **Tympanic Thermometer** | BLE 5.0 | Low (~2 Mbps) | Short (~10m) | Periodic temperature readings |
| **HRV Band** | BLE 5.0 | Medium (~10 Mbps) | Short (~10m) | Continuous vital monitoring |
| **Mobile ↔ Backend** | HTTPS/SSL | High | Unlimited | Data sync & management |
| **Web Dashboard** | HTTPS/SSL | High | Unlimited | Analytics & reporting |

---

## 🧠 Firmware Architecture

Terdapat tiga firmware independen berbasis ESP32:

| Perangkat | Fungsi Utama | Connectivity | Data Flow |
|-----------|--------------|--------------|-----------|
| **ESP32 Server** | Koordinasi stimulus, aggregasi data | WiFi + WebSocket | Mobile App ↔ Clients |
| **ESP32 Client 1** | LED/Sound reaction test | WiFi HTTP | Server → Response Time |
| **ESP32 Client 2** | Visual reaction test | WiFi HTTP | Server → Response Time |

---

## 🗄️ Database Schema

```mermaid
erDiagram
    users {
        uuid id PK
        varchar username
        varchar email
        varchar password_hash
        varchar full_name
        varchar university
        varchar role
        varchar status
        varchar registration_type
        uuid created_by FK
        boolean initial_password
        varchar platform_access
        datetime created_at
        datetime updated_at
    }

    user_registration_logs {
        uuid id PK
        uuid admin_id FK
        uuid operator_id FK
        varchar action
        text notes
        varchar ip_address
        datetime created_at
    }

    respondents {
        uuid id PK
        varchar guest_name
        varchar gender
        int age
        int height
        int weight
        varchar status
        varchar university
        uuid created_by FK
        datetime created_at
    }

    sessions {
        uuid id PK
        varchar session_code
        uuid operator_id FK
        uuid respondent_id FK
        varchar test_type
        varchar device_id
        varchar device_name
        varchar status
        text measurement_context
        text environment_notes
        text additional_notes
        json local_data
        int trials_completed
        int total_trials
        datetime started_at
        datetime ended_at
        datetime created_at
        datetime updated_at
    }

    session_configs {
        uuid id PK
        uuid session_id FK
        varchar config_type
        varchar stimulus_type
        varchar stimulus_category
        int trials_per_stimulus
        int order_index
        int measurement_duration
        int sampling_interval
        text target_condition
        datetime created_at
    }

    reaction_trials {
        uuid id PK
        uuid session_id FK
        varchar stimulus_type
        varchar stimulus_category
        int response_time
        int trial_number
        varchar reaction_type
        datetime created_at
    }

    tympani_readings {
        uuid id PK
        uuid session_id FK
        decimal temperature
        int reading_number
        varchar measurement_phase
        varchar body_position
        decimal environment_temp
        datetime reading_time
        datetime created_at
    }

    vital_readings {
        uuid id PK
        uuid session_id FK
        int heart_rate
        decimal heart_rate_variability
        int spo2
        int reading_number
        varchar measurement_phase
        varchar activity_context
        varchar body_position
        datetime reading_time
        datetime created_at
    }

    users ||--o{ user_registration_logs : "admin_creates"
    users ||--o{ user_registration_logs : "operator_registered"
    users ||--o{ respondents : "creates"
    users ||--o{ sessions : "operates"
    respondents ||--o{ sessions : "participates_in"
    sessions ||--o{ session_configs : "configures"
    sessions ||--o{ reaction_trials : "records_reactions"
    sessions ||--o{ tympani_readings : "records_temperature"
    sessions ||--o{ vital_readings : "records_vitals"
```

---

## 🖥️ Backend API Endpoints

### 🔐 Authentication & Users
```http
POST   /auth/login
POST   /admin/users
GET    /admin/users
PUT    /admin/users/{user_id}
```

### 👥 Respondents Management
```http
POST   /respondents
GET    /respondents
PUT    /respondents/{id}
```

### 🧪 Session Management
```http
POST   /sessions
GET    /sessions
PATCH  /sessions/{id}/end
PUT    /sessions/{id}
```

### 📊 Data Collection
```http
POST   /sessions/{id}/events/reaction
POST   /sessions/{id}/events/tympani
POST   /sessions/{id}/events/vitals
GET    /sessions/{id}/export.csv
```

---

## 🔒 Security Architecture

| Layer | Security Measure | Implementation |
|-------|------------------|----------------|
| **Network** | HTTPS + SSL/TLS | Cloudflare Tunnel |
| **Authentication** | JWT Tokens | Bearer Token Authentication |
| **Data Integrity** | UUID Primary Keys | Prevent ID guessing |
| **API Security** | Rate Limiting | Request throttling |
| **BLE Security** | Pairing & Bonding | Secure device connection |

---

## 🚀 Deployment Specifications

### Backend Infrastructure
- **Server**: Raspberry Pi 4 (4GB RAM)
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 13+
- **Reverse Proxy**: Nginx
- **Tunnel**: Cloudflare Tunnel

### Network Configuration
```yaml
WiFi Network:
  SSID: "Ergoquipt-Lab"
  Security: WPA2-Enterprise
  Band: 2.4GHz & 5GHz

BLE Devices:
  Tympanic: Service UUID: 0x1809
  HRV Band: Service UUID: 0x180D
```

---

## 🐍 Python Environment Setup

### Prerequisites
- **Python 3.11** (Recommended)
- **PostgreSQL 13+**
- **Virtual Environment** (venv)

### Deployment Environment Setup

```bash
# 1. Update system and install Python 3.11
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# 2. Create project directory
mkdir -p /opt/ergoquipt
cd /opt/ergoquipt

# 3. Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 4. Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# 5. Install dependencies
pip install -r requirements.txt

# 6. Environment configuration
cp .env.example .env
# Edit .env with your specific settings
```

### Environment Variables (.env)
```bash
# Database Configuration
DATABASE_URL=postgresql://ergoquipt_user:password@localhost:5432/ergoquipt

# Security
SECRET_KEY=your-super-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Production Service Configuration

Create systemd service file `/etc/systemd/system/ergoquipt.service`:

```ini
[Unit]
Description=Ergoquipt FastAPI Backend
After=network.target postgresql.service

[Service]
Type=exec
User=ergoquipt
Group=ergoquipt
WorkingDirectory=/opt/ergoquipt
Environment=PATH=/opt/ergoquipt/venv/bin
ExecStart=/opt/ergoquipt/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration

`/etc/nginx/sites-available/ergoquipt`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Startup Commands

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable ergoquipt
sudo systemctl start ergoquipt
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status ergoquipt
sudo systemctl status nginx
```

### Monitoring and Logs

```bash
# View application logs
sudo journalctl -u ergoquipt -f

# Check service status
sudo systemctl status ergoquipt

# Database backups (add to crontab)
0 2 * * * pg_dump -U ergoquipt_user ergoquipt > /backups/ergoquipt_$(date +%Y%m%d).sql
```

---

## 📱 Mobile App Features

### Device Management
- **ESP32 Network**: Auto-discovery & WebSocket management
- **BLE Devices**: Scanning, pairing, and data collection
- **Data Sync**: Real-time synchronization to backend

### Measurement Modules
- Reaction Time Test (Visual/LED/Sound)
- Tympanic Temperature Reading
- Continuous Vital Signs Monitoring

---

## 🔧 Development Setup

```bash
# Clone repository
git clone https://github.com/ergoquipt/ergoquipt-system.git
cd ergoquipt-system

# Backend setup with Python 3.11 virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Access API documentation
# Local: http://127.0.0.1:8000/docs
# Production: https://ergoquipt.inkubasistartupunhas.id/docs
```

---

## 📚 API Documentation

Live API documentation available at:
👉 **[https://ergoquipt.inkubasistartupunhas.id/docs](https://ergoquipt.inkubasistartupunhas.id/docs)**

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🏷️ Acknowledgements

Developed by **Ergoquipt Team**, part of the **Inkubator Startup Universitas Hasanuddin** initiative.

---

**✨ Revolutionizing Ergonomics Research with Integrated Physiological Monitoring**