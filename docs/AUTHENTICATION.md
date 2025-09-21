# Authentication System

The MicroK8s Cluster Orchestrator now includes a comprehensive user authentication and authorization system to secure access to the platform.

## Features

### User Management
- **User Registration**: Create new user accounts with email verification
- **User Profiles**: Manage personal information and account settings
- **Password Management**: Secure password hashing and change functionality
- **Role-Based Access Control**: Admin and regular user roles

### Security Features
- **Session Management**: Secure login sessions with Flask-Login
- **Password Hashing**: Uses Werkzeug's secure password hashing
- **Route Protection**: All application routes require authentication
- **Operation Tracking**: All operations are tracked by user

### Admin Features
- **User Management**: View, activate/deactivate, and delete users
- **Role Management**: Grant or revoke admin privileges
- **System-wide Access**: Admin users can view all operations and data

## Getting Started

### First Time Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Database Migration**:
   ```bash
   python scripts/migrate_auth.py
   ```

3. **Start the Application**:
   ```bash
   python cli.py web
   ```

4. **Create First Admin User**:
   - **Option A - Web Interface**: Navigate to `/auth/register` (first user gets admin privileges)
   - **Option B - CLI**: Run `python cli.py user create-admin` for command-line user creation

### User Roles

#### Administrator
- Full access to all features
- Can view all operations from all users
- Can manage other users (create, deactivate, delete)
- Can grant/revoke admin privileges
- Access to user management interface

#### Regular User
- Can access all cluster management features
- Can only view their own operations
- Cannot manage other users
- Cannot access admin-only features

## Authentication Endpoints

### Public Endpoints
- `GET /auth/login` - Login page
- `POST /auth/login` - Process login
- `GET /auth/register` - Registration page (restricted after first user)
- `POST /auth/register` - Process registration

### Protected Endpoints
- `GET /auth/logout` - Logout user
- `GET /auth/profile` - User profile page
- `POST /auth/profile` - Update profile
- `GET /auth/change-password` - Change password page
- `POST /auth/change-password` - Process password change

### Admin-Only Endpoints
- `GET /auth/users` - User management page
- `POST /auth/users/<id>/toggle-admin` - Toggle admin status
- `POST /auth/users/<id>/toggle-active` - Toggle active status
- `POST /auth/users/<id>/delete` - Delete user

## CLI User Management

The system includes comprehensive command-line tools for user management, useful for automation, initial setup, and emergency access.

### Available CLI Commands

#### Create Admin User
```bash
# Interactive mode (prompts for all details)
python cli.py user create-admin

# With parameters
python cli.py user create-admin -u admin -e admin@example.com -f John -l Doe
```

#### List Users
```bash
# Table format (default)
python cli.py user list

# JSON format
python cli.py user list --format json
```

#### Manage User Privileges
```bash
# Toggle admin status
python cli.py user toggle-admin username

# Deactivate user (with confirmation)
python cli.py user deactivate username

# Deactivate user (skip confirmation)
python cli.py user deactivate username --confirm

# Activate user
python cli.py user activate username
```

### CLI Command Features
- **Secure Password Input**: Hidden password prompts with confirmation
- **Validation**: Checks for existing usernames and emails
- **Colored Output**: Visual feedback with success/error/warning messages
- **Flexible Output**: Table or JSON format for data export
- **Safety Checks**: Confirmation prompts for destructive operations
- **Error Handling**: Comprehensive error messages and graceful failures

### Use Cases for CLI Commands
- **Initial Setup**: Create first admin user without web interface
- **Automation**: Script user management for CI/CD pipelines
- **Emergency Access**: Create admin users when web interface is unavailable
- **Bulk Operations**: Manage multiple users programmatically
- **System Administration**: Remote user management via SSH

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login DATETIME,
    login_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Operations Table Updates
The operations table has been updated to track which user initiated each operation:
- Added `user_id` foreign key to users table
- Maintained `created_by` field for backward compatibility

## Security Considerations

1. **Password Security**:
   - Minimum 6 characters required
   - Passwords are hashed using Werkzeug's secure methods
   - No plain text passwords stored

2. **Session Security**:
   - Sessions use Flask's secure session management
   - Configurable session timeout
   - "Remember Me" functionality available

3. **Access Control**:
   - All routes protected with `@login_required`
   - Role-based access for admin features
   - Users can only view their own operations

4. **Input Validation**:
   - Username uniqueness enforced
   - Email format validation
   - Password confirmation required

## Configuration

### Flask Settings
Add these to your configuration:
```python
# Secret key for session management (change in production!)
SECRET_KEY = 'your-secret-key-here'

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Remember me duration
```

### First User Registration
- Registration is open only when no admin users exist
- After the first admin is created, only admins can create new users
- This prevents unauthorized account creation

## Troubleshooting

### Common Issues

1. **"Access Denied" Messages**:
   - Ensure user is logged in
   - Check if admin privileges are required
   - Verify user account is active

2. **Database Errors**:
   - Run the migration script: `python scripts/migrate_auth.py`
   - Check database file permissions
   - Ensure all dependencies are installed

3. **Login Issues**:
   - Verify username and password
   - Check if account is active
   - Try clearing browser cookies

### Reset Admin Access
If you lose admin access, you can manually update the database:
```sql
UPDATE users SET is_admin = 1 WHERE username = 'your-username';
```

## Development Notes

### Adding New Protected Routes
```python
from flask_login import login_required, current_user

@bp.route('/new-route')
@login_required
def new_route():
    # Route is now protected
    pass
```

### Checking Admin Status
```python
if current_user.is_admin:
    # Admin-only code
    pass
```

### Tracking Operations by User
```python
operation.user_id = current_user.id
operation.created_by = current_user.full_name
```

## Future Enhancements

Potential improvements for the authentication system:
- Email verification for new accounts
- Password reset functionality
- Two-factor authentication (2FA)
- OAuth integration (Google, GitHub, etc.)
- Audit logging for admin actions
- Account lockout after failed attempts
- Password complexity requirements
