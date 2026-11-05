# Port Asset Lifecycle Management System

A Flask-based web application designed to manage, monitor, and maintain port assets throughout their lifecycle. Developed as an internship project associated with New Mangalore Port Authority (NMPA).

## Project Overview

The Port Asset Lifecycle Management System is a web-based application that helps organize and manage asset-related information within different port departments.

The application provides centralized asset management, maintenance tracking, inspection records, approval workflows, and lifecycle history. It supports different user roles, including administrators and staff, to manage responsibilities and access relevant information.

The primary objective is to simplify asset management processes, improve record organization, and provide better visibility into asset maintenance and operational activities.

## Project Objectives

- Maintain centralized records of port assets.
- Organize assets according to departments and locations.
- Track asset conditions and maintenance activities.
- Manage maintenance assignments and repair requests.
- Support inspection and approval workflows.
- Maintain historical records of asset activities.
- Provide dashboards and reports for administrative monitoring.

## Key Features

### 1. User Authentication and Role Management

- User registration and login.
- Role-based access for administrators and staff.
- Session-based user authentication.
- Department-based access management.
- Administrator role switching.

### 2. Asset Management

- Add and register new assets.
- Edit and update asset information.
- View individual asset details.
- Assign assets to departments.
- Track asset condition and status.
- Upload asset photographs.
- Manage asset disposal and records.
- Search and filter asset information.

### 3. Department Management

- Department-specific asset management.
- Department-level administrative access.
- Department-wise maintenance monitoring.
- Department-specific dashboards and reports.

### 4. Maintenance Management

- Assign maintenance tasks to staff or departments.
- Submit repair and maintenance requests.
- Record maintenance details and repair costs.
- Review repair estimates.
- Track maintenance progress.
- Update maintenance completion status.

### 5. Inspection Management

- Record asset inspection details.
- Maintain inspection dates and inspector information.
- Record asset conditions and remarks.
- View inspection history.

### 6. Approval Management

- Review maintenance and repair estimates.
- Approve or reject maintenance requests.
- Manage maintenance completion approvals.
- Maintain approval status and remarks.

### 7. Asset Lifecycle Tracking

- Track asset creation and registration.
- Maintain maintenance history.
- Record inspection activities.
- Track approval-related activities.
- Maintain asset editing and disposal history.

### 8. Maintenance Prediction

- Estimate the next maintenance date using the average interval between previous completed maintenance activities.
- Support maintenance planning through historical maintenance records.

### 9. Dashboards and Reports

- Administrative dashboard.
- Staff dashboard.
- Asset statistics and status information.
- Department-wise reports.
- Maintenance and inspection information.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database management |
| HTML5 | Web page structure |
| CSS3 | User interface styling |
| JavaScript | Browser-side interactions |
| Jinja2 | Dynamic HTML templating |
| Werkzeug | Flask utilities and request handling |

## System Architecture

The application follows a server-rendered web architecture.

1. **Presentation Layer:** HTML, CSS, JavaScript and Jinja templates provide the user interface.
2. **Application Layer:** Python and Flask handle application routes, authentication, validation and business logic.
3. **Database Layer:** SQLite stores user, asset, maintenance, inspection, approval and lifecycle information.
4. **File Storage:** Local storage maintains uploaded asset photographs.

## Database Modules

The application uses the following primary database tables:

| Table | Description |
|---|---|
| Users | Stores user and department information |
| Assets | Maintains asset details and status |
| Maintenance | Stores maintenance and repair records |
| Inspection | Maintains asset inspection details |
| Approvals | Stores approval requests and decisions |
| Lifecycle | Records asset lifecycle activities |

## Application Workflow

1. Users register and log in to the application.
2. The application identifies the user's role and department.
3. Administrators manage assets and assign maintenance activities.
4. Staff update assigned maintenance tasks and submit inspection information.
5. Administrators review maintenance requests and approvals.
6. Asset-related activities are maintained in lifecycle records.
7. Dashboards and reports provide an overview of asset management activities.

## My Role and Contributions

Developed as part of my three-month industrial internship at New Mangalore Port Authority during my MCA program.

My project involvement included working with the web application's development and understanding its major functional components, including:

- Backend development using Python and Flask.
- Database operations using SQLite.
- Frontend development using HTML, CSS and JavaScript.
- Asset management functionality.
- Maintenance and inspection workflows.
- User roles and department-based functionality.
- Integration of application components.

## Project Structure

```text
PORT_ASSET_MANAGEMENT/
│
├── run.py
├── requirements.txt
├── port_asset.db
│
├── templates/
│   ├── base.html
│   ├── register.html
│   ├── admin/
│   └── staff/
│
├── static/
│   ├── CSS files
│   ├── images/
│   └── uploads/
│
└── README.md
```

*Note: The folder structure above is a simplified representation of the application.*

## Installation and Setup

### Prerequisites

- Python 3.x
- pip
- Code editor (VS Code recommended)

### Step 1: Clone the Repository

```text
git clone YOUR_GITHUB_REPOSITORY_URL
```

### Step 2: Navigate to the Project Directory

```text
cd PORT_ASSET_MANAGEMENT
```

### Step 3: Create a Virtual Environment

```text
python -m venv venv
```

### Step 4: Activate the Virtual Environment

Windows:

```text
venv\Scripts\activate
```

### Step 5: Install Dependencies

```text
pip install -r requirements.txt
```

### Step 6: Run the Application

```text
python run.py
```

Open your browser and navigate to:

```text
http://127.0.0.1:5000/
```

## Learning Outcomes

Through this project, I gained practical exposure to:

- Python-based web application development.
- Flask application architecture.
- Database operations using SQLite.
- Frontend and backend integration.
- User authentication and session management.
- CRUD operations.
- Department-based application workflows.
- Maintenance and approval management.
- Organizing and maintaining application data.

## Future Enhancements

- Implement stronger password security and authentication.
- Introduce more advanced reporting and analytics.
- Add automated maintenance notifications.
- Improve asset tracking and monitoring.
- Implement enhanced access control.
- Deploy the application on a secure production server.

## Acknowledgement

This project was developed as part of my industrial internship at **New Mangalore Port Authority (NMPA)** during my Master of Computer Applications (MCA) program.

I am grateful for the opportunity to gain practical exposure to software application development and database management through this project.

---

**Project Category:** Full Stack Web Application  
**Backend:** Python, Flask  
**Database:** SQLite  
**Frontend:** HTML, CSS, JavaScript
