# Health Monitoring & Status Page System

## 🏥 Overview

Your Driver App backend now includes a comprehensive health monitoring and status page system that provides real-time monitoring of all API endpoints, system metrics, and service health status.

## ✅ Features Implemented

### 🔍 **Health Monitoring**
- ✅ **Endpoint Monitoring** - Automatic health checks for all API endpoints
- ✅ **Response Time Tracking** - Monitor API response times and performance
- ✅ **Uptime Calculation** - 24-hour uptime percentages for each service
- ✅ **System Metrics** - CPU, memory, disk usage, and database performance
- ✅ **Request Logging** - Complete API request/response logging with metrics
- ✅ **Error Detection** - Automatic detection of slow requests and errors

### 📊 **Status Page**
- ✅ **Public Status Dashboard** - Beautiful HTML status page for users
- ✅ **Real-time Updates** - Auto-refreshing status information
- ✅ **Service Overview** - Visual indicators for all monitored services
- ✅ **Incident Tracking** - Record and display service incidents
- ✅ **Historical Data** - Charts and metrics over time
- ✅ **Mobile Responsive** - Works perfectly on all devices

### ⚡ **Background Monitoring**
- ✅ **Celery Tasks** - Automated background health checks
- ✅ **Scheduled Monitoring** - Configurable check intervals
- ✅ **Alerting System** - Detect and alert on service issues
- ✅ **Data Cleanup** - Automatic cleanup of old monitoring data
- ✅ **Performance Reports** - Daily system performance reports

## 🌐 **Endpoints & URLs**

### Public Status Page
```
http://localhost:8000/health/status-page/
```

### Basic Health Check
```
http://localhost:8000/health/
```

### Health API Endpoints
```
GET  /health/api/overview/                    - Health overview
GET  /health/api/endpoints/                   - All endpoints health
GET  /health/api/endpoints/{id}/             - Specific endpoint health
GET  /health/api/metrics/                     - System metrics (auth required)
GET  /health/api/logs/                        - Request logs (auth required)
GET  /health/api/incidents/                   - Incidents (auth required)
POST /health/api/run-health-checks/           - Manual health check (staff required)
```

### Status Page Data API (AJAX)
```
GET  /health/status-page-api/                - JSON data for status page
```

## 📈 **Monitored Endpoints**

The system automatically monitors these endpoints:

| Service | Endpoint | Method | Check Interval |
|---------|----------|--------|----------------|
| API Root | `/` | GET | 2 minutes |
| Health Check | `/health/` | GET | 1 minute |
| User Registration | `/api/v1/auth/register/` | POST | 5 minutes |
| User Login | `/api/v1/auth/login/` | POST | 5 minutes |
| OAuth Applications | `/api/v1/auth/oauth/applications/` | GET | 10 minutes |
| Health Overview API | `/health/api/overview/` | GET | 5 minutes |
| Status Page | `/health/status-page/` | GET | 5 minutes |
| Admin Panel | `/admin/` | GET | 10 minutes |

## 🛠️ **Management Commands**

### Setup Health Monitoring
```bash
python manage.py setup_health_monitoring
```

### Run Health Checks
```bash
# Check all endpoints
python manage.py run_health_checks

# Check specific endpoint
python manage.py run_health_checks --endpoint "API Root"

# Include system metrics
python manage.py run_health_checks --collect-metrics
```

## 🔧 **Configuration**

### Status Page Settings
Configure the status page appearance and behavior in Django admin:
- **URL**: http://localhost:8000/admin/health/statuspagesettings/
- **Settings**: Page title, description, colors, refresh interval
- **Features**: Toggle response times, uptime percentages, incident history

### Monitoring Endpoints
Add/modify monitored endpoints in Django admin:
- **URL**: http://localhost:8000/admin/health/serviceendpoint/
- **Configure**: Check intervals, timeout settings, expected status codes
- **Actions**: Enable/disable monitoring, manual health checks

## 📊 **Metrics & Analytics**

### System Metrics Collected
- **CPU Usage** - Current CPU utilization percentage
- **Memory Usage** - RAM usage in MB and percentage
- **Disk Usage** - Disk space utilization percentage
- **Database Performance** - Connection times and query counts
- **Request Statistics** - Total requests, error rates, response times
- **External Services** - Twilio, AfricasTalking, Email service status

### Request Logging
All API requests are automatically logged with:
- **Response Time** - Precise timing in seconds
- **Status Codes** - HTTP response codes
- **User Information** - Authenticated user details
- **IP Addresses** - Client IP tracking
- **Error Details** - Full error messages for failed requests
- **Request Size** - Payload and response sizes

## 🎨 **Status Page Features**

### Visual Status Indicators
- 🟢 **Operational** - Service working perfectly
- 🟡 **Degraded** - Performance issues detected
- 🟠 **Partial Outage** - Some functionality affected
- 🔴 **Major Outage** - Service completely down
- ⚫ **Maintenance** - Scheduled maintenance mode

### Real-time Updates
- **Auto-refresh** - Configurable refresh intervals
- **AJAX Updates** - Seamless data updates without page reload
- **Live Metrics** - Real-time system performance data
- **Status Changes** - Instant notification of status changes

### Performance Charts
- **Uptime Graphs** - 24-hour uptime visualization
- **Response Time Charts** - Performance over time
- **Error Rate Trends** - Error rate tracking
- **System Resource Usage** - CPU, memory, and disk charts

## ⏰ **Background Tasks**

### Scheduled Tasks (Celery Beat)
```bash
# Health checks every 5 minutes
run_health_checks_task

# System metrics every 10 minutes  
collect_system_metrics_task

# Data cleanup daily
cleanup_old_health_data_task

# Alerting checks every 3 minutes
check_endpoint_alerting_task

# Uptime updates hourly
update_endpoint_uptime_task

# Daily reports at 00:30
generate_daily_report_task
```

### Starting Background Services
```bash
# Start Celery worker
celery -A driver_app_backend worker -l info

# Start Celery beat scheduler
celery -A driver_app_backend beat -l info

# Start both together
celery -A driver_app_backend worker -l info -B
```

## 🚨 **Alerting & Incidents**

### Automatic Alerting
- **Downtime Detection** - Alert when service is down for 10+ minutes
- **Performance Degradation** - Alert on slow response times
- **High Error Rates** - Alert on increased error percentages
- **Resource Issues** - Alert on high CPU/memory usage

### Incident Management
- **Create Incidents** - Track service disruptions
- **Status Updates** - Update incident status and resolution
- **Affected Services** - Link incidents to specific endpoints
- **Public Communication** - Display incidents on status page

## 📱 **Mobile & Responsive**

The status page is fully responsive and works perfectly on:
- **Desktop** - Full feature experience
- **Tablets** - Optimized layout for medium screens
- **Mobile** - Touch-friendly mobile experience
- **All Browsers** - Cross-browser compatibility

## 🔒 **Security & Permissions**

### Access Control
- **Public Status Page** - No authentication required
- **Health API** - Authentication required for sensitive endpoints
- **Admin Functions** - Staff permissions required
- **Manual Operations** - Admin-only access

### Data Privacy
- **Request Logging** - Sensitive data filtered out
- **IP Tracking** - Compliance with privacy regulations
- **User Information** - Only necessary data collected
- **Data Retention** - Automatic cleanup of old data

## 🚀 **Performance & Optimization**

### Middleware Integration
- **Request Tracking** - Minimal performance impact
- **Response Headers** - X-Response-Time header added
- **Background Processing** - Non-blocking health checks
- **Database Optimization** - Indexed queries for fast lookups

### Caching & Storage
- **Efficient Queries** - Optimized database queries
- **Data Retention** - Configurable data retention policies
- **Batch Processing** - Efficient bulk operations
- **Memory Usage** - Low memory footprint

## 📋 **Admin Interface**

### Health Monitoring Admin
Access comprehensive admin interface at: http://localhost:8000/admin/health/

#### Available Sections:
1. **Service Endpoints** - Manage monitored endpoints
2. **Health Checks** - View health check history
3. **System Metrics** - Review system performance data
4. **API Request Logs** - Analyze API usage patterns
5. **Incidents** - Manage service incidents
6. **Status Page Settings** - Configure status page appearance

## 🔧 **Customization**

### Status Page Themes
Customize colors and appearance:
- **Primary Color** - Main theme color
- **Success Color** - Operational status color
- **Warning Color** - Degraded status color
- **Danger Color** - Outage status color

### Monitoring Configuration
- **Check Intervals** - Customize how often endpoints are checked
- **Timeout Settings** - Configure request timeout values
- **Expected Status Codes** - Set expected HTTP responses
- **Retry Logic** - Configure retry attempts for failed checks

## 📊 **Sample Status Page**

Your status page will display:

```
┌─────────────────────────────────────────────────────────┐
│                    Driver App Status                     │
│              Current status of Driver App services       │
│                                                          │
│        🟢 All Systems Operational                        │
│              8/8 services operational                    │
└─────────────────────────────────────────────────────────┘

Service Status:
┌─────────────────┬──────────────┬─────────────┬──────────┐
│ Service         │ Status       │ 24h Uptime  │ Response │
├─────────────────┼──────────────┼─────────────┼──────────┤
│ API Root        │ 🟢 Operational │ 100.0%     │ 0.12s   │
│ Health Check    │ 🟢 Operational │ 99.98%     │ 0.08s   │
│ User Registration│ 🟢 Operational │ 99.95%     │ 0.15s   │
│ User Login      │ 🟢 Operational │ 99.97%     │ 0.13s   │
└─────────────────┴──────────────┴─────────────┴──────────┘

System Performance (Last 24h):
┌─────────────┬──────────────┬──────────────┬─────────────┐
│ CPU Usage   │ Memory Usage │ Avg Response │ Error Rate  │
│ 15.2%       │ 68.4%        │ 0.12s        │ 0.05%       │
└─────────────┴──────────────┴──────────────┴─────────────┘
```

## 🎯 **Next Steps**

1. **Visit Status Page**: http://localhost:8000/health/status-page/
2. **Test Health API**: http://localhost:8000/health/
3. **Configure Monitoring**: Add your own endpoints to monitor
4. **Setup Alerting**: Configure notifications for downtime
5. **Start Background Tasks**: Run Celery workers for automatic monitoring
6. **Customize Appearance**: Update status page settings in admin

## 🆘 **Troubleshooting**

### Common Issues:

**Health checks not running automatically?**
- Start Celery worker: `celery -A driver_app_backend worker -l info`
- Start Celery beat: `celery -A driver_app_backend beat -l info`

**Status page not loading?**
- Check if health app is in INSTALLED_APPS
- Run migrations: `python manage.py migrate`
- Verify URL configuration

**Endpoints showing as unhealthy?**
- Check if Django server is running
- Verify endpoint URLs are correct
- Check firewall and network settings

**Missing system metrics?**
- Install psutil: `pip install psutil`
- Run manual collection: `python manage.py run_health_checks --collect-metrics`

Your health monitoring system is now fully operational! 🎉