# TimeKpr WebUI

A web-based interface for managing TimeKpr parental controls across multiple computers in your network.

![Timekpr Dashboard](docs/dashboard.png)

## Features

- **Remote Management**: Control multiple computers running TimeKpr from a single web interface
- **Time Adjustments**: Add or remove time for users on remote systems
- **Usage Tracking**: View daily and weekly usage statistics with interactive charts
- **Weekly Scheduling**: Set different time limits for each day of the week
- **Real-time Sync Status**: Live updates of synchronization status without page refresh
- **User Management**: Add, validate, and monitor users across different systems
- **Background Synchronization**: Automatic synchronization of settings and time adjustments
- **Responsive Design**: Works on desktop and mobile devices

---

## 🚀 Getting Started

### Prerequisites

Before running TimeKpr WebUI, ensure you have:
- **Docker and Docker Compose** installed on your system
- **TimeKpr-nExT** installed on all target computers you want to manage
- **Network access** between the WebUI host and target computers

### 1. Quick Setup with Docker

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/timekpr-ui.git
cd timekpr-ui
```

2. **Start with Docker Compose:**
```bash
docker-compose up -d
```

This will build the container and start the application on `http://localhost:5000`

### 2. First Login and Password Setup

1. **Open your browser** and navigate to `http://localhost:5000`
2. **Login with default credentials:**
   - Username: `admin`
   - Password: `admin`

3. **⚠️ IMPORTANT - Change Password Immediately:**
   - Go to **Settings** page
   - Change the default password
   - This password will be used for both web login AND SSH connections to managed computers

### 3. Remote System Configuration

For **each computer** you want to manage remotely:

#### Install TimeKpr-nExT:
```bash
sudo apt update
sudo apt install timekpr-next
```

#### Create dedicated management user:
```bash
sudo adduser timekpr-remote
sudo usermod -aG timekpr timekpr-remote
```

#### Set password (must match your web admin password):
```bash
sudo passwd timekpr-remote
# Enter the SAME password you set in the web interface
```

#### Verify SSH access:
```bash
# Test from the WebUI host machine
ssh timekpr-remote@TARGET_COMPUTER_IP
```

### 4. Add Your First User

1. Go to **Admin** panel in the web interface
2. Click **"Add User"**
3. Enter:
   - **Username**: The actual user account on the remote computer
   - **System IP**: IP address of the remote computer
4. Click **"Add User"** - the system will automatically validate the connection

---

## 📊 Daily Usage

### Dashboard Overview

The main dashboard provides a comprehensive view of all managed users:

![Dashboard](docs/dashboard.png)
*Real-time view of all users with usage charts, time remaining, and sync status*

#### Key Features:
- **📈 Usage Charts**: Weekly usage history with weekend highlighting
- **⏱️ Time Left Today**: Current remaining time for each user
- **🔄 Sync Status**: Real-time indicators for pending changes
- **⚡ Quick Actions**: Instant time adjustments and schedule access

### Time Management

#### Adjusting Time Limits
1. Click **"Adjust Time"** on any user card
2. Use **+15m/-15m** buttons or set custom amounts
3. Changes apply immediately if the computer is online
4. Offline computers receive updates when they come back online

![Time Adjustment](docs/time-adjust.png)
*Modern toast notifications replace old popup dialogs*

#### Weekly Scheduling
1. Click **"Schedule"** for detailed time management
2. Set different time limits for each day of the week
3. **Weekdays vs Weekends**: Visual distinction in charts
4. **Real-time Sync**: Status badges update automatically every 5 seconds

![Weekly Schedule](docs/schedule.png)
*Comprehensive weekly schedule management with sync status*

### Administrative Functions

#### User Management
- **Add/Remove Users**: Manage users across multiple computers
- **Validation Status**: Real-time connection verification
- **Usage History**: Track patterns and trends

#### System Monitoring
- **Background Tasks**: Automatic sync monitoring (hidden when working properly)
- **Error Handling**: Smart notifications appear only when issues need attention
- **Connection Status**: Live indicators for each managed system

### Background Synchronization

The system continuously monitors and synchronizes:
- ✅ **Time adjustments** for offline computers
- ✅ **Weekly schedule changes**
- ✅ **Usage data collection** every 10 seconds
- ✅ **Automatic retry** for failed connections

#### Sync Status Indicators:
- **🟢 Hidden**: Everything working normally
- **🟡 "Schedule Not Synced"**: Changes pending sync
- **🔴 Error indicators**: Issues requiring attention

### Mobile-Friendly Interface

The responsive design works seamlessly on:
- **📱 Smartphones**: Touch-optimized controls
- **📱 Tablets**: Adaptive grid layouts  
- **💻 Desktop**: Full feature access

---

## 🔧 Advanced Configuration

### Environment Variables
- `FLASK_ENV`: Development mode (default: production)
- Custom database paths and network settings available

### Docker Customization
```yaml
# docker-compose.yml modifications
ports:
  - "8080:5000"  # Change port binding
volumes:
  - ./data:/app/data  # Persistent data storage
```

### Troubleshooting
- **Connection Issues**: Verify SSH access and user permissions
- **Sync Problems**: Check background task status in dashboard
- **Performance**: Monitor system resources for large user bases

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description

## 📄 License

MIT License - see LICENSE file for details.

## Acknowledgements

- This project works with [Timekpr-nExT](https://mjasnik.gitlab.io/timekpr-next/), a parental control tool for Linux
- Built with Flask, SQLAlchemy, and Paramiko
- Inspired by [timekpr-next-remote](https://github.com/mrjones-plip/timekpr-next-remote) - Main reason for creating this version was the need for background service that applies changes to PCs that are currently powered down.